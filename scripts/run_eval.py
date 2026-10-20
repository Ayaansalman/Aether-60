#!/usr/bin/env python3
"""
AETHER Full-Pipeline Evaluation Harness (Phase 5).
Conforms to docs/MASTER_PLAN.md Phase 5 and Engineering Specification.

Executes the standardized 12-prompt evaluation suite (10 standard + 2 stress prompts)
through the full generation, validation, QA, and self-repair pipeline.
Supports both mock dry runs and live model providers.
"""

import argparse
import asyncio
import datetime
import json
import os
import re
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Path setup: locate repo root and canonical backend root
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "aether-backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    backend_env = BACKEND_DIR / ".env"
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)
    else:
        load_dotenv()
except ImportError:
    pass

from providers.base import (
    ProviderError,
    get_model_request_count,
    reset_model_request_count,
)
from providers.factory import get_provider, set_custom_provider
from providers.mock import MockModelProvider, MOCK_LABEL
from services import job_store, event_store
from services.orchestrator import run_single_job, get_artifacts_dir

MOCK_BANNER = """================================================================================
        MOCK PROVIDER: not a real model, results are not evidence
================================================================================"""


def find_prompts_file(filename: str = "prompts.json") -> Path:
    """Finds a prompt JSON file in the canonical aether-backend/bench directory."""
    candidates = [
        BACKEND_DIR / "bench" / filename,
        ROOT_DIR / "aether-backend" / "bench" / filename,
        Path.cwd() / "aether-backend" / "bench" / filename,
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    raise FileNotFoundError(f"Could not locate canonical aether-backend/bench/{filename}")


def load_eval_prompts(
    prompts_path: Optional[Path] = None,
    stress_path: Optional[Path] = None,
    filter_ids: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Loads standard prompts and stress prompts from the canonical benchmark location,
    optionally injecting a custom prompt and filtering by prompt IDs.
    """
    p_file = prompts_path or find_prompts_file("prompts.json")
    with open(p_file, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    try:
        s_file = stress_path or find_prompts_file("stress_prompts.json")
        with open(s_file, "r", encoding="utf-8") as f:
            stress_prompts = json.load(f)
    except FileNotFoundError:
        stress_prompts = []

    combined = prompts + stress_prompts

    if custom_prompt:
        cid = "repair_demo" if "repair demo" in custom_prompt.lower() else "custom_01"
        custom_entry = {
            "id": cid,
            "prompt": custom_prompt,
            "expected_theme": None,
            "expected_objective_type": "survive_seconds" if "repair demo" in custom_prompt.lower() else None,
            "expect_limitation": False,
            "notes": "Custom prompt provided via CLI",
        }
        # If not already present with same id, add it
        combined.append(custom_entry)

        if not filter_ids:
            return [custom_entry]

    if filter_ids:
        filter_set = {i.strip() for i in filter_ids if i.strip()}
        matched = []
        for fid in filter_ids:
            clean_id = fid.strip()
            found = next((p for p in combined if p["id"] == clean_id), None)
            if found and found not in matched:
                matched.append(found)
        # Any remaining that matched set
        for p in combined:
            if p["id"] in filter_set and p not in matched:
                matched.append(p)
        return matched

    return combined


def classify_qa_failure(qa_report: Dict[str, Any]) -> str:
    """
    Classifies a QA failure into one of the standardized categories:
    schema, rendering, interaction, objective, restart, timeout, provider_error, not_run.
    """
    checks = qa_report.get("checks", [])
    failed = [c for c in checks if not c.get("passed")]
    failed_ids = {c.get("id") for c in failed}

    if "canvas_mounted" in failed_ids or "hook_ready" in failed_ids:
        return "rendering"
    if any(cid in failed_ids for cid in ["player_movement", "movement_speed_consistent", "diagonal_normalized", "attack_responds", "hud_consistent"]):
        return "interaction"
    if any(cid in failed_ids for cid in ["restart_resets_after_win", "restart_resets_after_loss", "no_actions_after_end"]):
        return "restart"
    if any(cid in failed_ids for cid in ["objective_progress", "win_reachable", "lose_reachable", "idle_survival_min_seconds", "flee_bot_survives"]):
        return "objective"
    return "objective"


def is_server_listening(port: int) -> bool:
    """Checks if a local TCP port has an active listener."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_servers_if_needed(qa_mode: str) -> Tuple[Optional[subprocess.Popen], Optional[subprocess.Popen]]:
    """If real QA is required and servers are not running, starts them."""
    if qa_mode != "real":
        return None, None

    backend_proc = None
    frontend_proc = None

    if not is_server_listening(8000):
        _env_py = os.getenv("AETHER_PYTHON")
        if _env_py and Path(_env_py).exists():
            py_bin = str(Path(_env_py))
        elif (BACKEND_DIR / "venv" / "Scripts" / "python.exe").exists():
            py_bin = str(BACKEND_DIR / "venv" / "Scripts" / "python.exe")
        else:
            py_bin = sys.executable
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BACKEND_DIR)
        print("[run_eval] Spawning background backend on port 8000 for real QA...")
        backend_proc = subprocess.Popen(
            [py_bin, "-m", "uvicorn", "main:app", "--port", "8000"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if not is_server_listening(5173):
        node_bin = r"C:\Program Files\nodejs\npm.cmd" if Path(r"C:\Program Files\nodejs\npm.cmd").exists() else "npm.cmd"
        env = os.environ.copy()
        if r"C:\Program Files\nodejs" not in env.get("PATH", ""):
            env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")
        print("[run_eval] Spawning background Vite dev server on port 5173 for real QA...")
        frontend_proc = subprocess.Popen(
            [node_bin, "run", "dev"],
            cwd=str(ROOT_DIR / "aether-frontend"),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if backend_proc or frontend_proc:
        print("[run_eval] Waiting for dev servers to become ready...")
        time.sleep(4)

    return backend_proc, frontend_proc


def stop_servers(backend_proc: Optional[subprocess.Popen], frontend_proc: Optional[subprocess.Popen]) -> None:
    """Terminates dev servers started by the harness."""
    for proc, name in [(backend_proc, "Backend"), (frontend_proc, "Vite dev server")]:
        if proc:
            try:
                print(f"[run_eval] Stopping spawned {name}...")
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def run_evaluation(
    real_flag: bool = False,
    max_requests: int = 18,
    delay_seconds: float = 13.0,
    qa_mode: str = "fake",
    prompts_file: Optional[Path] = None,
    stress_file: Optional[Path] = None,
    filter_ids: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
    output_dir: Optional[Path] = None,
    docs_file: Optional[Path] = None,
    custom_provider: Optional[Any] = None,
    allow_fallback: bool = False,
    timeout: Optional[float] = None,
    run_label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the full evaluation pipeline per rules 1-6.
    """
    env_provider = os.getenv("MODEL_PROVIDER", "mock").strip().lower()

    if custom_provider is not None:
        set_custom_provider(custom_provider)
        active_provider = custom_provider
        is_mock = isinstance(active_provider, MockModelProvider) or env_provider == "mock"
    else:
        active_provider = get_provider()
        is_mock = isinstance(active_provider, MockModelProvider) or env_provider == "mock"

    # Save original environment to avoid leaking into other tests/runs
    orig_env_allow_fallback = os.environ.get("AETHER_ALLOW_FALLBACK")
    orig_env_fallbacks = os.environ.get("MODEL_FALLBACKS")

    # Fallback configuration: disabled unless --allow-fallback is passed
    if not allow_fallback:
        os.environ["AETHER_ALLOW_FALLBACK"] = "0"
        os.environ["MODEL_FALLBACKS"] = ""
        if hasattr(active_provider, "allow_fallback"):
            setattr(active_provider, "allow_fallback", False)
    else:
        os.environ["AETHER_ALLOW_FALLBACK"] = "1"
        if hasattr(active_provider, "allow_fallback"):
            setattr(active_provider, "allow_fallback", True)

    # Rule 2: Real providers need an explicit --real flag
    if not is_mock and not real_flag:
        print(f"Error: MODEL_PROVIDER is '{env_provider}' but --real was not specified.", file=sys.stderr)
        print("Real provider runs require an explicit --real flag to prevent accidental quota consumption.", file=sys.stderr)
        sys.exit(1)

    # Rule 1: Provider and model come from environment only
    if is_mock:
        provider_name = "mock"
        model_name = "mock"
        print(MOCK_BANNER)
    else:
        provider_name = env_provider
        model_name = os.getenv("MODEL_NAME") or os.getenv("OPENAI_MODEL") or getattr(active_provider, "model_name", "unknown")

    # Set QA_MODE for the orchestrator
    os.environ["QA_MODE"] = qa_mode

    # Reset model request counter
    reset_model_request_count()

    # Load prompts (canonical bench, filtered by ids/prompt if provided)
    all_prompts = load_eval_prompts(
        prompts_path=prompts_file,
        stress_path=stress_file,
        filter_ids=filter_ids,
        custom_prompt=custom_prompt,
    )
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    date_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")

    # Request timeout configuration: CLI flag, env var, or default 60.0s
    req_timeout = timeout
    if req_timeout is None:
        env_to = os.getenv("MODEL_TIMEOUT_SECONDS")
        if env_to:
            try:
                req_timeout = float(env_to)
            except ValueError:
                req_timeout = 60.0
        else:
            req_timeout = 60.0
    os.environ["MODEL_TIMEOUT_SECONDS"] = str(req_timeout)
    if hasattr(active_provider, "timeout_seconds"):
        setattr(active_provider, "timeout_seconds", req_timeout)

    print("\n" + "=" * 90)
    print("                     AETHER FULL-PIPELINE EVALUATION HARNESS")
    print("=" * 90)
    print(f"Date:               {date_str}")
    print(f"Provider:           {provider_name}")
    print(f"Model ID:           {model_name}")
    print(f"Fallback Status:    fallback: {'enabled' if allow_fallback else 'disabled'}")
    print(f"Request Timeout:    {req_timeout}s")
    print(f"Total Prompts:      {len(all_prompts)}")
    print(f"Max Requests:       {max_requests}")
    print(f"Request Delay:      {delay_seconds}s")
    print(f"QA Mode:            {qa_mode}")
    print("=" * 90 + "\n")

    eval_out_dir = output_dir or (ROOT_DIR / "artifacts" / "eval")
    eval_out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_filename = f"eval_{provider_name}_{model_name}_{timestamp_str}.jsonl"
    jsonl_path = eval_out_dir / jsonl_filename
    json_filename = f"eval_{provider_name}_{model_name}_{timestamp_str}.json"
    json_path = eval_out_dir / json_filename
    md_filename = f"eval_{provider_name}_{model_name}_{timestamp_str}.md"
    md_path = eval_out_dir / md_filename
    docs_target = docs_file or (ROOT_DIR / "docs" / "EVAL_RESULTS.md")

    records: List[Dict[str, Any]] = []

    def write_disk_artifacts(current_run_status: str) -> Dict[str, Any]:
        """Writes .json, .md, and EVAL_RESULTS.md to disk immediately."""
        cur_summary = compute_eval_summary(
            records=records,
            all_prompts=all_prompts,
            provider_name=provider_name,
            model_name=model_name,
            is_mock=is_mock,
            qa_mode=qa_mode,
            run_status=current_run_status,
            date_str=date_str,
            request_timeout_seconds=req_timeout,
            run_label=run_label,
        )
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(cur_summary, jf, indent=2)
        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write(generate_markdown_report(cur_summary))
        docs_target.parent.mkdir(parents=True, exist_ok=True)
        with open(docs_target, "w", encoding="utf-8") as df:
            df.write(generate_docs_eval_results(cur_summary, json_filename))
        return cur_summary

    # Rule 3 Pre-flight check before a real run
    if not is_mock:
        print(f"[Pre-flight] Performing ping completion test with {provider_name} ({model_name})...")
        try:
            pre_res = active_provider.complete(system="You are a health ping test.", user="Respond with OK")
            if not pre_res or not pre_res.text:
                raise ValueError("Empty completion returned from model")
            print(f"[Pre-flight] Model ping successful in {pre_res.latency_ms}ms.")
        except Exception as exc:
            print(f"[Pre-flight] Pre-flight check failed for {model_name}: {exc}", file=sys.stderr)
            print("[Pre-flight] Saving partial results marked incomplete and halting run.")
            for rem in all_prompts:
                unrun_rec = {
                    "id": rem["id"],
                    "model_used": model_name,
                    "prompt": rem["prompt"],
                    "spec_validated_first_response": None,
                    "playable_at_1": None,
                    "playable_at_3": None,
                    "repair_attempted": False,
                    "repair_succeeded": False,
                    "total_latency_ms": None,
                    "token_usage": None,
                    "cost_estimate": None,
                    "failure_category": "provider_error",
                    "theme_match": None,
                    "objective_match": None,
                    "expect_limitation": bool(rem.get("expect_limitation", False)),
                    "disclosed_limitations_count": 0,
                    "limitation_honesty": None,
                    "prompt_adherence_1to5": None,
                    "final_status": "NOT_RUN",
                    "attempts": 0,
                    "error_code": "MODEL_HTTP_ERROR" if "429" in str(exc) or "quota" in str(exc).lower() else "PREFLIGHT_FAILED",
                    "notes": f"not run (pre-flight failed: {str(exc)[:120]})",
                }
                records.append(unrun_rec)
                with open(jsonl_path, "a", encoding="utf-8") as jf:
                    jf.write(json.dumps(unrun_rec) + "\n")
            summary = write_disk_artifacts("incomplete")
            print_cli_summary(summary)
            return summary

    backend_proc, frontend_proc = ensure_servers_if_needed(qa_mode)
    run_status = "complete"
    quota_stopped = False

    try:
        for idx, p_info in enumerate(all_prompts):
            pid = p_info["id"]
            p_text = p_info["prompt"]
            exp_theme = p_info.get("expected_theme")
            exp_obj = p_info.get("expected_objective_type")
            exp_limit = bool(p_info.get("expect_limitation", False))

            # Rule 3: Request budget check applies per model
            active_model_now = getattr(active_provider, "model_name", model_name)
            current_model_requests = get_model_request_count(active_model_now) if not is_mock else get_model_request_count()
            if current_model_requests + 1 > max_requests:
                print(f"[{pid}] Request budget for model '{active_model_now}' reached ({current_model_requests}/{max_requests}). Stopping run.")
                # Mark current and remaining prompts as not run (budget)
                for rem in all_prompts[idx:]:
                    unrun_rec = {
                        "id": rem["id"],
                        "model_used": getattr(active_provider, "model_name", model_name),
                        "prompt": rem["prompt"],
                        "spec_validated_first_response": None,
                        "playable_at_1": None,
                        "playable_at_3": None,
                        "repair_attempted": False,
                        "repair_succeeded": False,
                        "total_latency_ms": None,
                        "token_usage": None,
                        "cost_estimate": None,
                        "failure_category": "not_run",
                        "theme_match": None,
                        "objective_match": None,
                        "expect_limitation": bool(rem.get("expect_limitation", False)),
                        "disclosed_limitations_count": 0,
                        "limitation_honesty": None,
                        "prompt_adherence_1to5": None,
                        "final_status": "NOT_RUN",
                        "attempts": 0,
                        "error_code": "BUDGET_EXCEEDED",
                        "notes": "not run (budget)",
                    }
                    records.append(unrun_rec)
                    with open(jsonl_path, "a", encoding="utf-8") as jf:
                        jf.write(json.dumps(unrun_rec) + "\n")
                break

            print(f"[{idx+1}/{len(all_prompts)}] Running prompt {pid}: \"{p_text[:60]}...\"")
            t_start = time.time()
            t_ms = 0.0

            # Execute orchestrator in-process
            game_id = str(uuid.uuid4())
            job_store.create_job(game_id, prompt=p_text, max_attempts=3)
            try:
                asyncio.run(run_single_job(game_id))
                t_ms = round((time.time() - t_start) * 1000.0, 1)
            except Exception as exc:
                t_ms = round((time.time() - t_start) * 1000.0, 1)
                exc_str = str(exc)
                if "429" in exc_str or "quota" in exc_str.lower():
                    print(f"[{pid}] Quota 429 encountered during execution: {exc}")
                    quota_stopped = True
                else:
                    print(f"[{pid}] Exception during job execution: {exc}")

            job = job_store.get_job(game_id) or {}
            final_status = job.get("status", "FAILED")
            err_code = job.get("error_code")
            limitations = job.get("limitations") or []
            attempts = job.get("attempt", 1)

            # Check if repair events were emitted (excluding skipped repairs)
            events = event_store.get_events(game_id)
            has_repair_event = any(ev.get("stage") == "REPAIRING" and ev.get("result") != "SKIPPED" for ev in events)

            # Check if this was a quota 429 error (only genuine quota stops the whole run)
            is_quota_429 = False
            if err_code == "MODEL_HTTP_ERROR":
                detail_texts = [ev.get("detail", "") for ev in events]
                detail_texts.append(str(job.get("detail", "")))
                combined_err_text = " ".join(detail_texts).lower()
                if "429" in combined_err_text and any(q in combined_err_text for q in ("quota", "daily", "limit", "exhausted", "insufficient_quota")):
                    is_quota_429 = True

            if is_quota_429:
                quota_stopped = True

            # Analyze artifacts
            art_dir = get_artifacts_dir() / game_id
            spec_v1_exists = (art_dir / "game_ir_v1.json").is_file()
            spec_obj: Optional[Dict[str, Any]] = None
            if spec_v1_exists:
                try:
                    with open(art_dir / "game_ir_v1.json", "r", encoding="utf-8") as f:
                        spec_obj = json.load(f)
                except Exception:
                    pass

            # First-response validation
            if err_code in ("MODEL_HTTP_ERROR", "MODEL_TIMEOUT"):
                first_valid = None
            else:
                first_valid = spec_v1_exists and err_code not in ("SPEC_UNSUPPORTED", "MODEL_OUTPUT_INVALID")

            # QA results per attempt
            qa_att1_path = art_dir / "qa_report_attempt_1.json"
            qa_att1: Optional[Dict[str, Any]] = None
            if qa_att1_path.is_file():
                try:
                    with open(qa_att1_path, "r", encoding="utf-8") as f:
                        qa_att1 = json.load(f)
                except Exception:
                    pass

            playable_at_1 = False
            if qa_att1 and qa_att1.get("overall") == "PASS":
                crit_failed = [c for c in qa_att1.get("checks", []) if not c.get("passed") and c.get("critical", True)]
                if not crit_failed:
                    playable_at_1 = True

            repair_attempted = (attempts > 1) or has_repair_event
            repair_succeeded = repair_attempted and final_status in ("READY", "READY_WITH_WARNINGS")
            playable_at_3 = final_status in ("READY", "READY_WITH_WARNINGS")

            # Determine failure category
            if final_status in ("READY", "READY_WITH_WARNINGS"):
                failure_cat = None
            elif err_code in ("MODEL_HTTP_ERROR", "MODEL_TIMEOUT"):
                failure_cat = "provider_error"
            elif err_code in ("SPEC_UNSUPPORTED", "MODEL_OUTPUT_INVALID", "PROMPT_INVALID"):
                failure_cat = "schema"
            elif err_code == "QA_CRASHED":
                failure_cat = "timeout"
            elif qa_att1:
                failure_cat = classify_qa_failure(qa_att1)
            else:
                failure_cat = "objective"

            # Theme / Objective / Limitations
            theme_match = None
            if exp_theme and spec_obj:
                theme_match = spec_obj.get("theme") == exp_theme

            obj_match = None
            if exp_obj and spec_obj:
                obj_match = spec_obj.get("objective", {}).get("type") == exp_obj

            disclosed_limitations_count = len(limitations)
            lim_honest = (disclosed_limitations_count > 0) if exp_limit else None

            # Token usage & cost
            if is_mock:
                token_usage = "null (mock provider)"
                cost_estimate = "null (mock provider)"
            else:
                token_usage = "null (usage not returned)"
                cost_estimate = "null (zero cost / free tier)"

            active_model_now = getattr(active_provider, "model_name", model_name)
            model_used_here = job.get("model_id") or active_model_now
            rec = {
                "id": pid,
                "model_used": model_used_here,
                "prompt": p_text,
                "spec_validated_first_response": first_valid,
                "playable_at_1": playable_at_1,
                "playable_at_3": playable_at_3,
                "repair_attempted": repair_attempted,
                "repair_succeeded": repair_succeeded,
                "total_latency_ms": t_ms,
                "token_usage": token_usage,
                "cost_estimate": cost_estimate,
                "failure_category": failure_cat,
                "theme_match": theme_match,
                "objective_match": obj_match,
                "expect_limitation": exp_limit,
                "disclosed_limitations_count": disclosed_limitations_count,
                "limitation_honesty": lim_honest,
                "prompt_adherence_1to5": None,
                "final_status": final_status,
                "attempts": attempts,
                "error_code": err_code,
                "notes": p_info.get("notes", ""),
            }
            records.append(rec)

            # Append to .jsonl immediately after each prompt
            with open(jsonl_path, "a", encoding="utf-8") as jf:
                jf.write(json.dumps(rec) + "\n")

            # Write full results to disk after EVERY prompt
            write_disk_artifacts("running" if idx < len(all_prompts) - 1 else run_status)

            print(f"[{pid}] Done: status={final_status}, 1stValid={first_valid}, Play@1={playable_at_1}, Play@3={playable_at_3}, repairs={repair_attempted}/{repair_succeeded}, attempts={attempts}, latency={t_ms}ms")

            if err_code in ("MODEL_HTTP_ERROR", "MODEL_TIMEOUT") and not quota_stopped:
                print(f"[{pid}] Provider error ({err_code}): recorded as provider_error, continuing to next prompt.")

            # Rule 3: Stop run immediately on quota 429
            if quota_stopped:
                print(f"\n[Quota Fast-Fail] Stopping entire evaluation due to quota 429 on prompt {pid}.")
                run_status = "incomplete"
                # Mark remaining prompts as not run
                for rem in all_prompts[idx + 1:]:
                    unrun_rec = {
                        "id": rem["id"],
                        "model_used": getattr(active_provider, "model_name", model_name),
                        "prompt": rem["prompt"],
                        "spec_validated_first_response": None,
                        "playable_at_1": None,
                        "playable_at_3": None,
                        "repair_attempted": False,
                        "repair_succeeded": False,
                        "total_latency_ms": None,
                        "token_usage": None,
                        "cost_estimate": None,
                        "failure_category": "not_run",
                        "theme_match": None,
                        "objective_match": None,
                        "expect_limitation": bool(rem.get("expect_limitation", False)),
                        "disclosed_limitations_count": 0,
                        "limitation_honesty": None,
                        "prompt_adherence_1to5": None,
                        "final_status": "NOT_RUN",
                        "attempts": 0,
                        "error_code": "QUOTA_STOPPED",
                        "notes": "not run (quota stopped)",
                    }
                    records.append(unrun_rec)
                    with open(jsonl_path, "a", encoding="utf-8") as jf:
                        jf.write(json.dumps(unrun_rec) + "\n")
                break

            # Pacing delay between prompts
            if delay_seconds > 0 and idx < len(all_prompts) - 1:
                time.sleep(delay_seconds)

    finally:
        set_custom_provider(None)
        stop_servers(backend_proc, frontend_proc)
        if orig_env_allow_fallback is not None:
            os.environ["AETHER_ALLOW_FALLBACK"] = orig_env_allow_fallback
        else:
            os.environ.pop("AETHER_ALLOW_FALLBACK", None)
        if orig_env_fallbacks is not None:
            os.environ["MODEL_FALLBACKS"] = orig_env_fallbacks
        else:
            os.environ.pop("MODEL_FALLBACKS", None)

    # Write final outputs to disk
    summary = write_disk_artifacts(run_status)

    # Print summary table and request count
    print_cli_summary(summary)
    print(f"\nArtifacts saved:")
    print(f"  - {jsonl_path} (streamed append-only)")
    print(f"  - {json_path}")
    print(f"  - {md_path}")
    print(f"  - {docs_target}")
    # Rule 6: Print total model request count at the end
    print(f"\nTotal Model Requests: {summary.get('total_model_requests', 0)}")

    # Verification: verify that model_used equals configured model for every row
    mismatches = []
    for r in records:
        if r.get("failure_category") != "not_run":
            row_model = r.get("model_used")
            if row_model != model_name:
                mismatches.append(f"Prompt {r.get('id')}: expected '{model_name}', got '{row_model}'")
    if mismatches:
        print("\n[WARNING] Model Mismatch Detected:")
        for m in mismatches:
            print(f"  - {m}")
    else:
        attempted_count = len([r for r in records if r.get('failure_category') != 'not_run'])
        print(f"\n[Verification] model_used equals configured model '{model_name}' for all {attempted_count} attempted rows (0 mismatches).")

    return summary


def compute_eval_summary(
    records: List[Dict[str, Any]],
    all_prompts: List[Dict[str, Any]],
    provider_name: str,
    model_name: str,
    is_mock: bool,
    qa_mode: str,
    run_status: str,
    date_str: str,
    request_timeout_seconds: float = 60.0,
    run_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Computes headline metrics, per-model breakdowns, and summary dictionary."""
    attempted_prompts = [r for r in records if r.get("failure_category") != "not_run"]
    model_response_prompts = [
        r for r in attempted_prompts
        if r.get("spec_validated_first_response") is not None and r.get("failure_category") != "provider_error"
    ]
    model_resp_count = len(model_response_prompts)

    valid_first_count = sum(1 for r in model_response_prompts if r.get("spec_validated_first_response"))
    playable1_count = sum(1 for r in model_response_prompts if r.get("playable_at_1"))
    playable3_count = sum(1 for r in model_response_prompts if r.get("playable_at_3"))

    repairs_attempted_count = sum(1 for r in model_response_prompts if r.get("repair_attempted"))
    repairs_succeeded_count = sum(1 for r in model_response_prompts if r.get("repair_succeeded"))

    latencies = [r["total_latency_ms"] for r in model_response_prompts if isinstance(r.get("total_latency_ms"), (int, float))]
    median_latency = round(statistics.median(latencies), 1) if latencies else 0.0
    min_latency = round(min(latencies), 1) if latencies else 0.0
    max_latency = round(max(latencies), 1) if latencies else 0.0
    mean_latency = round(statistics.mean(latencies), 1) if latencies else 0.0

    theme_evaluated = [r for r in model_response_prompts if r.get("theme_match") is not None]
    theme_match_count = sum(1 for r in theme_evaluated if r.get("theme_match"))

    obj_evaluated = [r for r in model_response_prompts if r.get("objective_match") is not None]
    obj_match_count = sum(1 for r in obj_evaluated if r.get("objective_match"))

    limit_evaluated = [r for r in model_response_prompts if r.get("expect_limitation") is True]
    limit_honest_count = sum(1 for r in limit_evaluated if r.get("limitation_honesty") is True)
    if limit_evaluated:
        limitation_honesty_rate = f"{limit_honest_count}/{len(limit_evaluated)} ({(limit_honest_count / len(limit_evaluated) * 100):.1f}%)"
    else:
        limitation_honesty_rate = "N/A (no limitation prompts)"

    non_limit_disclosed_count = sum(
        1 for r in model_response_prompts
        if not r.get("expect_limitation") and r.get("disclosed_limitations_count", 0) > 0
    )

    total_model_requests = get_model_request_count()

    # Determine models used across all prompts
    models_used = sorted(list(set(
        str(r.get("model_used")) for r in records
        if r.get("model_used") and r.get("failure_category") != "not_run"
    )))
    if len(models_used) > 1:
        run_model_label = "mixed models"
    elif len(models_used) == 1:
        run_model_label = models_used[0]
    else:
        run_model_label = model_name

    # Per-model rates breakdown
    per_model_rates = {}
    for m in models_used:
        m_prompts = [r for r in model_response_prompts if str(r.get("model_used")) == m]
        m_count = len(m_prompts)
        m_valid_first = sum(1 for r in m_prompts if r.get("spec_validated_first_response"))
        m_playable1 = sum(1 for r in m_prompts if r.get("playable_at_1"))
        m_playable3 = sum(1 for r in m_prompts if r.get("playable_at_3"))
        m_rep_att = sum(1 for r in m_prompts if r.get("repair_attempted"))
        m_rep_succ = sum(1 for r in m_prompts if r.get("repair_succeeded"))
        m_lats = [r["total_latency_ms"] for r in m_prompts if isinstance(r.get("total_latency_ms"), (int, float))]
        per_model_rates[m] = {
            "prompts_count": m_count,
            "spec_validated_first_rate": f"{m_valid_first}/{m_count} ({(m_valid_first / m_count * 100 if m_count else 0):.1f}%)",
            "playable_at_1_rate": f"{m_playable1}/{m_count} ({(m_playable1 / m_count * 100 if m_count else 0):.1f}%)",
            "playable_at_3_rate": f"{m_playable3}/{m_count} ({(m_playable3 / m_count * 100 if m_count else 0):.1f}%)",
            "repair_success_rate": f"{m_rep_succ}/{m_rep_att} ({(m_rep_succ / m_rep_att * 100 if m_rep_att else 0):.1f}%)" if m_rep_att else "N/A (0/0)",
            "median_latency_ms": round(statistics.median(m_lats), 1) if m_lats else 0.0,
            "min_latency_ms": round(min(m_lats), 1) if m_lats else 0.0,
            "max_latency_ms": round(max(m_lats), 1) if m_lats else 0.0,
        }

    return {
        "benchmark_date": date_str,
        "provider": provider_name,
        "model": run_model_label,
        "is_mock": is_mock,
        "qa_mode": qa_mode,
        "run_status": run_status,
        "run_label": run_label,
        "request_timeout_seconds": request_timeout_seconds,
        "total_prompts": len(all_prompts),
        "prompts_attempted": len(attempted_prompts),
        "prompts_with_model_response": model_resp_count,
        "spec_validated_first_rate": f"{valid_first_count}/{model_resp_count} ({(valid_first_count / model_resp_count * 100 if model_resp_count else 0):.1f}%)",
        "playable_at_1_rate": f"{playable1_count}/{model_resp_count} ({(playable1_count / model_resp_count * 100 if model_resp_count else 0):.1f}%)",
        "playable_at_3_rate": f"{playable3_count}/{model_resp_count} ({(playable3_count / model_resp_count * 100 if model_resp_count else 0):.1f}%)",
        "repair_success_rate": f"{repairs_succeeded_count}/{repairs_attempted_count} ({(repairs_succeeded_count / repairs_attempted_count * 100 if repairs_attempted_count else 0):.1f}%)" if repairs_attempted_count else "N/A (0/0)",
        "theme_match_rate": f"{theme_match_count}/{len(theme_evaluated)} ({(theme_match_count / len(theme_evaluated) * 100 if theme_evaluated else 0):.1f}%)" if theme_evaluated else "N/A",
        "objective_match_rate": f"{obj_match_count}/{len(obj_evaluated)} ({(obj_match_count / len(obj_evaluated) * 100 if obj_evaluated else 0):.1f}%)" if obj_evaluated else "N/A",
        "limitation_honesty_rate": limitation_honesty_rate,
        "non_limit_disclosed_count": non_limit_disclosed_count,
        "median_latency_ms": median_latency,
        "min_latency_ms": min_latency,
        "max_latency_ms": max_latency,
        "mean_latency_ms": mean_latency,
        "total_model_requests": total_model_requests,
        "models_used": models_used,
        "per_model_rates": per_model_rates,
        "records": records,
    }


def print_cli_summary(summary: Dict[str, Any]) -> None:
    """Prints the evaluation results summary table to stdout."""
    print("\n" + "=" * 100)
    if summary.get("is_mock"):
        print("          MOCK PROVIDER: not a real model, results are not evidence")
        print("=" * 100)
    print("                              EVALUATION RESULTS SUMMARY")
    print("=" * 100)
    print(f"Status:                                  {summary['run_status'].upper()}")
    print(f"Provider / Model:                        {summary['provider']} / {summary['model']}")
    print(f"Total Suite Prompts:                     {summary['total_prompts']}")
    print(f"Prompts Attempted:                       {summary['prompts_attempted']}")
    print(f"Model Responses Received:                {summary['prompts_with_model_response']}")
    print(f"Spec Validated First:                    {summary['spec_validated_first_rate']}")
    print(f"Playable @ Attempt 1:                    {summary['playable_at_1_rate']}")
    print(f"Playable @ Attempt 3:                    {summary['playable_at_3_rate']}")
    print(f"Repair Success Rate:                     {summary['repair_success_rate']}")
    print(f"Theme Match Rate:                        {summary['theme_match_rate']}")
    print(f"Objective Match Rate:                    {summary['objective_match_rate']}")
    print(f"Limitation Honesty Rate (expect=True):   {summary['limitation_honesty_rate']}")
    print(f"Non-Limitation Prompts Disclosing Limits:{summary['non_limit_disclosed_count']} prompt(s)")
    print(f"Latency (Median / Min / Max):            {summary['median_latency_ms']} ms / {summary['min_latency_ms']} ms / {summary['max_latency_ms']} ms")
    print("=" * 100)

    print(f"\n{'ID':<12} | {'Status':<6} | {'1stVal':<6} | {'Play@1':<6} | {'Play@3':<6} | {'Rep':<4} | {'Att':<3} | {'Cat':<11} | {'Latency':<8} | {'Prompt':<30}")
    print("-" * 105)
    for r in summary["records"]:
        pid = r["id"]
        st = r["final_status"]
        v1 = "PASS" if r["spec_validated_first_response"] else ("FAIL" if r["spec_validated_first_response"] is False else "—")
        p1 = "PASS" if r["playable_at_1"] else ("FAIL" if r["playable_at_1"] is False else "—")
        p3 = "PASS" if r["playable_at_3"] else ("FAIL" if r["playable_at_3"] is False else "—")
        rep = "SUCC" if r["repair_succeeded"] else ("ATT" if r["repair_attempted"] else "NO")
        att = str(r["attempts"])
        cat = r["failure_category"] or "none"
        lat = f"{r['total_latency_ms']:.0f}ms" if r["total_latency_ms"] is not None else "—"
        prompt_snippet = r["prompt"][:30]
        print(f"{pid:<12} | {st:<6} | {v1:<6} | {p1:<6} | {p3:<6} | {rep:<4} | {att:<3} | {cat:<11} | {lat:<8} | {prompt_snippet:<30}")
    print("=" * 105)


def generate_markdown_report(summary: Dict[str, Any]) -> str:
    """Generates detailed markdown content for eval artifact."""
    mock_header = ""
    if summary.get("is_mock"):
        mock_header = "> **MOCK PROVIDER: not a real model, results are not evidence**\n\n"

    label_header = ""
    if summary.get("run_label"):
        label_header = f"> **{summary['run_label']}**\n\n"

    lines = [
        f"# AETHER Full-Pipeline Evaluation Report: {summary['provider']} ({summary['model']})",
        "",
        mock_header,
        label_header,
        f"- **Benchmark Date:** {summary['benchmark_date']}",
        f"- **Provider:** `{summary['provider']}`",
        f"- **Model ID:** `{summary['model']}`",
        f"- **QA Execution Mode:** `{summary['qa_mode']}`",
        f"- **Run Status:** `{summary['run_status']}`",
        f"- **Request Timeout:** {summary.get('request_timeout_seconds', 60.0)} s",
        f"- **Sample Size:** {summary['total_prompts']} prompt(s)",
        f"- **Total Model Requests:** {summary['total_model_requests']}",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Rate / Value | Note |",
        "|---|---|---|",
        f"| **First-Response Spec Validation** | **{summary['spec_validated_first_rate']}** | Evaluated over prompts with model response |",
        f"| **Playable @ Attempt 1** | **{summary['playable_at_1_rate']}** | Initial build passed all critical QA |",
        f"| **Playable @ Attempt 3** | **{summary['playable_at_3_rate']}** | Pass after up to 2 repair iterations |",
        f"| **Repair Success Rate** | **{summary['repair_success_rate']}** | Repairs that transitioned failing game to READY |",
        f"| **Theme Match Rate** | **{summary['theme_match_rate']}** | Faithful to specified theme |",
        f"| **Objective Match Rate** | **{summary['objective_match_rate']}** | Faithful to specified objective |",
        f"| **Limitation Honesty Rate** | **{summary['limitation_honesty_rate']}** | Prompts with expect_limitation=True |",
        f"| **Non-Limitation Disclosed** | **{summary['non_limit_disclosed_count']} prompt(s)** | Disclosed limitations on standard prompts |",
        f"| **Median Latency** | **{summary['median_latency_ms']} ms** | Model response prompts only |",
        f"| **Min Latency** | **{summary['min_latency_ms']} ms** | Model response prompts only |",
        f"| **Max Latency** | **{summary['max_latency_ms']} ms** | Model response prompts only |",
        "",
        "## Per-Prompt Evaluation Results",
        "",
        "| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category | Theme | Obj | Limit | Adherence (1-5) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in summary["records"]:
        v1 = "✅" if r["spec_validated_first_response"] else ("❌" if r["spec_validated_first_response"] is False else "—")
        p1 = "✅" if r["playable_at_1"] else ("❌" if r["playable_at_1"] is False else "—")
        p3 = "✅" if r["playable_at_3"] else ("❌" if r["playable_at_3"] is False else "—")
        rep = "Succ" if r["repair_succeeded"] else ("Att" if r["repair_attempted"] else "No")
        att = str(r["attempts"])
        cat = r["failure_category"] or "none"
        lat = f"{r['total_latency_ms']:.0f}ms" if r["total_latency_ms"] is not None else "—"
        thm = "✅" if r["theme_match"] is True else ("❌" if r["theme_match"] is False else "—")
        obj = "✅" if r["objective_match"] is True else ("❌" if r["objective_match"] is False else "—")
        lim = "✅" if r["limitation_honesty"] is True else ("❌" if r["limitation_honesty"] is False else "—")
        clean_prompt = r["prompt"].replace("|", "\\|")

        lines.append(
            f"| `{r['id']}` | {clean_prompt} | `{r['final_status']}` | {v1} | {p1} | {p3} | {rep} | {att} | {lat} | `{cat}` | {thm} | {obj} | {lim} | |"
        )

    lines.extend([
        "",
        "## Check Definitions & Failure Taxonomy",
        "- **schema**: GameIR failed validation rules or schema constraints.",
        "- **rendering**: Game canvas failed to mount or Phaser QA hook not ready.",
        "- **interaction**: Player movement, velocity consistency, attack response, or controls failed.",
        "- **objective**: Win condition unreachable, score progress halted, or playability thresholds failed.",
        "- **restart**: Scene restart failed to restore fresh initial playing state.",
        "- **timeout**: Planner, QA execution, or repair timed out.",
        "- **provider_error**: Model HTTP error, quota 429, or network disconnect.",
        "- **not_run**: Prompt omitted due to request budget or quota fast-fail.",
    ])

    return "\n".join(lines) + "\n"


def generate_docs_eval_results(summary: Dict[str, Any], json_artifact_name: str) -> str:
    """Generates the content for docs/EVAL_RESULTS.md."""
    banner = ""
    if summary.get("is_mock"):
        banner = "> **MOCK PROVIDER: not a real model, results are not evidence**\n\n"

    lines = [
        "# AETHER Pipeline Evaluation Results",
        "",
        banner,
        f"> **Generated:** {summary['benchmark_date']}  ",
        f"> **Provider:** `{summary['provider']}`  ",
        f"> **Model ID:** `{summary['model']}`  ",
        f"> **Artifact:** `artifacts/eval/{json_artifact_name}`  ",
        f"> **Repair Limit:** Max 2 repairs (3 test runs)  ",
        f"> **Total Model Requests:** {summary['total_model_requests']}",
        "",
        "## Executive Summary",
        "",
        "| Evaluation Metric | Rate / Value | Denominator Scope |",
        "|---|---|---|",
        f"| **First-Response Validation Rate** | **{summary['spec_validated_first_rate']}** | Prompts that received model response |",
        f"| **Playable @ Attempt 1** | **{summary['playable_at_1_rate']}** | Initial build passed all critical QA |",
        f"| **Playable @ Attempt 3** | **{summary['playable_at_3_rate']}** | Reached READY within repair limit |",
        f"| **Repair Success Rate** | **{summary['repair_success_rate']}** | Successful repairs over repair attempts |",
        f"| **Theme Fidelity** | **{summary['theme_match_rate']}** | Matching target prompt theme |",
        f"| **Objective Fidelity** | **{summary['objective_match_rate']}** | Matching target objective type |",
        f"| **Limitation Honesty** | **{summary['limitation_honesty_rate']}** | Prompts with expect_limitation=True |",
        f"| **Non-Limitation Disclosed** | **{summary['non_limit_disclosed_count']} prompt(s)** | Disclosed limitations on standard prompts |",
        f"| **Median Latency** | **{summary['median_latency_ms']} ms** | Model response prompts only |",
        f"| **Min Latency** | **{summary['min_latency_ms']} ms** | Model response prompts only |",
        f"| **Max Latency** | **{summary['max_latency_ms']} ms** | Model response prompts only |",
    ]

    per_model = summary.get("per_model_rates", {})
    if len(per_model) > 1:
        lines.extend([
            "",
            "## Per-Model Rates Breakdown",
            "",
            "| Model | Prompts | First Valid | Playable@1 | Playable@3 | Repair Success | Median Latency |",
            "|---|---|---|---|---|---|---|",
        ])
        for m_name, m_stats in per_model.items():
            lines.append(
                f"| `{m_name}` | {m_stats['prompts_count']} | {m_stats['spec_validated_first_rate']} | {m_stats['playable_at_1_rate']} | {m_stats['playable_at_3_rate']} | {m_stats['repair_success_rate']} | {m_stats['median_latency_ms']}ms |"
            )

    lines.extend([
        "",
        "## Per-Prompt Evaluation Table",
        "",
        "| ID | Model | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category | Adherence (1-5) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])

    for r in summary["records"]:
        v1 = "✅" if r["spec_validated_first_response"] else ("❌" if r["spec_validated_first_response"] is False else "—")
        p1 = "✅" if r["playable_at_1"] else ("❌" if r["playable_at_1"] is False else "—")
        p3 = "✅" if r["playable_at_3"] else ("❌" if r["playable_at_3"] is False else "—")
        rep = "Succ" if r["repair_succeeded"] else ("Att" if r["repair_attempted"] else "No")
        att = str(r["attempts"])
        cat = r["failure_category"] or "none"
        lat = f"{r['total_latency_ms']:.0f}ms" if r["total_latency_ms"] is not None else "—"
        clean_p = r["prompt"].replace("|", "\\|")
        m_used = r.get("model_used") or summary.get("model", "")
        lines.append(f"| `{r['id']}` | `{m_used}` | {clean_p} | `{r['final_status']}` | {v1} | {p1} | {p3} | {rep} | {att} | {lat} | `{cat}` | |")

    lines.extend([
        "",
        "## How to Re-Run with Another Provider",
        "",
        "To evaluate against another provider (e.g. Gemini 2.5 Flash, Groq, Ollama, or OpenAI):",
        "",
        "1. Configure provider credentials in `.env` (or set environment variables for the process):",
        "   ```bash",
        "   MODEL_PROVIDER=openai_compat",
        "   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai",
        "   OPENAI_API_KEY=your_key_here",
        "   OPENAI_MODEL=gemini-2.5-flash",
        "   ```",
        "",
        "2. Run the evaluation harness with the explicit `--real` flag:",
        "   ```bash",
        "   python scripts/run_eval.py --real --max-requests 18 --delay 13",
        "   ```",
        "",
        "3. Filenames and records automatically incorporate the provider and model names:",
        "   - Results will be saved to `artifacts/eval/eval_<provider>_<model>_<timestamp>.json`",
        "   - Separate providers never overwrite each other's timestamped artifacts.",
    ])

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="AETHER Full-Pipeline Evaluation Harness (Phase 5)")
    parser.add_argument("--real", action="store_true", help="Explicitly allow running with a real model provider")
    parser.add_argument("--max-requests", type=int, default=18, help="Maximum request budget across planner and repair (default: 18)")
    parser.add_argument("--delay", type=float, default=13.0, help="Pacing delay in seconds between prompts (default: 13.0)")
    parser.add_argument("--qa-mode", choices=["real", "fake"], default="fake", help="QA execution mode: 'real' (browser Playwright) or 'fake' (default: fake)")
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated prompt IDs to evaluate (e.g. p01,p05,s01)")
    parser.add_argument("--prompt", type=str, default=None, help="Ad-hoc custom prompt to evaluate")
    parser.add_argument("--prompts-file", type=Path, default=None, help="Path to base prompts JSON")
    parser.add_argument("--stress-file", type=Path, default=None, help="Path to stress prompts JSON")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for eval artifacts")
    parser.add_argument("--docs-file", type=Path, default=None, help="Path to write docs/EVAL_RESULTS.md")
    parser.add_argument("--allow-fallback", action="store_true", default=False, help="Allow automatic model fallback during evaluation (disabled by default)")
    parser.add_argument("--timeout", type=float, default=None, help="Model request timeout in seconds (or MODEL_TIMEOUT_SECONDS env var; default 60.0s)")
    parser.add_argument("--run-label", type=str, default=None, help="Descriptive label for this evaluation run")

    args = parser.parse_args()

    filter_ids = [x.strip() for x in args.ids.split(",")] if args.ids else None

    run_evaluation(
        real_flag=args.real,
        max_requests=args.max_requests,
        delay_seconds=args.delay,
        qa_mode=args.qa_mode,
        prompts_file=args.prompts_file,
        stress_file=args.stress_file,
        filter_ids=filter_ids,
        custom_prompt=args.prompt,
        output_dir=args.output_dir,
        docs_file=args.docs_file,
        allow_fallback=args.allow_fallback,
        timeout=args.timeout,
        run_label=args.run_label,
    )


if __name__ == "__main__":
    main()
