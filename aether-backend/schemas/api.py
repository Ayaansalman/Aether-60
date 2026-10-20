"""
API Request and Response Models.
Conforms to Sections 4.4, 4.5, 6, and 9.1 of the AETHER Engineering Specification.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GameCreateRequest(BaseModel):
    """Payload for submitting a prompt to generate a new game."""
    prompt: str = Field(
        ...,
        description="Natural language game design prompt (1-1200 chars)"
    )


class GameCreateResponse(BaseModel):
    """Response returned upon successfully queuing a generation job (HTTP 202)."""
    game_id: str
    status: str = "QUEUED"
    stage: str = "QUEUED"
    message: str = "Job accepted and queued for processing"


class QASummary(BaseModel):
    """Aggregate summary of QA checks."""
    passed: int = 0
    failed: int = 0
    critical_failed: List[str] = Field(default_factory=list)


class GameStatusResponse(BaseModel):
    """Detailed status and metadata for a generation job."""
    game_id: str
    prompt: str
    status: str
    stage: str
    attempt: int = 1
    max_attempts: int = 3
    created_at: str
    updated_at: str
    game_url: Optional[str] = None
    qa_summary: Optional[QASummary] = None
    error_code: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)


class GameEvent(BaseModel):
    """Discrete lifecycle event emitted during job execution."""
    id: Optional[int] = None
    game_id: str
    ts: str
    stage: str
    result: str
    detail: str
    attempt: int = 1
    rationale: Optional[str] = None
    diff: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """System health and active model provider status."""
    model_config = ConfigDict(protected_namespaces=())

    status: str
    provider: str
    model: str
    has_api_key: bool
    model_requests: Optional[int] = None
    model_used: Optional[str] = None
    fallback_events: Optional[List[str]] = None
    model_requests_by_model: Optional[Dict[str, int]] = None


class ErrorResponse(BaseModel):
    """Standard error response payload."""
    detail: str
    error_code: Optional[str] = None
