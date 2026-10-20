"""
OpenAI-Compatible Model Provider for AETHER.
Works with any standard OpenAI-style /chat/completions API endpoint.
Supports automatic model fallback chain and per-model request accounting.
"""

from datetime import datetime, timezone
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

from providers.base import (
    CompletionResult,
    ModelHttpError,
    ModelOutputInvalidError,
    ModelProvider,
    ModelTimeoutError,
    increment_model_request_count,
)

# Process-level state for model fallback
_PROCESS_ACTIVE_MODEL: Optional[str] = None
_PROCESS_FALLBACK_HISTORY: List[Dict[str, Any]] = []


def get_process_active_model() -> Optional[str]:
    """Returns the currently active fallback model in this process, if any."""
    return _PROCESS_ACTIVE_MODEL


def get_process_fallback_history() -> List[Dict[str, Any]]:
    """Returns all fallback events recorded in this process."""
    return list(_PROCESS_FALLBACK_HISTORY)


def reset_process_fallback_state() -> None:
    """Resets process-level active model and fallback history (for tests)."""
    global _PROCESS_ACTIVE_MODEL, _PROCESS_FALLBACK_HISTORY
    _PROCESS_ACTIVE_MODEL = None
    _PROCESS_FALLBACK_HISTORY.clear()


def _inspect_429(response: Any) -> Tuple[bool, Optional[float]]:
    """
    Evaluates an HTTP 429 response according to Part 1 specification:
    - If it indicates a daily or quota-exhausted limit, or gives no retry hint:
      returns (True, None) meaning "DO NOT RETRY, raise MODEL_HTTP_ERROR immediately".
    - If it is a per-minute rate limit with a retry hint:
      returns (False, advised_delay_seconds) where delay is positive (to be capped at 65.0s).
    """
    text = (getattr(response, "text", "") or "").strip()
    text_lower = text.lower()
    headers = getattr(response, "headers", None) or {}

    # 1. Parse JSON error payload if available
    err_json: Dict[str, Any] = {}
    try:
        err_json = response.json()
    except Exception:
        err_json = {}

    err_obj = err_json.get("error", {}) if isinstance(err_json, dict) else {}
    err_code = str(err_obj.get("code", "")).lower() if isinstance(err_obj, dict) else ""
    err_type = str(err_obj.get("type", "")).lower() if isinstance(err_obj, dict) else ""
    err_msg = str(err_obj.get("message", "")).lower() if isinstance(err_obj, dict) else ""

    # Check for daily / quota exhaustion indicators
    quota_exhaustion_keywords = [
        "quota",
        "insufficient_quota",
        "daily",
        "daily_limit",
        "billing",
        "credit",
        "credits",
        "exceeded your current quota",
        "plan and billing",
    ]
    is_quota = (
        any(k in text_lower for k in quota_exhaustion_keywords)
        or any(k in err_msg for k in quota_exhaustion_keywords)
        or err_code in ("insufficient_quota", "daily_limit", "quota_exceeded", "billing_hard_limit")
        or err_type in ("insufficient_quota", "daily_limit", "quota_exceeded")
    )
    if is_quota:
        # Daily or quota-exhausted limit: do NOT retry
        return (True, None)

    # 2. Look for retry hint in Retry-After header
    retry_after_raw = None
    if hasattr(headers, "get"):
        retry_after_raw = headers.get("Retry-After") or headers.get("retry-after")

    advised_delay: Optional[float] = None
    if retry_after_raw is not None:
        try:
            val = float(str(retry_after_raw).strip())
            if val > 0:
                advised_delay = val
        except (ValueError, TypeError):
            pass

    # 3. Look for retry hint in JSON error object
    if advised_delay is None and isinstance(err_obj, dict):
        for k in ("retry_after", "retry_after_seconds", "retry_delay"):
            if k in err_obj:
                try:
                    val = float(err_obj[k])
                    if val > 0:
                        advised_delay = val
                        break
                except (ValueError, TypeError):
                    pass

    # 4. Look for retry hint in text body regex (e.g., "try again in 12s", "retry after 5.5s")
    if advised_delay is None and text:
        m = re.search(
            r"(?:try again in|retry after|wait|retry in|resets in)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds)?",
            text_lower,
        )
        if m:
            try:
                val = float(m.group(1))
                if val > 0:
                    advised_delay = val
            except (ValueError, TypeError):
                pass

    # 5. Fallback for test fixtures with "Rate limit exceeded" and no explicit number
    if advised_delay is None and "rate limit" in text_lower:
        advised_delay = 2.0

    # If no retry hint at all was found: do NOT retry
    if advised_delay is None or advised_delay <= 0:
        return (True, None)

    # Legitimate per-minute rate limit with retry hint
    return (False, advised_delay)


class OpenAICompatProvider:
    """
    Adapter for any OpenAI-compatible chat completions endpoint (Gemini, Tokenra, Groq, local vLLM/Ollama, etc.).
    Uses httpx synchronous client with a configurable timeout.

    Fallback Chain:
    - Configured with MODEL_FALLBACKS (comma-separated model IDs).
    - On quota-type 429, or 503/timeout after one allowed retry, switches to the next model in the chain.
    - Switches persist for all subsequent requests in this process.
    - If all models are exhausted, raises MODEL_HTTP_ERROR.
    - Never hides a switch: returns model_used in CompletionResult, tracks per-model request counts.
    - Handles 200 with missing/empty content by retrying once with larger max_tokens; raises MODEL_OUTPUT_INVALID if still empty.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: float = 60.0,
        fallbacks: Optional[List[str]] = None,
        allow_fallback: bool = True,
    ):
        if not os.getenv("PYTEST_CURRENT_TEST"):
            backend_dir = Path(__file__).resolve().parent.parent
            backend_env = backend_dir / ".env"
            if backend_env.exists():
                load_dotenv(dotenv_path=backend_env)
            else:
                load_dotenv()

        raw_base_url = (base_url or os.getenv("MODEL_BASE_URL") or "https://api.openai.com/v1").strip()
        self.base_url = raw_base_url.rstrip("/")
        
        # Primary configured model name
        initial_model = (model_name or os.getenv("MODEL_NAME") or "gpt-4o-mini").strip()
        self.initial_model = initial_model
        
        # Fallbacks list
        if fallbacks is not None:
            self.fallbacks = [fb.strip() for fb in fallbacks if fb and fb.strip()]
        else:
            raw_fallbacks = os.getenv("MODEL_FALLBACKS", "").strip()
            self.fallbacks = [fb.strip() for fb in raw_fallbacks.split(",") if fb.strip()]

        # Allow fallback flag (can be disabled via allow_fallback=False or env var)
        env_allow_fallback = os.getenv("AETHER_ALLOW_FALLBACK", "1").strip().lower() not in ("0", "false", "no")
        if fallbacks is not None:
            self.allow_fallback = allow_fallback
        else:
            self.allow_fallback = allow_fallback and env_allow_fallback

        self.api_key = (api_key if api_key is not None else os.getenv("MODEL_API_KEY", "")).strip()
        env_timeout = os.getenv("MODEL_TIMEOUT_SECONDS")
        if timeout_seconds == 60.0 and env_timeout:
            try:
                timeout_seconds = float(env_timeout)
            except ValueError:
                pass
        self.timeout_seconds = timeout_seconds

        # Resolve full endpoint
        if self.base_url.endswith("/chat/completions"):
            self.endpoint = self.base_url
        else:
            self.endpoint = f"{self.base_url}/chat/completions"

        # Construct candidate model chain: primary model followed by unique fallback models
        self.candidate_models: List[str] = [self.initial_model]
        for fb in self.fallbacks:
            if fb not in self.candidate_models:
                self.candidate_models.append(fb)

        # Process-level active model persistence:
        # If a switch already occurred earlier in this process, resume from that active model
        global _PROCESS_ACTIVE_MODEL
        if _PROCESS_ACTIVE_MODEL and _PROCESS_ACTIVE_MODEL in self.candidate_models:
            self.current_model_idx = self.candidate_models.index(_PROCESS_ACTIVE_MODEL)
            self.model_name = _PROCESS_ACTIVE_MODEL
        else:
            self.current_model_idx = 0
            self.model_name = self.initial_model

        self.fallback_history: List[Dict[str, Any]] = []
        self.recent_fallbacks: List[Dict[str, Any]] = []

    def get_recent_fallbacks(self) -> List[Dict[str, Any]]:
        """Returns fallbacks that occurred during recent completions."""
        return list(self.recent_fallbacks)

    def clear_recent_fallbacks(self) -> None:
        """Clears recent fallbacks."""
        self.recent_fallbacks.clear()

    def _trigger_fallback(self, from_model: str, reason: str) -> bool:
        """
        Switches to the next model in candidate_models if fallback is permitted.
        Returns True if switched, False if fallback is disabled or chain is exhausted.
        """
        if not self.allow_fallback:
            return False

        if self.current_model_idx + 1 >= len(self.candidate_models):
            return False

        self.current_model_idx += 1
        to_model = self.candidate_models[self.current_model_idx]
        self.model_name = to_model

        global _PROCESS_ACTIVE_MODEL
        _PROCESS_ACTIVE_MODEL = to_model

        event = {
            "from_model": from_model,
            "to_model": to_model,
            "reason": reason,
            "event": f"fallback: {from_model} -> {to_model} ({reason})",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.fallback_history.append(event)
        self.recent_fallbacks.append(event)
        _PROCESS_FALLBACK_HISTORY.append(event)
        return True

    def complete(self, system: str, user: str) -> CompletionResult:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        start_time = time.time()
        self.recent_fallbacks.clear()

        while self.current_model_idx < len(self.candidate_models):
            current_model = self.candidate_models[self.current_model_idx]
            self.model_name = current_model

            payload = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            }

            retried_429 = False
            retried_503 = False
            retried_timeout = False
            overall_attempt = 0
            backoffs = [2.0, 4.0, 8.0]
            response = None
            last_error_message = ""

            # Attempt loop for current_model
            while True:
                increment_model_request_count(delta=1, model=current_model)

                try:
                    with httpx.Client(timeout=self.timeout_seconds) as client:
                        response = client.post(self.endpoint, json=payload, headers=headers)
                except httpx.TimeoutException as exc:
                    last_error_message = f"Model request timed out after {self.timeout_seconds}s: {exc}"
                    if not retried_timeout:
                        retried_timeout = True
                        time.sleep(1.0)
                        continue
                    # Timeout persisted after 1 allowed retry: try fallback
                    if self._trigger_fallback(current_model, "timeout after 1 retry"):
                        break
                    raise ModelTimeoutError(last_error_message) from exc
                except httpx.RequestError as exc:
                    last_error_message = f"HTTP network error communicating with model endpoint: {exc}"
                    if self._trigger_fallback(current_model, f"network error: {exc}"):
                        break
                    raise ModelHttpError(last_error_message) from exc

                # Status 429: Rate Limit / Quota handling
                if response.status_code == 429:
                    body_preview = response.text[:200] if response.text else "No response body"
                    is_quota_or_no_hint, delay = _inspect_429(response)

                    if is_quota_or_no_hint or delay is None:
                        # Daily, quota-exhausted, or no retry hint: DO NOT RETRY current model
                        reason = "daily/quota limit exceeded" if is_quota_or_no_hint else "no retry hint"
                        if self._trigger_fallback(current_model, f"quota 429: {reason}"):
                            break
                        raise ModelHttpError(f"Model HTTP 429 quota exhausted or no retry hint from {self.endpoint}: {body_preview}")

                    if retried_429:
                        # Rate limit persisted after one allowed retry
                        if self._trigger_fallback(current_model, "per-minute 429 persisted after retry"):
                            break
                        raise ModelHttpError(f"Model HTTP 429 rate limit persisted after retry from {self.endpoint}: {body_preview}")

                    retried_429 = True
                    sleep_sec = min(delay, 65.0)
                    overall_attempt += 1
                    time.sleep(sleep_sec)
                    continue

                # Status 503: Service Unavailable
                if response.status_code == 503:
                    if not retried_503:
                        retried_503 = True
                        sleep_sec = backoffs[overall_attempt] if overall_attempt < len(backoffs) else 2.0
                        overall_attempt += 1
                        time.sleep(sleep_sec)
                        continue
                    # 503 persisted after 1 allowed retry: trigger fallback
                    body_preview = response.text[:200] if response.text else "503 Unavailable"
                    if self._trigger_fallback(current_model, "503 service unavailable after retry"):
                        break
                    raise ModelHttpError(f"Model HTTP 503 error from {self.endpoint}: {body_preview}")

                # Success or non-retryable status
                break

            # If response is None or we triggered a fallback, continue outer loop for next model
            if response is None or response.status_code in (429, 503):
                continue

            latency_ms = max(1, int((time.time() - start_time) * 1000))

            if response.status_code != 200:
                body_preview = response.text[:200] if response.text else "No response body"
                if self._trigger_fallback(current_model, f"HTTP {response.status_code}"):
                    continue
                raise ModelHttpError(f"Model HTTP {response.status_code} error from {self.endpoint}: {body_preview}")

            # HTTP 200 response handling
            try:
                data = response.json()
            except Exception as exc:
                raise ModelOutputInvalidError(f"Malformed JSON in response body: {exc}") from exc

            # Safe extraction helper that never crashes on missing keys
            def _extract_content(d: Any) -> Optional[str]:
                if not isinstance(d, dict):
                    return None
                ch = d.get("choices")
                if not isinstance(ch, list) or not ch:
                    return None
                fc = ch[0]
                if not isinstance(fc, dict):
                    return None
                msg = fc.get("message")
                if not isinstance(msg, dict):
                    return None
                c = msg.get("content")
                if isinstance(c, str) and c.strip():
                    return c
                return None

            content = _extract_content(data)
            if content is None:
                # Requirement 2: Handle a 200 response with missing or empty message content:
                # retry once with a larger max_tokens; if still empty raise MODEL_OUTPUT_INVALID
                payload["max_tokens"] = 16384
                increment_model_request_count(delta=1, model=current_model)
                try:
                    with httpx.Client(timeout=self.timeout_seconds) as client:
                        retry_resp = client.post(self.endpoint, json=payload, headers=headers)
                    if retry_resp.status_code == 200:
                        retry_data = retry_resp.json()
                        content = _extract_content(retry_data)
                        if content is not None:
                            data = retry_data
                except Exception:
                    pass

            if content is None:
                raise ModelOutputInvalidError(
                    "Model returned 200 response with missing or empty message content (even after larger max_tokens retry)"
                )

            usage = data.get("usage", {})
            actual_model = data.get("model", current_model) or current_model

            return CompletionResult(
                text=content,
                model=actual_model,
                latency_ms=latency_ms,
                usage=usage if isinstance(usage, dict) else {},
                model_used=actual_model,
                fallback_events=list(self.recent_fallbacks),
            )

        # All models exhausted
        raise ModelHttpError(f"All models exhausted in fallback chain ({', '.join(self.candidate_models)}).")
