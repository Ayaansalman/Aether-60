"""
Tests for AETHER Benchmark Tooling and Runner.
Verifies metrics calculation, artifact generation, and banner behaviors with fake providers.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from providers.base import CompletionResult, ModelProvider
from providers.mock import MockModelProvider
from scripts.run_planner_bench import run_benchmark


class FakeBenchProvider:
    """Deterministic fake provider for fast offline unit testing of benchmark tooling."""

    def __init__(self, fail_first_for_id: Optional[str] = None, always_fail_id: Optional[str] = None):
        self.call_count = 0
        self.fail_first_for_id = fail_first_for_id
        self.always_fail_id = always_fail_id
        self.seen_attempts: Dict[str, int] = {}
        self.model = "fake-bench-model"

    def complete(self, system: str, user: str) -> CompletionResult:
        self.call_count += 1

        is_3d = "3d" in user.lower()
        limitations = ["3D graphics requested; adapted to 2D."] if is_3d else []

        # Theme detection
        theme = "fantasy"
        if "spooky" in user.lower():
            theme = "spooky"
        elif "sci_fi" in user.lower() or "cyberpunk" in user.lower() or "robot" in user.lower():
            theme = "sci_fi"
        elif "pirate" in user.lower():
            theme = "pirate"
        elif "cozy" in user.lower():
            theme = "cozy"

        is_survive = "45 seconds" in user.lower() or "surviving" in user.lower()
        obj = {"type": "survive_seconds", "target": 45} if is_survive else {"type": "collect_count", "target": 8}

        spec = {
            "schema_version": "1.0",
            "title": "Bench Test Game",
            "genre": "arena_survival",
            "premise": "Test premise for benchmark runner.",
            "theme": theme,
            "player": {
                "move_speed": 200.0,
                "max_health": 3,
                "attack_mode": "projectile" if not is_survive else "avoid_only",
            },
            "enemies": [{"type": "chaser", "count": 5, "speed": 75.0}],
            "collectibles": [{"type": "crystal", "count": 10}] if not is_survive else [],
            "objective": obj,
            "difficulty": 2,
            "controls": {"movement": "WASD or arrow keys", "attack": "Space" if not is_survive else None},
            "seed": 100,
        }

        # Simulate failure if configured
        if self.always_fail_id and self.always_fail_id in user:
            return CompletionResult(text="Invalid output", model=self.model, latency_ms=15, usage={})

        if self.fail_first_for_id and self.fail_first_for_id in user:
            count = self.seen_attempts.get(self.fail_first_for_id, 0) + 1
            self.seen_attempts[self.fail_first_for_id] = count
            if count == 1:
                return CompletionResult(text="Corrupted JSON", model=self.model, latency_ms=15, usage={})

        payload = {"spec": spec, "limitations": limitations}
        return CompletionResult(
            text=json.dumps(payload),
            model=self.model,
            latency_ms=25,
            usage={"total_tokens": 80},
        )


def test_bench_runner_with_fake_provider(tmp_path):
    """Benchmark runner processes all prompts, computes metrics, and outputs artifacts."""
    fake_provider = FakeBenchProvider()

    res = run_benchmark(
        provider=fake_provider,
        delay_seconds=0.0,
        artifacts_dir=tmp_path / "bench_out",
    )

    summary = res["summary"]
    records = res["records"]

    assert summary["total_prompts"] == 10
    assert summary["first_response_validation_rate"] == 100.0
    assert summary["final_success_rate"] == 100.0
    assert summary["limitation_honesty_rate"] == 100.0
    assert summary["median_latency_ms"] == 25.0
    assert summary["max_latency_ms"] == 25

    # Check files created
    json_path = Path(res["json_path"])
    md_path = Path(res["md_path"])

    assert json_path.exists()
    assert md_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert len(saved_data["records"]) == 10


def test_bench_runner_with_mock_provider(tmp_path):
    """When using MockModelProvider, output sets provider='mock' and generates valid report."""
    mock_provider = MockModelProvider()

    res = run_benchmark(
        provider=mock_provider,
        delay_seconds=0.0,
        artifacts_dir=tmp_path / "mock_out",
    )

    summary = res["summary"]
    assert summary["provider"] == "mock"
    assert summary["model_id"] == "mock"
    assert summary["final_success_rate"] == 100.0

    md_content = Path(res["md_path"]).read_text(encoding="utf-8")
    assert "MOCK PROVIDER: not a real model, results are not evidence" in md_content


def test_latency_stats_and_status_distinction(tmp_path):
    """
    Verifies that:
    1. Latency median and max are computed ONLY over calls that returned a model response.
    2. Failed calls before response (HTTP/timeout) are excluded from latency stats.
    3. 'not run' is reported distinctly from 'validation failed'.
    4. Denominators and skipped prompts are explicitly recorded.
    """
    from providers.base import ModelHttpError

    class FailureModesProvider:
        def __init__(self):
            self.model = "test-fail-modes"

        def complete(self, system: str, user: str) -> CompletionResult:
            if "spooky wizard" in user.lower():
                # Success: 40ms
                spec = {
                    "schema_version": "1.0",
                    "title": "Wizard Arena",
                    "genre": "arena_survival",
                    "premise": "A spooky wizard surviving.",
                    "theme": "spooky",
                    "player": {"move_speed": 200.0, "max_health": 3, "attack_mode": "projectile"},
                    "enemies": [{"type": "chaser", "count": 5, "speed": 80.0}],
                    "collectibles": [{"type": "crystal", "count": 10}],
                    "objective": {"type": "collect_count", "target": 8},
                    "difficulty": 2,
                    "controls": {"movement": "WASD", "attack": "Space"},
                    "seed": 1,
                }
                return CompletionResult(
                    text=json.dumps({"spec": spec, "limitations": []}),
                    model=self.model,
                    latency_ms=40,
                )
            elif "robot surviving" in user.lower():
                # Model responded with invalid output -> Validation Failed: 80ms
                return CompletionResult(
                    text="INVALID NOT JSON OUTPUT",
                    model=self.model,
                    latency_ms=80,
                )
            else:
                # Error before model response -> Not Run
                raise ModelHttpError("429 Quota Exceeded")

    test_prompts = [
        {
            "id": "t01",
            "prompt": "a spooky wizard collecting crystals",
            "expected_theme": "spooky",
            "expected_objective_type": "collect_count",
            "expect_limitation": False,
            "notes": "Test success prompt",
        },
        {
            "id": "t02",
            "prompt": "a robot surviving against waves",
            "expected_theme": "sci_fi",
            "expected_objective_type": "collect_count",
            "expect_limitation": False,
            "notes": "Test invalid model response prompt",
        },
        {
            "id": "t03",
            "prompt": "a pirate captain collecting gold",
            "expected_theme": None,
            "expected_objective_type": None,
            "expect_limitation": True,
            "notes": "Test error before response prompt",
        },
    ]

    custom_prompts_file = tmp_path / "custom_prompts.json"
    custom_prompts_file.write_text(json.dumps(test_prompts), encoding="utf-8")

    res = run_benchmark(
        provider=FailureModesProvider(),
        delay_seconds=0.0,
        prompts_path=custom_prompts_file,
        artifacts_dir=tmp_path / "failure_out",
    )

    summary = res["summary"]
    records = res["records"]

    # 1. Check prompt statuses
    r1 = next(r for r in records if r["id"] == "t01")
    r2 = next(r for r in records if r["id"] == "t02")
    r3 = next(r for r in records if r["id"] == "t03")

    assert r1["status"] == "PASS"
    assert r1["ok"] is True
    assert r1["model_responded"] is True
    assert r1["latency_ms"] == 40

    assert r2["status"] == "VALIDATION_FAILED"
    assert r2["ok"] is False
    assert r2["model_responded"] is True
    assert r2["latency_ms"] > 0

    assert r3["status"] == "NOT_RUN"
    assert r3["ok"] is False
    assert r3["model_responded"] is False
    assert r3["error_code"] == "MODEL_HTTP_ERROR"

    # 2. Check counts
    assert summary["total_prompts"] == 3
    assert summary["responded_prompts"] == 2
    assert summary["not_run_prompts"] == 1
    assert summary["validation_failed_prompts"] == 1
    assert summary["passed_prompts"] == 1

    # 3. Check latency stats: only over calls that returned model response (t01 and t02)
    assert summary["latency_evaluated_count"] == 2
    assert summary["latency_excluded_count"] == 1
    # Latencies are [40, 160] (80 on attempt 1 + 80 on retry 2) -> median = 100.0, max = 160
    assert summary["median_latency_ms"] == (40 + r2["latency_ms"]) / 2
    assert summary["max_latency_ms"] == r2["latency_ms"]

    # 4. Check denominators
    assert summary["first_response_validation_denominator"] == "1/2"
    assert summary["final_success_denominator"] == "1/2"
    assert summary["theme_match_denominator"] == "1/2"
    assert summary["theme_skipped_prompts"] == ["t03"]

    # 5. Check markdown report formatting
    md_content = Path(res["md_path"]).read_text(encoding="utf-8")
    assert "⚠️ Not Run (MODEL_HTTP_ERROR)" in md_content
    assert "❌ Validation Failed" in md_content
    assert "— (excluded)" in md_content
