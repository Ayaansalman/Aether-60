"""
Base Protocol and Result types for AETHER LLM Model Providers.
"""

from dataclasses import dataclass, field
from contextvars import ContextVar
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# Present in the repair agent's system prompt; lets the labeled mock provider detect repair requests.
REPAIR_AGENT_MARKER = "AETHER_REPAIR_AGENT_V1"

# The v2 job installs a listener in its async context; asyncio.to_thread copies
# that context into each interpretation/design call. Other jobs stay isolated.
fallback_listener: ContextVar = ContextVar('aether_model_fallback_listener',default=None)

# Process-level counter of model requests
_MODEL_REQUEST_COUNT: int = 0
_MODEL_REQUESTS_BY_MODEL: Dict[str, int] = {}


def get_model_request_count(model: Optional[str] = None) -> int:
    """Returns the total number of model requests executed, or count for a specific model."""
    if model is not None:
        return _MODEL_REQUESTS_BY_MODEL.get(model, 0)
    return _MODEL_REQUEST_COUNT


def get_model_requests_by_model() -> Dict[str, int]:
    """Returns a copy of request counts per model."""
    return dict(_MODEL_REQUESTS_BY_MODEL)


def increment_model_request_count(delta: int = 1, model: Optional[str] = None) -> int:
    """Increments and returns the process model request count (overall and per-model)."""
    global _MODEL_REQUEST_COUNT
    _MODEL_REQUEST_COUNT += delta
    if model:
        _MODEL_REQUESTS_BY_MODEL[model] = _MODEL_REQUESTS_BY_MODEL.get(model, 0) + delta
    return _MODEL_REQUEST_COUNT


def reset_model_request_count() -> None:
    """Resets the process model request count to zero (useful for tests)."""
    global _MODEL_REQUEST_COUNT
    _MODEL_REQUEST_COUNT = 0
    _MODEL_REQUESTS_BY_MODEL.clear()


@dataclass
class CompletionResult:
    text: str
    model: str
    latency_ms: int
    usage: Dict[str, Any] = field(default_factory=dict)
    model_used: Optional[str] = None
    fallback_events: list = field(default_factory=list)

    def __post_init__(self):
        if not self.model_used:
            self.model_used = self.model


class ProviderError(Exception):
    """Base exception for model provider errors."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ModelTimeoutError(ProviderError):
    """Raised when a model completion request times out (MODEL_TIMEOUT)."""
    def __init__(self, message: str = "Model request timed out"):
        super().__init__("MODEL_TIMEOUT", message)


class ModelHttpError(ProviderError):
    """Raised when an HTTP error or communication failure occurs (MODEL_HTTP_ERROR)."""
    def __init__(self, message: str = "Model HTTP error"):
        super().__init__("MODEL_HTTP_ERROR", message)


class ModelOutputInvalidError(ProviderError):
    """Raised when model output is structurally corrupted or missing (MODEL_OUTPUT_INVALID)."""
    def __init__(self, message: str = "Model output was invalid"):
        super().__init__("MODEL_OUTPUT_INVALID", message)


@runtime_checkable
class ModelProvider(Protocol):
    """Protocol interface defining the contract for all AETHER Model Providers."""
    def complete(self, system: str, user: str) -> CompletionResult:
        """
        Executes a synchronous completion call against the underlying model backend.
        """
        ...
