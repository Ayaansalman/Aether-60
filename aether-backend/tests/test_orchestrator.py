"""
Tests for Orchestrator State Machine and Worker Execution.
Conforms to Phase 1 Acceptance Criteria.
"""

import asyncio
import json
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from providers.base import ProviderError
from schemas.game_ir import GameIR
from services import event_store, job_store
from services.orchestrator import (
    get_artifacts_dir,
    run_single_job,
    trigger_queue_processing,
)
from services.planner import PlanResult


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Sets up an isolated SQLite database and artifacts directory for each test."""
    test_db = tmp_path / "test_app.db"
    test_artifacts = tmp_path / "artifacts"
    test_artifacts.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AETHER_DB_PATH", str(test_db))
    monkeypatch.setenv("AETHER_ARTIFACTS_DIR", str(test_artifacts))
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    job_store.init_job_store(test_db)
    event_store.init_event_store(test_db)
    return {"db": test_db, "artifacts": test_artifacts}


@pytest.mark.anyio
async def test_orchestrator_happy_path(tmp_path):
    """Full lifecycle walk from QUEUED to READY with mock provider and fake QA."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "a spooky wizard collecting crystals")

    await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "READY"
    assert job["stage"] == "TESTING"
    assert job["error_code"] is None
    assert job["spec_json"] is not None
    assert job["game_url"] == f"http://localhost:5173/play/{gid}"
    assert job["qa_summary"]["passed"] > 0
    assert len(job["qa_summary"]["critical_failed"]) == 0

    # Verify artifacts
    job_dir = get_artifacts_dir() / gid
    assert (job_dir / "game_ir_v1.json").exists()
    assert (job_dir / "qa_report_attempt_1.json").exists()
    assert (job_dir / "agent_trace.jsonl").exists()

    # Verify lifecycle events
    events = event_store.get_events(gid)
    stages = [e["stage"] for e in events]
    assert "PLANNING" in stages
    assert "VALIDATING_SPEC" in stages
    assert "BUILDING" in stages
    assert "TESTING" in stages


@pytest.mark.anyio
async def test_orchestrator_provider_timeout():
    """Provider timeout marks job FAILED with MODEL_TIMEOUT."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "timeout prompt")

    timeout_result = PlanResult(
        ok=False,
        errors=["Model request timed out after 30s"],
        error_code="MODEL_TIMEOUT",
    )

    with patch("services.orchestrator.plan_game", return_value=timeout_result):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "MODEL_TIMEOUT"

    events = event_store.get_events(gid)
    failed_event = [e for e in events if e["result"] == "FAILED"][0]
    assert "MODEL_TIMEOUT" in job["error_code"] or "timeout" in failed_event["detail"].lower()


@pytest.mark.anyio
async def test_orchestrator_model_output_invalid():
    """Unparseable model output marks job FAILED with MODEL_OUTPUT_INVALID."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "gibberish prompt")

    invalid_result = PlanResult(
        ok=False,
        errors=["Model output could not be parsed into JSON"],
        error_code="MODEL_OUTPUT_INVALID",
    )

    with patch("services.orchestrator.plan_game", return_value=invalid_result):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "MODEL_OUTPUT_INVALID"


from services.validator import ValidationResult

@pytest.mark.anyio
async def test_orchestrator_spec_unsupported():
    """Invalid GameIR specification schema marks job FAILED with SPEC_UNSUPPORTED."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "unsupported spec prompt")

    invalid_val = ValidationResult(ok=False, spec=None, errors=["Player move_speed 999 exceeds max 400"])
    with patch("services.orchestrator.validate_game_ir", return_value=invalid_val):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "SPEC_UNSUPPORTED"


@pytest.mark.anyio
async def test_orchestrator_qa_crash(monkeypatch):
    """QA suite crash or subprocess failure marks job FAILED with QA_CRASHED."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "qa crashing prompt")

    # Force real QA mode and mock failure
    monkeypatch.setenv("QA_MODE", "real")

    mock_process = MagicMock()
    mock_process.stdout = "FATAL: Playwright browser failed to launch"
    mock_process.returncode = 1

    with patch("subprocess.run", return_value=mock_process):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "QA_CRASHED"


@pytest.mark.anyio
async def test_orchestrator_concurrency_queueing():
    """
    Multiple submitted jobs wait in QUEUED and execute sequentially under concurrency limit 1.
    All jobs reach terminal states, no stuck jobs.
    """
    gids = [str(uuid.uuid4()) for _ in range(3)]
    for i, gid in enumerate(gids):
        job_store.create_job(gid, f"Prompt {i+1}")

    # Process all jobs in queue
    await trigger_queue_processing()

    for gid in gids:
        job = job_store.get_job(gid)
        assert job is not None
        assert job["status"] == "READY"
        assert job["stage"] == "TESTING"

    # Queue should now be completely drained
    assert job_store.get_next_queued_job() is None


@pytest.mark.anyio
async def test_orchestrator_no_stuck_jobs_on_fatal_exception():
    """Any unhandled exception guarantees terminal FAILED status with INTERNAL_ERROR."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "fatal crash test")

    with patch("services.orchestrator.plan_game", side_effect=RuntimeError("System out of memory")):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "INTERNAL_ERROR"


@pytest.mark.anyio
async def test_orchestrator_failing_qa_stores_failed_checks_in_report_and_events(tmp_path, monkeypatch):
    """
    Verifies that QA execution capturing output preserves failing check IDs in:
    1. qa_report_attempt_N.json artifact file
    2. job_store qa_summary ('critical_failed')
    3. event_store events table ('TESTING' stage with 'FAILED' result containing failed check IDs)
    """
    monkeypatch.setenv("AETHER_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.setenv("QA_MODE", "real")

    gid = str(uuid.uuid4())
    job_store.create_job(gid, "failing qa check test")

    failing_report = {
        "url": f"http://localhost:5173/play/{gid}?test=1",
        "overall": "FAIL",
        "checks": [
            {"id": "canvas_mounted", "passed": True, "critical": True, "patchable": False},
            {"id": "hook_ready", "passed": True, "critical": True, "patchable": False},
            {"id": "idle_survival_min_seconds", "passed": False, "critical": True, "patchable": True, "message": "Player survived 0.4s < 3.0s"},
            {"id": "flee_bot_survives", "passed": False, "critical": True, "patchable": True, "message": "Flee bot died after 0.5s"},
        ],
        "page_errors": [],
        "screenshot_path": str(tmp_path / "screenshot.png"),
        "repair_recommended": True,
    }

    mock_proc = MagicMock()
    mock_proc.stdout = json.dumps(failing_report)
    mock_proc.returncode = 1

    with patch("subprocess.run", return_value=mock_proc):
        with patch("services.orchestrator.propose_repair", side_effect=RuntimeError("stop after first QA")):
            try:
                await run_single_job(gid)
            except RuntimeError:
                pass

    # 1. Assert QA report artifact was saved and contains failed checks
    report_file = tmp_path / gid / "qa_report_attempt_1.json"
    assert report_file.exists(), "qa_report_attempt_1.json must be persisted"
    with open(report_file, "r", encoding="utf-8") as f:
        saved_report = json.load(f)
    saved_failed_ids = [c["id"] for c in saved_report["checks"] if not c["passed"]]
    assert saved_failed_ids == ["idle_survival_min_seconds", "flee_bot_survives"]

    # 2. Assert job_store recorded critical_failed IDs in qa_summary
    job = job_store.get_job(gid)
    assert job is not None
    qa_summary = job.get("qa_summary", {})
    assert "idle_survival_min_seconds" in qa_summary.get("critical_failed", [])
    assert "flee_bot_survives" in qa_summary.get("critical_failed", [])

    # 3. Assert event_store recorded the failed checks in TESTING FAILED event detail
    events = event_store.get_events(gid)
    testing_fail_events = [e for e in events if e["stage"] == "TESTING" and e["result"] == "FAILED"]
    assert len(testing_fail_events) >= 1
    assert "idle_survival_min_seconds" in testing_fail_events[0]["detail"]
    assert "flee_bot_survives" in testing_fail_events[0]["detail"]
