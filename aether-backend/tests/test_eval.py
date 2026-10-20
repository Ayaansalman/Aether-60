"""
Unit tests for the Phase 5 evaluation harness (scripts/run_eval.py).
Tests budget stopping, quota 429 stopping with partial results,
not-run vs failed accounting, and mock banner behavior.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
import pytest

# Ensure scripts and backend root are in sys.path
TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "scripts"))

from providers.base import CompletionResult, ModelProvider, ProviderError, increment_model_request_count
from run_eval import run_evaluation, MOCK_BANNER


class MockFakeProvider:
    """Configurable fake provider for evaluation harness tests."""

    def __init__(self, name: str = "fake-eval-model", fail_on_call: int = -1, error_type: str = "429"):
        self.model_name = name
        self.call_count = 0
        self.fail_on_call = fail_on_call
        self.error_type = error_type

    def complete(self, system: str, user: str) -> CompletionResult:
        self.call_count += 1
        increment_model_request_count()

        if self.call_count == self.fail_on_call:
            if self.error_type == "429":
                raise ProviderError("MODEL_HTTP_ERROR", "HTTP 429: You exceeded your current quota.")
            elif self.error_type == "503":
                raise ProviderError("MODEL_HTTP_ERROR", "HTTP 503: Service Unavailable")
            else:
                raise ProviderError("MODEL_TIMEOUT", "Request timed out")

        spec = {
            "schema_version": "1.0",
            "title": f"Fake Game {self.call_count}",
            "genre": "arena_survival",
            "premise": "A test game",
            "theme": "sci_fi",
            "player": {"move_speed": 220, "max_health": 3, "attack_mode": "projectile"},
            "enemies": [{"type": "chaser", "count": 3, "speed": 60}],
            "collectibles": [{"type": "gem", "count": 5}],
            "objective": {"type": "collect_count", "target": 5},
            "difficulty": 2,
            "controls": {"movement": "WASD", "attack": "Space"},
            "seed": 42,
        }
        res_body = {"spec": spec, "limitations": []}
        return CompletionResult(
            text=json.dumps(res_body),
            model=self.model_name,
            latency_ms=25,
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        )


def test_eval_budget_stop(tmp_path, monkeypatch):
    """
    Budget stop test:
    Harness must stop before starting any prompt that would exceed max_requests,
    and mark all remaining prompts as 'not run (budget)'.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    fake_provider = MockFakeProvider()
    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    # Set budget to 2 requests
    summary = run_evaluation(
        real_flag=False,
        max_requests=2,
        delay_seconds=0.0,
        qa_mode="fake",
        output_dir=out_dir,
        docs_file=docs_file,
        custom_provider=fake_provider,
    )

    records = summary["records"]
    assert len(records) == 12  # All 12 prompts represented
    # Exactly 2 attempted, remaining 10 marked NOT_RUN
    attempted = [r for r in records if r["final_status"] != "NOT_RUN"]
    not_run = [r for r in records if r["final_status"] == "NOT_RUN"]

    assert len(attempted) == 2
    assert len(not_run) == 10
    for r in not_run:
        assert r["failure_category"] == "not_run"
        assert r["notes"] == "not run (budget)"

    assert summary["total_model_requests"] == 2


def test_eval_quota_429_stop(tmp_path, monkeypatch):
    """
    Quota 429 fast-fail test:
    On quota 429, the harness must halt the run, mark the run status as 'incomplete',
    save partial results, and mark remaining prompts as not run.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    # Fail on prompt 2 with quota error
    fake_provider = MockFakeProvider(fail_on_call=2, error_type="429")
    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    summary = run_evaluation(
        real_flag=False,
        max_requests=18,
        delay_seconds=0.0,
        qa_mode="fake",
        output_dir=out_dir,
        docs_file=docs_file,
        custom_provider=fake_provider,
    )

    assert summary["run_status"] == "incomplete"
    records = summary["records"]

    # Prompt 1 should be READY
    assert records[0]["final_status"] in ("READY", "READY_WITH_WARNINGS")

    # Prompt 2 should be PROVIDER_ERROR with MODEL_HTTP_ERROR
    assert records[1]["final_status"] == "FAILED"
    assert records[1]["failure_category"] == "provider_error"
    assert records[1]["error_code"] == "MODEL_HTTP_ERROR"

    # Remaining prompts should be not_run
    for r in records[2:]:
        assert r["final_status"] == "NOT_RUN"
        assert r["failure_category"] == "not_run"

    # Partial artifacts must exist on disk
    json_files = list(out_dir.glob("*.json"))
    md_files = list(out_dir.glob("*.md"))
    assert len(json_files) == 1
    assert len(md_files) == 1
    assert docs_file.exists()


def test_eval_accounting_denominators(tmp_path, monkeypatch):
    """
    Accounting test:
    Verify that 'not run' and 'provider_error' are separate from 'validation failed',
    and latency and validation rates are computed ONLY over prompts that received a model response.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    # Prompt 1 passes, prompt 2 fails with 429, prompts 3..12 not run
    fake_provider = MockFakeProvider(fail_on_call=2, error_type="429")
    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    summary = run_evaluation(
        real_flag=False,
        max_requests=18,
        delay_seconds=0.0,
        qa_mode="fake",
        output_dir=out_dir,
        docs_file=docs_file,
        custom_provider=fake_provider,
    )

    # Prompt 1 got model response. Prompt 2 threw HTTP error (no model response GameIR).
    # Denominator for model response should be 1.
    assert summary["prompts_with_model_response"] == 1
    assert summary["spec_validated_first_rate"] == "1/1 (100.0%)"
    assert summary["playable_at_1_rate"] == "1/1 (100.0%)"
    assert summary["playable_at_3_rate"] == "1/1 (100.0%)"


def test_eval_mock_banner(tmp_path, monkeypatch, capsys):
    """
    Mock banner test:
    Verifies that running in mock mode outputs the required banner and
    writes provider='mock' everywhere.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    summary = run_evaluation(
        real_flag=False,
        max_requests=2,
        delay_seconds=0.0,
        qa_mode="fake",
        output_dir=out_dir,
        docs_file=docs_file,
    )

    captured = capsys.readouterr()
    assert "MOCK PROVIDER: not a real model, results are not evidence" in captured.out
    assert summary["provider"] == "mock"
    assert summary["is_mock"] is True


def test_eval_refuses_real_without_flag(monkeypatch):
    """
    Real flag enforcement test:
    If MODEL_PROVIDER is not mock and --real is omitted, run_evaluation must refuse to run.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "openai_compat")
    with pytest.raises(SystemExit) as excinfo:
        run_evaluation(real_flag=False, custom_provider=None)
    assert excinfo.value.code == 1


def test_eval_honest_limitations_latency_and_ids(tmp_path, monkeypatch):
    """
    Verifies:
    1. Limitation honesty is computed ONLY over prompts with expect_limitation=True.
    2. Non-limitation prompts that disclosed limitations are separately counted.
    3. Min, max, and median latency are computed.
    4. filter_ids (--ids) accurately selects specific prompts.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    # Run on p01, p09
    # p01: expect_limitation=False
    # p09: expect_limitation=True
    summary = run_evaluation(
        real_flag=False,
        max_requests=18,
        delay_seconds=0.0,
        qa_mode="fake",
        filter_ids=["p01", "p09"],
        output_dir=out_dir,
        docs_file=docs_file,
    )

    assert summary["total_prompts"] == 2
    assert summary["prompts_with_model_response"] == 2
    # p09 is the only limitation prompt
    assert summary["limitation_honesty_rate"] == "1/1 (100.0%)"
    # p01 is not a limitation prompt, but in mock may or may not disclose limitations
    assert "non_limit_disclosed_count" in summary
    assert summary["min_latency_ms"] > 0
    assert summary["max_latency_ms"] >= summary["min_latency_ms"]
    assert summary["median_latency_ms"] >= summary["min_latency_ms"]


def test_eval_timeout_continues_next_prompt(tmp_path, monkeypatch):
    """
    Timeout handling test:
    A model timeout must be recorded as provider_error for that prompt,
    and the harness must NOT halt; it continues with subsequent prompts.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    fake_provider = MockFakeProvider(fail_on_call=2, error_type="timeout")
    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    summary = run_evaluation(
        real_flag=False,
        max_requests=18,
        delay_seconds=0.0,
        qa_mode="fake",
        filter_ids=["p01", "p02", "p03"],
        output_dir=out_dir,
        docs_file=docs_file,
        custom_provider=fake_provider,
    )

    assert summary["run_status"] == "complete"
    assert summary["prompts_attempted"] == 3
    records = summary["records"]

    # Prompt 1 succeeds
    assert records[0]["id"] == "p01"
    assert records[0]["final_status"] in ("READY", "READY_WITH_WARNINGS")

    # Prompt 2 failed with timeout recorded as provider_error
    assert records[1]["id"] == "p02"
    assert records[1]["final_status"] == "FAILED"
    assert records[1]["failure_category"] == "provider_error"
    assert records[1]["error_code"] == "MODEL_TIMEOUT"

    # Prompt 3 was executed (run did NOT stop)
    assert records[2]["id"] == "p03"
    assert records[2]["final_status"] in ("READY", "READY_WITH_WARNINGS")


def test_eval_http_503_continues_next_prompt(tmp_path, monkeypatch):
    """
    503 error handling test:
    A 503 Service Unavailable error must be recorded as provider_error for that prompt,
    and the harness continues with subsequent prompts.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    fake_provider = MockFakeProvider(fail_on_call=2, error_type="503")
    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    summary = run_evaluation(
        real_flag=False,
        max_requests=18,
        delay_seconds=0.0,
        qa_mode="fake",
        filter_ids=["p01", "p02", "p03"],
        output_dir=out_dir,
        docs_file=docs_file,
        custom_provider=fake_provider,
    )

    assert summary["run_status"] == "complete"
    assert summary["prompts_attempted"] == 3
    records = summary["records"]

    assert records[1]["id"] == "p02"
    assert records[1]["final_status"] == "FAILED"
    assert records[1]["failure_category"] == "provider_error"
    assert records[1]["error_code"] == "MODEL_HTTP_ERROR"

    assert records[2]["id"] == "p03"
    assert records[2]["final_status"] in ("READY", "READY_WITH_WARNINGS")


def test_eval_configurable_timeout(tmp_path, monkeypatch):
    """
    Configurable timeout test:
    Verify that timeout parameter or MODEL_TIMEOUT_SECONDS sets request_timeout_seconds
    and appears in the artifact header.
    """
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("QA_MODE", "fake")

    out_dir = tmp_path / "artifacts_eval"
    docs_file = tmp_path / "EVAL_RESULTS.md"

    # Explicit timeout argument
    summary = run_evaluation(
        real_flag=False,
        max_requests=2,
        delay_seconds=0.0,
        qa_mode="fake",
        filter_ids=["p01"],
        output_dir=out_dir,
        docs_file=docs_file,
        timeout=45.0,
    )

    assert summary["request_timeout_seconds"] == 45.0
    md_files = list(out_dir.glob("*.md"))
    assert len(md_files) == 1
    md_content = md_files[0].read_text(encoding="utf-8")
    assert "- **Request Timeout:** 45.0 s" in md_content


