"""
Provider Factory for AETHER LLM integration.
Conforms to Section 7.2 of the AETHER specification.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

from providers.base import ModelProvider
from providers.mock import MockModelProvider
from providers.openai_compat import OpenAICompatProvider

_custom_provider: Optional[ModelProvider] = None


def set_custom_provider(provider: Optional[ModelProvider]) -> None:
    """Sets a global custom provider override (used for testing and evaluation)."""
    global _custom_provider
    _custom_provider = provider


def get_provider(provider_type: Optional[str] = None) -> ModelProvider:
    """
    Factory function returning the configured ModelProvider.
    Reads MODEL_PROVIDER environment variable: 'mock' | 'openai_compat'.
    Defaults to 'mock' if unspecified.
    """
    if _custom_provider is not None:
        return _custom_provider

    backend_dir = Path(__file__).resolve().parent.parent
    backend_env = backend_dir / ".env"
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)
    else:
        load_dotenv()

    name = (provider_type or os.getenv("MODEL_PROVIDER") or "mock").strip().lower()

    if name == "openai_compat":
        return OpenAICompatProvider()
    elif name == "mock":
        return MockModelProvider()
    else:
        # Graceful fallback to mock provider for unknown values
        return MockModelProvider()

