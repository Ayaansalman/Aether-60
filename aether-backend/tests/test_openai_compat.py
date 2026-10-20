"""
Unit and integration tests for OpenAICompatProvider quota handling and model request counting.
Conforms to PART 1 requirements:
- HTTP 429 quota-exhausted or daily limits: zero retries, immediate MODEL_HTTP_ERROR.
- HTTP 429 with no retry hint: zero retries, immediate MODEL_HTTP_ERROR.
- HTTP 429 per-minute rate limit: retried at most once after advised delay (capped at 65s).
- Per-process model request counter tracks all model requests and retries accurately.
"""

import json
from typing import Any, Dict, List, Optional
import httpx
import pytest

from providers.base import (
    ModelHttpError,
    get_model_request_count,
    increment_model_request_count,
    reset_model_request_count,
)
from providers.openai_compat import OpenAICompatProvider


def _make_valid_response_json() -> Dict[str, Any]:
    spec = {
        "schema_version": "1.0",
        "title": "Quota Test Arena",
        "genre": "arena_survival",
        "premise": "Test premise for quota verification.",
        "theme": "sci_fi",
        "player": {"move_speed": 200.0, "max_health": 3, "attack_mode": "projectile"},
        "enemies": [{"type": "chaser", "count": 4, "speed": 70.0}],
        "collectibles": [{"type": "battery", "count": 8}],
        "objective": {"type": "survive_seconds", "target": 30},
        "difficulty": 2,
        "controls": {"movement": "WASD or arrow keys", "attack": "Space"},
        "seed": 123,
    }
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"spec": spec, "limitations": []})
                }
            }
        ],
        "model": "gpt-4o-mini",
        "usage": {"total_tokens": 100},
    }


class FakeResponse:
    def __init__(self, status_code: int, json_data: Optional[Dict[str, Any]] = None, text: str = "", headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text or (json.dumps(self._json_data) if self._json_data else "")
        self.headers = headers or {}

    def json(self):
        return self._json_data


def test_429_quota_exhausted_raises_immediately_without_retry(monkeypatch):
    """HTTP 429 with quota exhausted indicators must NOT retry and raise MODEL_HTTP_ERROR immediately."""
    reset_model_request_count()
    post_calls = 0
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(*args, **kwargs):
        nonlocal post_calls
        post_calls += 1
        return FakeResponse(
            429,
            json_data={"error": {"message": "You exceeded your current quota, please check your plan and billing details.", "type": "insufficient_quota", "code": "insufficient_quota"}},
            headers={"Retry-After": "10"},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="sk-test-fake")
    with pytest.raises(ModelHttpError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_HTTP_ERROR"
    assert "quota" in str(exc_info.value).lower()
    assert post_calls == 1  # exactly 1 call: zero retries
    assert sleep_calls == []  # did not sleep
    assert get_model_request_count() == 1


def test_429_daily_limit_raises_immediately_without_retry(monkeypatch):
    """HTTP 429 indicating a daily limit must NOT retry and raise MODEL_HTTP_ERROR immediately."""
    reset_model_request_count()
    post_calls = 0
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(*args, **kwargs):
        nonlocal post_calls
        post_calls += 1
        return FakeResponse(
            429,
            text="Daily request limit reached for free tier model. Please wait until tomorrow.",
            headers={"Retry-After": "86400"},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="sk-test-fake")
    with pytest.raises(ModelHttpError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_HTTP_ERROR"
    assert post_calls == 1
    assert sleep_calls == []
    assert get_model_request_count() == 1


def test_429_no_retry_hint_raises_immediately_without_retry(monkeypatch):
    """HTTP 429 with no retry hint header or text must NOT retry and raise MODEL_HTTP_ERROR immediately."""
    reset_model_request_count()
    post_calls = 0
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(*args, **kwargs):
        nonlocal post_calls
        post_calls += 1
        return FakeResponse(
            429,
            text="Too Many Requests. Request blocked.",
            headers={},  # No Retry-After header
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="sk-test-fake")
    with pytest.raises(ModelHttpError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_HTTP_ERROR"
    assert post_calls == 1
    assert sleep_calls == []
    assert get_model_request_count() == 1


def test_429_per_minute_retries_once_with_advised_delay(monkeypatch):
    """HTTP 429 for per-minute rate limit with Retry-After header retries once after advised delay."""
    reset_model_request_count()
    post_calls = 0
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(*args, **kwargs):
        nonlocal post_calls
        post_calls += 1
        if post_calls == 1:
            return FakeResponse(
                429,
                text="Rate limit exceeded. Please retry after 12 seconds.",
                headers={"Retry-After": "12"},
            )
        return FakeResponse(200, json_data=_make_valid_response_json())

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="sk-test-fake")
    res = provider.complete("system", "user")

    assert res is not None
    assert post_calls == 2  # initial + 1 retry
    assert sleep_calls == [12.0]  # slept advised delay
    assert get_model_request_count() == 2


def test_429_per_minute_caps_delay_at_65s(monkeypatch):
    """HTTP 429 advising a delay >65s (e.g. 120s) caps the retry sleep to 65.0s."""
    reset_model_request_count()
    post_calls = 0
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(*args, **kwargs):
        nonlocal post_calls
        post_calls += 1
        if post_calls == 1:
            return FakeResponse(
                429,
                text="Rate limit per minute exceeded.",
                headers={"Retry-After": "120"},
            )
        return FakeResponse(200, json_data=_make_valid_response_json())

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="sk-test-fake")
    res = provider.complete("system", "user")

    assert res is not None
    assert post_calls == 2
    assert sleep_calls == [65.0]  # capped at 65.0s
    assert get_model_request_count() == 2


def test_429_per_minute_persisting_raises_after_single_retry(monkeypatch):
    """If per-minute 429 persists on retry, provider halts immediately without retrying again."""
    reset_model_request_count()
    post_calls = 0
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(*args, **kwargs):
        nonlocal post_calls
        post_calls += 1
        return FakeResponse(
            429,
            text="Requests per minute rate limit exceeded.",
            headers={"Retry-After": "5"},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="sk-test-fake")
    with pytest.raises(ModelHttpError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_HTTP_ERROR"
    assert post_calls == 2  # exactly 2 calls: initial + 1 retry only
    assert sleep_calls == [5.0]
    assert get_model_request_count() == 2


def test_process_model_request_counter():
    """Verify reset_model_request_count and increment_model_request_count."""
    reset_model_request_count()
    assert get_model_request_count() == 0
    increment_model_request_count(1)
    assert get_model_request_count() == 1
    increment_model_request_count(3)
    assert get_model_request_count() == 4
    reset_model_request_count()
    assert get_model_request_count() == 0


# =========================================================================
# Fallback Chain & Empty Content Tests (Requirement 5)
# =========================================================================

def test_fallback_daily_429_on_model_a_then_success_on_b(monkeypatch):
    """Daily 429 on model A immediately triggers fallback to model B and succeeds."""
    from providers.base import get_model_requests_by_model
    from providers.openai_compat import reset_process_fallback_state

    reset_model_request_count()
    reset_process_fallback_state()
    called_models = []

    def mock_post(client, url, json=None, headers=None):
        requested_model = json.get("model") if json else "unknown"
        called_models.append(requested_model)
        if requested_model == "model-a":
            return FakeResponse(
                429,
                json_data={"error": {"message": "You exceeded your current quota.", "code": "insufficient_quota"}},
            )
        # model-b succeeds
        resp_json = _make_valid_response_json()
        resp_json["model"] = "model-b"
        return FakeResponse(200, json_data=resp_json)

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(
        model_name="model-a",
        fallbacks=["model-b"],
        api_key="sk-test-fake",
    )
    res = provider.complete("system", "user")

    assert res is not None
    assert res.model == "model-b"
    assert res.model_used == "model-b"
    assert called_models == ["model-a", "model-b"]
    assert len(res.fallback_events) == 1
    assert "model-a -> model-b" in res.fallback_events[0]["event"]
    assert get_model_request_count("model-a") == 1
    assert get_model_request_count("model-b") == 1
    assert get_model_request_count() == 2
    assert get_model_requests_by_model() == {"model-a": 1, "model-b": 1}


def test_fallback_503_retried_once_then_fallback(monkeypatch):
    """HTTP 503 is retried once on model A, then triggers fallback to model B and succeeds."""
    from providers.openai_compat import reset_process_fallback_state

    reset_model_request_count()
    reset_process_fallback_state()
    called_models = []
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    def mock_post(client, url, json=None, headers=None):
        requested_model = json.get("model") if json else "unknown"
        called_models.append(requested_model)
        if requested_model == "model-a":
            return FakeResponse(503, text="Service Unavailable")
        resp_json = _make_valid_response_json()
        resp_json["model"] = "model-b"
        return FakeResponse(200, json_data=resp_json)

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(
        model_name="model-a",
        fallbacks=["model-b"],
        api_key="sk-test-fake",
    )
    res = provider.complete("system", "user")

    assert res is not None
    assert res.model == "model-b"
    assert res.model_used == "model-b"
    # model-a was tried twice (initial + 1 allowed retry), model-b was tried once
    assert called_models == ["model-a", "model-a", "model-b"]
    assert get_model_request_count("model-a") == 2
    assert get_model_request_count("model-b") == 1
    assert get_model_request_count() == 3
    assert len(sleep_calls) >= 1


def test_empty_content_retried_with_larger_max_tokens_success(monkeypatch):
    """Missing or empty content on 200 is retried once with larger max_tokens; succeeds if content returned."""
    from providers.openai_compat import reset_process_fallback_state

    reset_model_request_count()
    reset_process_fallback_state()
    call_payloads = []

    def mock_post(client, url, json=None, headers=None):
        call_payloads.append(dict(json) if json else {})
        if len(call_payloads) == 1:
            # First attempt: 200 with empty string content (e.g. Gemini 3.7 reasoning consumed budget)
            return FakeResponse(200, json_data={"choices": [{"message": {"content": ""}}]})
        # Second attempt: retried with larger max_tokens, returns valid content
        return FakeResponse(200, json_data=_make_valid_response_json())

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(model_name="model-a", api_key="sk-test-fake")
    res = provider.complete("system", "user")

    assert res is not None
    assert len(call_payloads) == 2
    assert call_payloads[1].get("max_tokens") == 16384
    assert get_model_request_count("model-a") == 2


def test_empty_content_persisting_raises_model_output_invalid(monkeypatch):
    """If empty content persists after retry with larger max_tokens, raise MODEL_OUTPUT_INVALID (never crash)."""
    from providers.base import ModelOutputInvalidError
    from providers.openai_compat import reset_process_fallback_state

    reset_model_request_count()
    reset_process_fallback_state()

    def mock_post(client, url, json=None, headers=None):
        # 200 with missing message key or empty content
        return FakeResponse(200, json_data={"choices": [{"message": {}}]})

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(model_name="model-a", api_key="sk-test-fake")
    with pytest.raises(ModelOutputInvalidError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_OUTPUT_INVALID"
    assert "empty" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()


def test_fallback_all_models_exhausted_raises_model_http_error(monkeypatch):
    """When all models in the fallback chain fail, raise MODEL_HTTP_ERROR."""
    from providers.openai_compat import reset_process_fallback_state

    reset_model_request_count()
    reset_process_fallback_state()
    called_models = []

    def mock_post(client, url, json=None, headers=None):
        requested_model = json.get("model") if json else "unknown"
        called_models.append(requested_model)
        return FakeResponse(
            429,
            json_data={"error": {"message": "Quota limit reached", "code": "quota_exceeded"}},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(
        model_name="model-a",
        fallbacks=["model-b", "model-c"],
        api_key="sk-test-fake",
    )
    with pytest.raises(ModelHttpError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_HTTP_ERROR"
    assert called_models == ["model-a", "model-b", "model-c"]
    assert get_model_request_count("model-a") == 1
    assert get_model_request_count("model-b") == 1
    assert get_model_request_count("model-c") == 1
    assert get_model_request_count() == 3


def test_fallback_disabled_raises_immediately_without_fallback(monkeypatch):
    """When fallback is disabled, provider raises immediately on quota 429 without switching."""
    from providers.openai_compat import reset_process_fallback_state

    reset_model_request_count()
    reset_process_fallback_state()
    called_models = []

    def mock_post(client, url, json=None, headers=None):
        requested_model = json.get("model") if json else "unknown"
        called_models.append(requested_model)
        return FakeResponse(
            429,
            json_data={"error": {"message": "Daily limit reached", "code": "daily_limit"}},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(
        model_name="model-a",
        fallbacks=["model-b"],
        allow_fallback=False,
        api_key="sk-test-fake",
    )
    with pytest.raises(ModelHttpError) as exc_info:
        provider.complete("system", "user")

    assert exc_info.value.code == "MODEL_HTTP_ERROR"
    assert called_models == ["model-a"]  # model-b never called
    assert get_model_request_count("model-a") == 1
    assert get_model_request_count("model-b") == 0

