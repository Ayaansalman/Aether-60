"""
Orchestrator Service for AETHER Autonomous Game Generation.
Drives the explicit state machine:
QUEUED -> PLANNING -> VALIDATING_SPEC -> BUILDING -> TESTING -> READY | READY_WITH_WARNINGS | FAILED
and the bounded self-repair loop (max 2 repairs, max 3 test runs):
TESTING (critical failure, all failed checks patchable) -> REPAIRING -> VALIDATING_SPEC -> BUILDING -> TESTING.
A failed non-patchable (runtime) check is never repaired: the job ends FAILED ("needs developer").
Conforms to Sections 4.4, 4.5, 6, and 9.1 of the AETHER Engineering Specification.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from providers.base import ProviderError
from providers.factory import get_provider
from schemas.game_ir import GameIR
from services import event_store, job_store
from services.planner import plan_game
from services.repair import propose_repair
from services.validator import validate_game_ir

logger = logging.getLogger("aether.orchestrator")

ERROR_MESSAGES: Dict[str, str] = {
    "PROMPT_INVALID": "The prompt provided is invalid or exceeds character limits.",
    "MODEL_TIMEOUT": "The AI model took too long to respond. Please try again.",
    "MODEL_HTTP_ERROR": "Upstream AI model connection failed or quota was exceeded. Please try again.",
    "MODEL_OUTPUT_INVALID": "The AI model returned an unparseable response.",
    "SPEC_UNSUPPORTED": "The generated game specification is unsupported or failed validation.",
    "QA_CRASHED": "Automated browser verification runner crashed or timed out.",
    "QA_FAILED": "A critical runtime check failed that cannot be repaired automatically (needs developer).",
    "REPAIR_LIMIT_REACHED": "The game could not be repaired within the maximum number of attempts.",
    "GAME_NOT_FOUND": "The requested game was not found.",
    "INTERNAL_ERROR": "An internal server error occurred while processing the game.",
}

# Bounded repair loop: first build + at most 2 repairs = at most 3 QA runs.
MAX_REPAIRS = 2
MAX_TEST_RUNS = MAX_REPAIRS + 1

# Single worker lock enforcing concurrency limit 1
_queue_lock = asyncio.Lock()


def get_artifacts_dir() -> Path:
    """Resolves the root directory for job artifacts."""
    env_dir = os.getenv("AETHER_ARTIFACTS_DIR")
    if env_dir:
        p = Path(env_dir)
    else:
        p = Path(__file__).resolve().parent.parent / "artifacts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_friendly_error_message(error_code: str) -> str:
    """Returns a user-friendly explanation for an error code."""
    return ERROR_MESSAGES.get(error_code, "An unexpected error occurred while processing the game.")


def normalize_model_error_code(raw_code: Optional[str], errors: List[str]) -> str:
    """Maps a provider/planner/repair error code to one of the documented job error codes."""
    code = raw_code or "MODEL_OUTPUT_INVALID"
    if "timeout" in code.lower() or "timeout" in " ".join(errors).lower():
        return "MODEL_TIMEOUT"
    if code in ("PROMPT_INVALID", "MODEL_HTTP_ERROR"):
        return code
    return "MODEL_OUTPUT_INVALID"


def append_trace(game_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    """Appends an event line to artifacts/<game_id>/agent_trace.jsonl."""
    try:
        job_dir = get_artifacts_dir() / game_id
        job_dir.mkdir(parents=True, exist_ok=True)
        trace_path = job_dir / "agent_trace.jsonl"
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "game_id": game_id,
            "event": event_type,
            "payload": payload,
        }
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning(f"Failed to append to agent trace for {game_id}: {exc}")


async def trigger_queue_processing() -> None:
    """
    Triggers the FIFO queue worker.
    Concurrency limit 1: If a worker is already running, extra jobs wait in QUEUED.
    """
    if _queue_lock.locked():
        return

    async with _queue_lock:
        while True:
            next_job = job_store.get_next_queued_job()
            if not next_job:
                break
            await run_single_job(next_job["game_id"])


class QARunError(Exception):
    """QA could not produce a report (timeout / crash). The job ends FAILED with QA_CRASHED."""

    def __init__(self, detail: str, trace_event: str, trace_payload: Dict[str, Any]):
        super().__init__(detail)
        self.detail = detail
        self.trace_event = trace_event
        self.trace_payload = trace_payload


async def execute_qa(
    game_id: str,
    game_url: str,
    artifacts_dir: Path,
    attempt: int,
) -> Dict[str, Any]:
    """
    Runs one QA pass and returns the parsed report dict.
    QA_MODE=fake returns a canned PASS report (tests only; `real` is the default).
    Real mode runs `python -m services.qa_runner <url>?test=1` as a subprocess with a 180s timeout.
    Raises QARunError on timeout or when no JSON report can be parsed.
    """
    qa_mode = os.getenv("QA_MODE", "real").strip().lower()

    if qa_mode == "fake":
        return {
            "url": f"{game_url}?test=1",
            "overall": "PASS",
            "checks": [
                {"id": "canvas_mounted", "passed": True, "critical": True, "patchable": False, "details": "Canvas mounted"},
                {"id": "hook_ready", "passed": True, "critical": True, "patchable": False, "details": "Hook ready"},
                {"id": "player_movement", "passed": True, "critical": True, "patchable": False, "details": "Movement verified"},
                {"id": "enemy_spawning", "passed": True, "critical": True, "patchable": False, "details": "Enemies active"},
                {"id": "objective_progress", "passed": True, "critical": True, "patchable": False, "details": "Objective operational"},
            ],
            "page_errors": [],
            "screenshot_path": str(artifacts_dir / "screenshot.png"),
            "repair_recommended": False,
        }

    backend_dir = Path(__file__).resolve().parent.parent
    venv_py = backend_dir / "venv" / "Scripts" / "python.exe"
    backend_python = str(venv_py) if venv_py.exists() else sys.executable
    qa_url = f"{game_url}?test=1"
    cmd = [backend_python, "-m", "services.qa_runner", qa_url, str(artifacts_dir)]

    def run_qa_subprocess() -> subprocess.CompletedProcess:
        sub_env = os.environ.copy()
        sub_env["PYTHONPATH"] = str(backend_dir)
        return subprocess.run(
            cmd,
            cwd=str(backend_dir),
            env=sub_env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )

    loop = asyncio.get_running_loop()
    try:
        proc = await loop.run_in_executor(None, run_qa_subprocess)
        stdout = proc.stdout.strip()
        try:
            return json.loads(stdout)
        except Exception:
            # Look for a JSON block in stdout if there was extra text
            match = re.search(r"\{[\s\S]*\}", stdout)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"No valid JSON output from QA runner: {stdout[:200]}")
    except subprocess.TimeoutExpired:
        raise QARunError(
            "QA runner timed out after 180s",
            "TESTING_TIMEOUT",
            {"timeout": 180, "attempt": attempt},
        )
    except Exception as exc:
        raise QARunError(
            f"QA runner failed to execute ({exc})",
            "TESTING_CRASHED",
            {"exception": str(exc), "attempt": attempt},
        )


def _fail_job(
    game_id: str,
    stage: str,
    error_code: str,
    detail: str,
    attempt: int,
    trace_event: str,
    trace_payload: Dict[str, Any],
    model_id: Optional[str] = None,
) -> None:
    """Moves a job to the terminal FAILED state with a friendly message, event and trace line."""
    friendly = get_friendly_error_message(error_code)
    update: Dict[str, Any] = {"status": "FAILED", "stage": stage, "error_code": error_code}
    if model_id:
        update["model_id"] = model_id
    job_store.update_job(game_id, **update)
    event_store.add_event(
        game_id,
        stage=stage,
        result="FAILED",
        detail=f"{friendly}: {detail}" if detail else friendly,
        attempt=attempt,
    )
    append_trace(game_id, trace_event, {"error_code": error_code, **trace_payload})


async def run_single_job(game_id: str) -> None:
    """Executes the full generation, QA and bounded-repair lifecycle for a single game job."""
    job = job_store.get_job(game_id)
    if not job:
        logger.error(f"Job {game_id} not found in store")
        return

    if job["status"] in ("READY", "READY_WITH_WARNINGS", "FAILED"):
        return

    artifacts_dir = get_artifacts_dir() / game_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths: List[str] = ["agent_trace.jsonl"]

    try:
        # -------------------------------------------------------------
        # 1. PLANNING STAGE
        # -------------------------------------------------------------
        job_store.update_job(game_id, status="PLANNING", stage="PLANNING")
        event_store.add_event(
            game_id,
            stage="PLANNING",
            result="START",
            detail="Initiating model game planning",
            attempt=1,
        )
        append_trace(game_id, "PLANNING_START", {"prompt": job["prompt"]})

        provider = get_provider()
        # Run synchronous planner in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        plan_result = await loop.run_in_executor(
            None, lambda: plan_game(job["prompt"], provider)
        )

        # Record any fallback events that occurred during planning
        recent_fallbacks = getattr(provider, "get_recent_fallbacks", lambda: [])()
        for fb in recent_fallbacks:
            event_store.add_event(
                game_id,
                stage="PLANNING",
                result="FALLBACK",
                detail=f"fallback: {fb['from_model']} -> {fb['to_model']} ({fb['reason']})",
                attempt=1,
            )
            append_trace(
                game_id,
                "FALLBACK",
                {
                    "from_model": fb["from_model"],
                    "to_model": fb["to_model"],
                    "reason": fb["reason"],
                    "event": f"fallback: {fb['from_model']} -> {fb['to_model']} ({fb['reason']})",
                },
            )

        if not plan_result.ok or plan_result.spec is None:
            err_code = normalize_model_error_code(plan_result.error_code, plan_result.errors)
            friendly = get_friendly_error_message(err_code)
            job_store.update_job(
                game_id,
                status="FAILED",
                stage="PLANNING",
                error_code=err_code,
                model_id=plan_result.model or getattr(provider, "model_name", ""),
            )
            event_store.add_event(
                game_id,
                stage="PLANNING",
                result="FAILED",
                detail=f"{friendly} ({'; '.join(plan_result.errors)})",
                attempt=1,
            )
            append_trace(game_id, "PLANNING_FAILED", {"error_code": err_code, "errors": plan_result.errors})
            return

        spec = plan_result.spec
        limitations = plan_result.limitations
        model_id = plan_result.model or getattr(provider, "model_name", "")

        job_store.update_job(game_id, limitations=limitations, model_id=model_id)
        event_store.add_event(
            game_id,
            stage="PLANNING",
            result="SUCCESS",
            detail=f"Specification generated by model ('{spec.title}')",
            attempt=1,
        )
        append_trace(game_id, "PLANNING_SUCCESS", {"title": spec.title, "limitations": limitations})

        # -------------------------------------------------------------
        # 2. VALIDATING_SPEC STAGE
        # -------------------------------------------------------------
        job_store.update_job(game_id, status="VALIDATING_SPEC", stage="VALIDATING_SPEC")
        event_store.add_event(
            game_id,
            stage="VALIDATING_SPEC",
            result="START",
            detail="Validating GameIR against schema and rules",
            attempt=1,
        )
        append_trace(game_id, "VALIDATING_START", {})

        raw_spec = spec.model_dump()
        val_res = validate_game_ir(raw_spec)
        if not val_res.ok or val_res.spec is None:
            validation_errors = val_res.errors
            err_code = "SPEC_UNSUPPORTED"
            friendly = get_friendly_error_message(err_code)
            job_store.update_job(
                game_id,
                status="FAILED",
                stage="VALIDATING_SPEC",
                error_code=err_code,
            )
            event_store.add_event(
                game_id,
                stage="VALIDATING_SPEC",
                result="FAILED",
                detail=f"{friendly}: {'; '.join(validation_errors)}",
                attempt=1,
            )
            append_trace(game_id, "VALIDATING_FAILED", {"errors": validation_errors})
            return

        spec = val_res.spec
        event_store.add_event(
            game_id,
            stage="VALIDATING_SPEC",
            result="SUCCESS",
            detail="GameIR specification schema and rules valid",
            attempt=1,
        )
        append_trace(game_id, "VALIDATING_SUCCESS", {"valid": True})

        # Persist spec artifact (game_ir_v1.json)
        spec_v1_path = artifacts_dir / "game_ir_v1.json"
        with open(spec_v1_path, "w", encoding="utf-8") as f:
            f.write(spec.model_dump_json(indent=2))
        artifact_paths.append("game_ir_v1.json")

        job_store.update_job(
            game_id,
            spec_json=spec.model_dump_json(),
            artifact_paths=artifact_paths,
        )

        # -------------------------------------------------------------
        # 3. BUILDING STAGE
        # -------------------------------------------------------------
        job_store.update_job(game_id, status="BUILDING", stage="BUILDING")
        event_store.add_event(
            game_id,
            stage="BUILDING",
            result="START",
            detail="Assembling game runtime parameters",
            attempt=1,
        )
        append_trace(game_id, "BUILDING_START", {})

        game_url = f"http://localhost:5173/play/{game_id}"
        job_store.update_job(game_id, game_url=game_url)
        event_store.add_event(
            game_id,
            stage="BUILDING",
            result="SUCCESS",
            detail=f"Game runtime mapped to {game_url}",
            attempt=1,
        )
        append_trace(game_id, "BUILDING_SUCCESS", {"game_url": game_url})

        # -------------------------------------------------------------
        # 4. TESTING <-> REPAIRING LOOP (max 3 QA runs, max 2 repairs)
        # -------------------------------------------------------------
        current_spec: GameIR = spec
        attempt = 1
        repairs_done = 0

        while True:
            job_store.update_job(game_id, status="TESTING", stage="TESTING", attempt=attempt)
            event_store.add_event(
                game_id,
                stage="TESTING",
                result="START",
                detail=f"Running automated browser QA suite (attempt {attempt})",
                attempt=attempt,
            )
            append_trace(game_id, "TESTING_START", {"attempt": attempt})

            try:
                report = await execute_qa(game_id, game_url, artifacts_dir, attempt)
            except QARunError as qa_exc:
                _fail_job(
                    game_id,
                    "TESTING",
                    "QA_CRASHED",
                    qa_exc.detail,
                    attempt,
                    qa_exc.trace_event,
                    qa_exc.trace_payload,
                )
                return

            # Persist QA report artifact for this attempt
            report_name = f"qa_report_attempt_{attempt}.json"
            with open(artifacts_dir / report_name, "w", encoding="utf-8") as f:
                f.write(json.dumps(report, indent=2))
            if report_name not in artifact_paths:
                artifact_paths.append(report_name)

            checks = report.get("checks", [])
            passed_count = sum(1 for c in checks if c.get("passed"))
            failed_count = sum(1 for c in checks if not c.get("passed"))
            failed_critical = [
                c for c in checks if not c.get("passed") and c.get("critical", True)
            ]
            critical_failed = [c.get("id") for c in failed_critical]

            qa_summary = {
                "passed": passed_count,
                "failed": failed_count,
                "critical_failed": critical_failed,
            }
            job_store.update_job(
                game_id,
                qa_summary=qa_summary,
                latest_qa_json=json.dumps(report),
                artifact_paths=artifact_paths,
            )

            if not critical_failed:
                final_status = "READY_WITH_WARNINGS" if failed_count > 0 else "READY"
                job_store.update_job(game_id, status=final_status, stage="TESTING")
                event_store.add_event(
                    game_id,
                    stage="TESTING",
                    result="SUCCESS",
                    detail=f"QA passed ({passed_count}/{len(checks)} checks). State: {final_status}",
                    attempt=attempt,
                )
                append_trace(game_id, "COMPLETED", {"status": final_status, "qa_summary": qa_summary, "attempt": attempt})
                return

            # ---- Critical failure: decide whether a parameter repair is allowed ----
            event_store.add_event(
                game_id,
                stage="TESTING",
                result="FAILED",
                detail=f"QA attempt {attempt} failed critical checks: {', '.join(critical_failed)}",
                attempt=attempt,
            )
            append_trace(game_id, "TESTING_CRITICAL_FAILED", {"attempt": attempt, "critical_failed": critical_failed})

            non_patchable = [c.get("id") for c in failed_critical if not c.get("patchable", False)]
            if non_patchable:
                event_store.add_event(
                    game_id,
                    stage="REPAIRING",
                    result="SKIPPED",
                    detail=(
                        "Needs developer: runtime check(s) failed that a parameter patch cannot fix "
                        f"({', '.join(non_patchable)}). No repair attempted."
                    ),
                    attempt=attempt,
                )
                _fail_job(
                    game_id,
                    "TESTING",
                    "QA_FAILED",
                    f"Needs developer: non-patchable critical check(s) failed ({', '.join(non_patchable)})",
                    attempt,
                    "FAILED",
                    {"critical_failed": critical_failed, "non_patchable": non_patchable},
                )
                return

            if repairs_done >= MAX_REPAIRS or attempt >= MAX_TEST_RUNS:
                _fail_job(
                    game_id,
                    "TESTING",
                    "REPAIR_LIMIT_REACHED",
                    f"Still failing after {repairs_done} repair(s): {', '.join(critical_failed)}",
                    attempt,
                    "FAILED",
                    {"critical_failed": critical_failed, "repairs": repairs_done},
                )
                return

            # -------------------------------------------------------------
            # 5. REPAIRING STAGE (parameter-only patch)
            # -------------------------------------------------------------
            repairs_done += 1
            attempt += 1
            job_store.update_job(game_id, status="REPAIRING", stage="REPAIRING", attempt=attempt)
            event_store.add_event(
                game_id,
                stage="REPAIRING",
                result="START",
                detail=f"Proposing parameter patch for failed checks: {', '.join(critical_failed)}",
                attempt=attempt,
            )
            append_trace(game_id, "REPAIRING_START", {"attempt": attempt, "failed": critical_failed})

            repair_input_spec = current_spec
            repair_result = await loop.run_in_executor(
                None, lambda: propose_repair(repair_input_spec, report, provider)
            )

            # Record any fallback events that occurred during repair
            recent_fallbacks = getattr(provider, "get_recent_fallbacks", lambda: [])()
            for fb in recent_fallbacks:
                event_store.add_event(
                    game_id,
                    stage="REPAIRING",
                    result="FALLBACK",
                    detail=f"fallback: {fb['from_model']} -> {fb['to_model']} ({fb['reason']})",
                    attempt=attempt,
                )
                append_trace(
                    game_id,
                    "FALLBACK",
                    {
                        "from_model": fb["from_model"],
                        "to_model": fb["to_model"],
                        "reason": fb["reason"],
                        "event": f"fallback: {fb['from_model']} -> {fb['to_model']} ({fb['reason']})",
                    },
                )

            if not repair_result.ok or repair_result.spec is None:
                err_code = normalize_model_error_code(repair_result.error_code, repair_result.errors)
                _fail_job(
                    game_id,
                    "REPAIRING",
                    err_code,
                    f"Repair proposal rejected ({'; '.join(repair_result.errors)})",
                    attempt,
                    "REPAIRING_FAILED",
                    {"errors": repair_result.errors},
                    model_id=repair_result.model or None,
                )
                return

            event_store.add_event(
                game_id,
                stage="REPAIRING",
                result="SUCCESS",
                detail=f"Parameter patch accepted ({len(repair_result.diff.get('after', {}))} field(s) changed)",
                attempt=attempt,
                rationale=repair_result.rationale,
                diff=repair_result.diff,
            )
            append_trace(
                game_id,
                "REPAIRING_SUCCESS",
                {"attempt": attempt, "rationale": repair_result.rationale, "diff": repair_result.diff},
            )

            # -------------------------------------------------------------
            # 6. VALIDATING_SPEC (patched) -> BUILDING -> TESTING
            # -------------------------------------------------------------
            job_store.update_job(game_id, status="VALIDATING_SPEC", stage="VALIDATING_SPEC", attempt=attempt)
            event_store.add_event(
                game_id,
                stage="VALIDATING_SPEC",
                result="START",
                detail="Validating repaired GameIR against schema and rules",
                attempt=attempt,
            )
            patched_val = validate_game_ir(repair_result.spec.model_dump())
            if not patched_val.ok or patched_val.spec is None:
                _fail_job(
                    game_id,
                    "VALIDATING_SPEC",
                    "SPEC_UNSUPPORTED",
                    "; ".join(patched_val.errors),
                    attempt,
                    "VALIDATING_FAILED",
                    {"errors": patched_val.errors, "attempt": attempt},
                )
                return
            current_spec = patched_val.spec
            event_store.add_event(
                game_id,
                stage="VALIDATING_SPEC",
                result="SUCCESS",
                detail="Repaired GameIR specification schema and rules valid",
                attempt=attempt,
            )

            spec_name = f"game_ir_v{attempt}.json"
            with open(artifacts_dir / spec_name, "w", encoding="utf-8") as f:
                f.write(current_spec.model_dump_json(indent=2))
            if spec_name not in artifact_paths:
                artifact_paths.append(spec_name)
            job_store.update_job(
                game_id,
                spec_json=current_spec.model_dump_json(),
                artifact_paths=artifact_paths,
            )

            job_store.update_job(game_id, status="BUILDING", stage="BUILDING", attempt=attempt)
            event_store.add_event(
                game_id,
                stage="BUILDING",
                result="SUCCESS",
                detail=f"Repaired runtime parameters saved as {spec_name}; re-running QA",
                attempt=attempt,
            )
            append_trace(game_id, "BUILDING_SUCCESS", {"attempt": attempt, "spec_artifact": spec_name})

    except Exception as exc:
        logger.exception(f"Unexpected fatal error while executing job {game_id}: {exc}")
        err_code = "INTERNAL_ERROR"
        friendly = get_friendly_error_message(err_code)
        job_store.update_job(
            game_id,
            status="FAILED",
            stage="INTERNAL_ERROR",
            error_code=err_code,
        )
        event_store.add_event(
            game_id,
            stage="INTERNAL_ERROR",
            result="FAILED",
            detail=f"{friendly}: {exc}",
            attempt=1,
        )
        append_trace(game_id, "INTERNAL_ERROR", {"exception": str(exc)})
