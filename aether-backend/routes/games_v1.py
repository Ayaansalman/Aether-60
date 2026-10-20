"""
Public v1 Game Generation API Routes.
Exposes /api/v1/games, /api/v1/health, and artifact downloads.
Conforms to Sections 4.4, 4.5, 6, and 9.1 of the AETHER Engineering Specification.
"""

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status
from fastapi.responses import FileResponse, JSONResponse

from providers.factory import get_provider
from schemas.api import (
    GameCreateRequest,
    GameCreateResponse,
    GameEvent,
    GameStatusResponse,
    HealthResponse,
    QASummary,
)
from services import event_store, job_store
from services.orchestrator import get_artifacts_dir, trigger_queue_processing

router = APIRouter()

ALLOWED_ARTIFACT_NAMES = {
    "game_ir_v1.json",
    "game_ir_v2.json",
    "game_ir_v3.json",
    "agent_trace.jsonl",
    "qa_report_attempt_1.json",
    "qa_report_attempt_2.json",
    "qa_report_attempt_3.json",
    "screenshot.png",
    "qa_screenshot.png",
}


def _validate_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


# -------------------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------------------
@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health():
    """Returns system status, active provider, model ID, and boolean key status."""
    provider = get_provider()
    provider_name = "mock"
    if type(provider).__name__ == "OpenAICompatProvider":
        provider_name = "openai_compat"

    model_name = getattr(provider, "model_name", "") or "mock-planner-v1"
    has_key = bool(os.getenv("MODEL_API_KEY", "").strip())

    from providers.base import get_model_request_count, get_model_requests_by_model
    from providers.openai_compat import get_process_fallback_history

    fallback_hist = getattr(provider, "fallback_history", []) or get_process_fallback_history()
    fallback_events_str = [
        fb.get("event") or f"fallback: {fb.get('from_model')} -> {fb.get('to_model')} ({fb.get('reason')})"
        for fb in fallback_hist
    ]

    return HealthResponse(
        status="ok",
        provider=provider_name,
        model=model_name,
        has_api_key=has_key,
        model_requests=get_model_request_count(),
        model_used=model_name,
        fallback_events=fallback_events_str,
        model_requests_by_model=get_model_requests_by_model(),
    )


# -------------------------------------------------------------------------
# Game Submission Endpoint (POST /api/v1/games -> 202 Accepted)
# -------------------------------------------------------------------------
@router.post(
    "/games",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GameCreateResponse,
    tags=["Games v1"],
)
async def create_game(
    request: GameCreateRequest,
    background_tasks: BackgroundTasks,
):
    """Submits a natural language prompt, stores job, and queues generation."""
    clean_prompt = request.prompt.strip()
    if not clean_prompt:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Prompt cannot be empty", "error_code": "PROMPT_INVALID"},
        )

    if len(clean_prompt) > 1200:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": "Prompt length exceeds maximum allowed 1200 characters",
                "error_code": "PROMPT_INVALID",
            },
        )

    game_id = str(uuid.uuid4())

    # 1. Persist in SQLite before processing starts
    job_store.create_job(game_id=game_id, prompt=clean_prompt)

    # 2. Record initial event
    event_store.add_event(
        game_id=game_id,
        stage="QUEUED",
        result="SUCCESS",
        detail="Job accepted and placed in execution queue",
        attempt=1,
    )

    # 3. Schedule background worker
    background_tasks.add_task(trigger_queue_processing)

    return GameCreateResponse(
        game_id=game_id,
        status="QUEUED",
        stage="QUEUED",
        message="Job accepted and queued for processing",
    )


# -------------------------------------------------------------------------
# Status Endpoint (GET /api/v1/games/{id})
# -------------------------------------------------------------------------
@router.get(
    "/games/{game_id}",
    response_model=GameStatusResponse,
    tags=["Games v1"],
)
async def get_game_status(game_id: str):
    """Retrieves current execution status, QA summary, and error information."""
    job = job_store.get_job(game_id)
    if not job:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    qa_summary = None
    if job.get("qa_summary"):
        qa_summary = QASummary(**job["qa_summary"])

    return GameStatusResponse(
        game_id=job["game_id"],
        prompt=job["prompt"],
        status=job["status"],
        stage=job["stage"],
        attempt=job["attempt"],
        max_attempts=job["max_attempts"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        game_url=job.get("game_url"),
        qa_summary=qa_summary,
        error_code=job.get("error_code"),
        limitations=job.get("limitations") or [],
    )


# -------------------------------------------------------------------------
# Spec Endpoint (GET /api/v1/games/{id}/spec)
# -------------------------------------------------------------------------
@router.get("/games/{game_id}/spec", tags=["Games v1"])
async def get_game_spec(game_id: str):
    """Returns validated GameIR specification for a game."""
    from services.game_registry import get_registered_spec
    reg_spec = get_registered_spec(game_id)
    if reg_spec:
        return reg_spec

    job = job_store.get_job(game_id)
    if not job:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    spec_json = job.get("spec_json")
    if not spec_json:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Game specification not yet available", "error_code": "SPEC_UNSUPPORTED"},
        )

    try:
        return json.loads(spec_json)
    except Exception:
        return spec_json


# -------------------------------------------------------------------------
# QA Report Endpoint (GET /api/v1/games/{id}/qa)
# -------------------------------------------------------------------------
@router.get("/games/{game_id}/qa", tags=["Games v1"])
async def get_game_qa_report(game_id: str):
    """Returns latest Playwright QA report for a game."""
    job = job_store.get_job(game_id)
    if not job:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    latest_qa = job.get("latest_qa_json")
    if not latest_qa:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "QA report not yet available"},
        )

    try:
        return json.loads(latest_qa)
    except Exception:
        return latest_qa


# -------------------------------------------------------------------------
# Lifecycle Events Endpoint (GET /api/v1/games/{id}/events)
# -------------------------------------------------------------------------
@router.get(
    "/games/{game_id}/events",
    response_model=List[GameEvent],
    tags=["Games v1"],
)
async def get_game_events(game_id: str):
    """Returns ordered lifecycle events for a game."""
    job = job_store.get_job(game_id)
    if not job:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Game not found", "error_code": "GAME_NOT_FOUND"},
        )

    events = event_store.get_events(game_id)
    return [GameEvent(**e) for e in events]


# -------------------------------------------------------------------------
# Safe Artifact Download Endpoint (GET /api/v1/games/{id}/artifacts/{name})
# -------------------------------------------------------------------------
@router.get("/games/{game_id}/artifacts/{name}", tags=["Games v1"])
async def download_game_artifact(game_id: str, name: str):
    """Safely serves whitelisted generation artifacts."""
    if not _validate_uuid(game_id):
        raise HTTPException(status_code=400, detail="Invalid game ID format")

    # Whitelist filename check and prevent traversal
    clean_name = os.path.basename(name)
    is_allowed = clean_name in ALLOWED_ARTIFACT_NAMES or (
        clean_name.endswith(".png") and re.match(r"^[a-zA-Z0-9_\-\.]+\.png$", clean_name)
    )

    if not is_allowed:
        raise HTTPException(status_code=403, detail="Requested artifact name is not permitted")

    file_path = get_artifacts_dir() / game_id / clean_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found")

    return FileResponse(path=str(file_path), filename=clean_name)
