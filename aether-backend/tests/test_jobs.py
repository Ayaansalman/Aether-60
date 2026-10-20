"""
Tests for API v1 Endpoints, SQLite Job Store, and Event Store.
Conforms to Phase 1 Acceptance Criteria.
"""

import os
import uuid
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from schemas.api import GameCreateRequest
from services import event_store, job_store


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
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


def test_job_and_event_store_crud(tmp_path):
    """Verifies SQLite job persistence, event ordering, and updates."""
    game_id = str(uuid.uuid4())
    job = job_store.create_job(game_id, prompt="A spooky wizard quest")

    assert job["game_id"] == game_id
    assert job["prompt"] == "A spooky wizard quest"
    assert job["status"] == "QUEUED"
    assert job["stage"] == "QUEUED"
    assert job["attempt"] == 1
    assert job["max_attempts"] == 3

    # Append events
    e1 = event_store.add_event(game_id, stage="QUEUED", result="SUCCESS", detail="Enqueued")
    e2 = event_store.add_event(game_id, stage="PLANNING", result="START", detail="Planning")
    events = event_store.get_events(game_id)
    assert len(events) == 2
    assert events[0]["stage"] == "QUEUED"
    assert events[1]["stage"] == "PLANNING"

    # Update job
    updated = job_store.update_job(
        game_id,
        status="READY",
        stage="TESTING",
        game_url=f"http://localhost:5173/play/{game_id}",
        qa_summary={"passed": 5, "failed": 0, "critical_failed": []},
    )
    assert updated is not None
    assert updated["status"] == "READY"
    assert updated["stage"] == "TESTING"
    assert updated["qa_summary"]["passed"] == 5


def test_restart_recovery_marks_non_terminal_jobs():
    """Startup recovery must transition any non-terminal job to FAILED (interrupted by restart)."""
    id_queued = str(uuid.uuid4())
    id_planning = str(uuid.uuid4())
    id_ready = str(uuid.uuid4())
    id_failed = str(uuid.uuid4())

    job_store.create_job(id_queued, "prompt 1")
    job_store.create_job(id_planning, "prompt 2")
    job_store.create_job(id_ready, "prompt 3")
    job_store.create_job(id_failed, "prompt 4")

    job_store.update_job(id_planning, status="PLANNING", stage="PLANNING")
    job_store.update_job(id_ready, status="READY", stage="TESTING")
    job_store.update_job(id_failed, status="FAILED", stage="PLANNING", error_code="MODEL_TIMEOUT")

    # Run restart recovery
    interrupted = job_store.mark_interrupted_jobs_on_startup()
    assert set(interrupted) == {id_queued, id_planning}

    # Verify statuses
    j1 = job_store.get_job(id_queued)
    j2 = job_store.get_job(id_planning)
    j3 = job_store.get_job(id_ready)
    j4 = job_store.get_job(id_failed)

    assert j1 is not None
    assert j2 is not None
    assert j3 is not None
    assert j4 is not None

    assert j1["status"] == "FAILED"
    assert j1["error_code"] == "INTERNAL_ERROR"
    assert j2["status"] == "FAILED"
    assert j2["error_code"] == "INTERNAL_ERROR"
    assert j3["status"] == "READY"
    assert j4["status"] == "FAILED"
    assert j4["error_code"] == "MODEL_TIMEOUT"


def test_api_health_endpoint():
    """Health check returns status, provider, model ID, and boolean key status."""
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["provider"] in ("mock", "openai_compat")
    assert "model" in data
    assert isinstance(data["has_api_key"], bool)


def test_api_post_game_validation():
    """POST /api/v1/games rejects empty prompts and prompts exceeding 1200 characters."""
    client = TestClient(app)

    # Empty prompt
    resp_empty = client.post("/api/v1/games", json={"prompt": "   "})
    assert resp_empty.status_code == 400
    assert resp_empty.json()["error_code"] == "PROMPT_INVALID"

    # Oversized prompt (>1200 characters)
    oversized = "a" * 1205
    resp_over = client.post("/api/v1/games", json={"prompt": oversized})
    assert resp_over.status_code == 400
    assert resp_over.json()["error_code"] == "PROMPT_INVALID"

    # Valid prompt returns HTTP 202 Accepted
    resp_valid = client.post("/api/v1/games", json={"prompt": "valid wizard game"})
    assert resp_valid.status_code == 202
    data = resp_valid.json()
    assert "game_id" in data
    assert data["status"] == "QUEUED"


def test_api_get_game_status_and_not_found():
    """GET /api/v1/games/{id} returns full job state or 404 GAME_NOT_FOUND."""
    client = TestClient(app)

    # Non-existent ID
    resp_404 = client.get(f"/api/v1/games/{uuid.uuid4()}")
    assert resp_404.status_code == 404
    assert resp_404.json()["error_code"] == "GAME_NOT_FOUND"

    # Existing job
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "Wizard adventure")
    job_store.update_job(
        gid,
        status="PLANNING",
        stage="PLANNING",
        limitations=["2D top-down only"],
    )

    resp_ok = client.get(f"/api/v1/games/{gid}")
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["game_id"] == gid
    assert data["status"] == "PLANNING"
    assert data["limitations"] == ["2D top-down only"]


def test_api_spec_qa_and_events_endpoints(tmp_path):
    """GET /spec, /qa, and /events routes return structured outputs."""
    client = TestClient(app)
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "Space defender")

    # Before spec/QA are available
    assert client.get(f"/api/v1/games/{gid}/spec").status_code == 404
    assert client.get(f"/api/v1/games/{gid}/qa").status_code == 404

    # Add spec and QA
    spec_data = {"title": "Space Defender", "genre": "arena_survival"}
    qa_data = {"overall": "PASS", "checks": []}
    job_store.update_job(
        gid,
        spec_json=str(spec_data).replace("'", '"'),
        latest_qa_json=str(qa_data).replace("'", '"'),
    )
    event_store.add_event(gid, stage="QUEUED", result="SUCCESS", detail="Queued")
    event_store.add_event(gid, stage="PLANNING", result="SUCCESS", detail="Planned")

    assert client.get(f"/api/v1/games/{gid}/spec").status_code == 200
    assert client.get(f"/api/v1/games/{gid}/qa").status_code == 200

    events_resp = client.get(f"/api/v1/games/{gid}/events")
    assert events_resp.status_code == 200
    events = events_resp.json()
    assert len(events) == 2
    assert events[0]["stage"] == "QUEUED"
    assert events[1]["stage"] == "PLANNING"


def test_safe_artifact_download(tmp_path):
    """Safe artifact download accepts whitelisted files and blocks path traversal."""
    client = TestClient(app)
    gid = str(uuid.uuid4())
    job_dir = tmp_path / "artifacts" / gid
    job_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy artifact
    spec_file = job_dir / "game_ir_v1.json"
    spec_file.write_text('{"title": "Test"}', encoding="utf-8")

    # Whitelisted file succeeds
    resp_ok = client.get(f"/api/v1/games/{gid}/artifacts/game_ir_v1.json")
    assert resp_ok.status_code == 200

    # Non-whitelisted file blocked
    resp_forbidden = client.get(f"/api/v1/games/{gid}/artifacts/secret.txt")
    assert resp_forbidden.status_code == 403

    # Path traversal blocked
    resp_traversal = client.get(f"/api/v1/games/{gid}/artifacts/../test_app.db")
    assert resp_traversal.status_code in (400, 403, 404)
