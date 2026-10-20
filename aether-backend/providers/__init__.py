"""
AETHER Model Providers Package.
"""

from providers.base import (
    CompletionResult,
    ModelHttpError,
    ModelOutputInvalidError,
    ModelProvider,
    ModelTimeoutError,
    ProviderError,
    get_model_request_count,
    increment_model_request_count,
    reset_model_request_count,
)

# Automatically wrap MockModelProvider.complete so mock runs increment the process counter
# without touching providers/mock.py
try:
    from providers.mock import MockModelProvider
    if not getattr(MockModelProvider, "_counting_wrapper_installed", False):
        _orig_mock_complete = MockModelProvider.complete

        def _counted_mock_complete(self, system: str, user: str) -> CompletionResult:
            increment_model_request_count()
            return _orig_mock_complete(self, system, user)

        MockModelProvider.complete = _counted_mock_complete
        MockModelProvider._counting_wrapper_installed = True
except ImportError:
    pass
