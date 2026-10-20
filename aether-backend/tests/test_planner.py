"""
Tests for the AETHER Game Planning Service and Model Providers.
Conforms to Sections 5.1, 5.2, and 7.2 of the AETHER Specification.
"""

import json
from typing import List, Optional

import pytest

from providers.base import (
    CompletionResult,
    ModelHttpError,
    ModelOutputInvalidError,
    ModelProvider,
    ModelTimeoutError,
)
from providers.mock import MockModelProvider
from schemas.game_ir import GameIR
from services.planner import plan_game


class FakeSequenceProvider:
    """Helper fake provider returning a sequence of preset response strings."""

    def __init__(self, responses: List[str], model: str = "fake-model"):
        self.responses = list(responses)
        self.call_count = 0
        self.model = model

    def complete(self, system: str, user: str) -> CompletionResult:
        if not self.responses:
            raise RuntimeError("No more fake responses configured.")
        resp = self.responses.pop(0)
        self.call_count += 1
        return CompletionResult(
            text=resp,
            model=self.model,
            latency_ms=10,
            usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        )


def _make_valid_spec_json(theme: str = "fantasy", title: str = "Valid Game") -> str:
    """Generates a valid JSON string wrapped in {"spec": ..., "limitations": []}."""
    data = {
        "spec": {
            "schema_version": "1.0",
            "title": title,
            "genre": "arena_survival",
            "premise": "A valid game premise for testing purposes.",
            "theme": theme,
            "player": {
                "move_speed": 200.0,
                "max_health": 3,
                "attack_mode": "projectile",
            },
            "enemies": [
                {
                    "type": "chaser",
                    "count": 5,
                    "speed": 75.0,
                }
            ],
            "collectibles": [
                {
                    "type": "crystal",
                    "count": 10,
                }
            ],
            "objective": {
                "type": "collect_count",
                "target": 5,
            },
            "difficulty": 2,
            "controls": {
                "movement": "WASD or arrow keys",
                "attack": "Space",
            },
            "seed": 123,
        },
        "limitations": [],
    }
    return json.dumps(data)


def test_valid_first_try():
    """Planner succeeds on first attempt with valid model output."""
    valid_json = _make_valid_spec_json("fantasy", "First Try Arena")
    fake = FakeSequenceProvider([valid_json])

    result = plan_game("create a magical fantasy game", provider=fake)

    assert result.ok is True
    assert result.attempts == 1
    assert result.error_code is None
    assert result.spec is not None
    assert result.spec.title == "First Try Arena"
    assert result.spec.theme == "fantasy"
    assert fake.call_count == 1


def test_invalid_first_then_valid_retry():
    """Planner catches invalid output on attempt 1, retries once, and succeeds on attempt 2."""
    invalid_json = json.dumps({"spec": {"title": "Bad", "theme": "unsupported_theme"}})
    valid_json = _make_valid_spec_json("pirate", "Pirate Recovery Arena")
    fake = FakeSequenceProvider([invalid_json, valid_json])

    result = plan_game("a pirate game", provider=fake)

    assert result.ok is True
    assert result.attempts == 2
    assert result.error_code is None
    assert result.spec is not None
    assert result.spec.theme == "pirate"
    assert fake.call_count == 2


def test_two_invalid_tries_fail():
    """Planner returns ok=False and MODEL_OUTPUT_INVALID after two consecutive invalid attempts."""
    invalid_1 = json.dumps({"corrupted": True})
    invalid_2 = json.dumps({"spec": {"invalid": "still invalid"}})
    fake = FakeSequenceProvider([invalid_1, invalid_2])

    result = plan_game("sci-fi survival", provider=fake)

    assert result.ok is False
    assert result.attempts == 2
    assert result.error_code == "MODEL_OUTPUT_INVALID"
    assert result.spec is None
    assert len(result.errors) > 0
    assert fake.call_count == 2


def test_fenced_json_handled():
    """Planner correctly strips markdown code fences (```json ... ```)."""
    inner_json = _make_valid_spec_json("cozy", "Cozy Fenced Game")
    fenced_text = f"```json\n{inner_json}\n```"
    fake = FakeSequenceProvider([fenced_text])

    result = plan_game("a cozy game with tea and gardens", provider=fake)

    assert result.ok is True
    assert result.attempts == 1
    assert result.spec is not None
    assert result.spec.title == "Cozy Fenced Game"
    assert result.spec.theme == "cozy"


def test_prompt_validation():
    """Empty prompts and prompts exceeding 1200 characters are rejected with PROMPT_INVALID."""
    # Empty prompt
    res_empty = plan_game("")
    assert res_empty.ok is False
    assert res_empty.error_code == "PROMPT_INVALID"
    assert res_empty.attempts == 0

    # Whitespace prompt
    res_whitespace = plan_game("   \n\t  ")
    assert res_whitespace.ok is False
    assert res_whitespace.error_code == "PROMPT_INVALID"
    assert res_whitespace.attempts == 0

    # Too long prompt (> 1200 chars)
    too_long = "a" * 1201
    res_long = plan_game(too_long)
    assert res_long.ok is False
    assert res_long.error_code == "PROMPT_INVALID"
    assert res_long.attempts == 0


def test_provider_timeout_maps_to_model_timeout():
    """ModelTimeoutError raised by provider is mapped to error_code='MODEL_TIMEOUT' without raising."""
    class TimeoutProvider:
        def complete(self, system: str, user: str) -> CompletionResult:
            raise ModelTimeoutError("Upstream model connection timed out after 60s")

    result = plan_game("any valid prompt", provider=TimeoutProvider())

    assert result.ok is False
    assert result.error_code == "MODEL_TIMEOUT"
    assert result.spec is None
    assert "timed out" in result.errors[0].lower()


def test_mock_provider_theme_keywords():
    """MockModelProvider returns valid specs matching keywords: spooky, pirate, robot/sci-fi, cozy."""
    mock_provider = MockModelProvider()

    cases = [
        ("a spooky wizard gathering glowing crystals", "spooky"),
        ("a pirate captain survives enemy ships", "pirate"),
        ("a robot defending its futuristic cyber core", "sci_fi"),
        ("sci-fi space survival against void drones", "sci_fi"),
        ("a cozy harvest gathering in the autumn woods", "cozy"),
    ]

    for prompt, expected_theme in cases:
        result = plan_game(prompt, provider=mock_provider)
        assert result.ok is True, f"Failed for prompt '{prompt}': {result.errors}"
        assert result.spec is not None
        assert result.spec.theme == expected_theme, (
            f"Expected theme '{expected_theme}' for prompt '{prompt}', got '{result.spec.theme}'"
        )
        assert result.attempts == 1
        assert result.first_response_validated is True
        assert len(result.errors) == 0


def test_openai_compat_retry_on_429_and_503(monkeypatch):
    """OpenAICompatProvider retries up to 3 times on 429/503 with backoff intervals [2.0, 4.0, 8.0]."""
    from providers.openai_compat import OpenAICompatProvider
    import httpx

    sleep_calls = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))

    post_call_count = 0

    class MockResponse:
        def __init__(self, status_code, json_data=None, text=""):
            self.status_code = status_code
            self._json_data = json_data or {}
            self.text = text

        def json(self):
            return self._json_data

    def mock_post(*args, **kwargs):
        nonlocal post_call_count
        post_call_count += 1
        if post_call_count == 1:
            return MockResponse(429, text="Rate limit exceeded")
        elif post_call_count == 2:
            return MockResponse(503, text="Service Unavailable")
        else:
            return MockResponse(200, json_data={
                "choices": [{"message": {"content": _make_valid_spec_json()}}],
                "model": "gpt-4o-mini",
                "usage": {"total_tokens": 50}
            })

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    provider = OpenAICompatProvider(api_key="test-key")
    result = provider.complete("system", "user")

    assert post_call_count == 3
    assert sleep_calls == [2.0, 4.0]
    assert result.model == "gpt-4o-mini"
    assert "Wizard" in result.text or "Valid Game" in result.text


def test_fences_with_conversational_text():
    """Planner extracts JSON when surrounded by conversational text before and after markdown fences."""
    inner_json = _make_valid_spec_json("spooky", "Spooky Fenced Game")
    conversational_text = (
        f"Sure! Here is the GameIR specification you requested:\n\n"
        f"```json\n{inner_json}\n```\n\n"
        f"Let me know if you need any adjustments!"
    )
    fake = FakeSequenceProvider([conversational_text])

    result = plan_game("a spooky haunted castle game", provider=fake)

    assert result.ok is True
    assert result.attempts == 1
    assert result.first_response_validated is True
    assert result.spec is not None
    assert result.spec.title == "Spooky Fenced Game"
    assert result.spec.theme == "spooky"


def test_mock_provider_prompts_evaluation():
    """Verify mock provider behavior for all 4 benchmark prompts."""
    provider = MockModelProvider()

    # 1. Spooky wizard
    r1 = plan_game("a spooky wizard collecting glowing crystals while ghosts chase me", provider=provider)
    assert r1.ok is True
    assert r1.spec is not None
    assert r1.spec.theme == "spooky"
    assert r1.first_response_validated is True

    # 2. Robot surviving 60 seconds
    r2 = plan_game("a robot surviving drone waves for 60 seconds", provider=provider)
    assert r2.ok is True
    assert r2.spec is not None
    assert r2.spec.theme == "sci_fi"
    assert r2.spec.objective.type == "survive_seconds"
    assert r2.spec.objective.target == 60

    # 3. 3D multiplayer racing
    r3 = plan_game("a 3D open world racing game with multiplayer", provider=provider)
    assert r3.ok is True
    assert any("3d" in lim.lower() for lim in r3.limitations)
    assert any("multiplayer" in lim.lower() for lim in r3.limitations)

    # 4. Make it hard
    r4 = plan_game("make it hard", provider=provider)
    assert r4.ok is True
    assert r4.spec is not None
    assert r4.spec.difficulty == 5
    assert r4.spec.enemies[0].speed >= 100.0
