"""
Tests for the bounded parameter-repair service (services/repair.py) and the labeled mock repair responder.
Conforms to Phase 4 acceptance criteria: patch validation, bounds, no-op rejection, extra=forbid.
"""

import json
from pathlib import Path
from typing import List

import pytest

from providers.base import CompletionResult, ModelHttpError, ModelTimeoutError, REPAIR_AGENT_MARKER
from providers.mock import MOCK_LABEL, TOO_HARD_SPEC, MockModelProvider
from schemas.game_ir import GameIR
from services.planner import plan_game
from services.qa_runner import _flee_vector
from services.repair import (
    build_repair_system_prompt,
    compute_spec_diff,
    parse_patch,
    propose_repair,
)
from services.validator import validate_game_ir

FRONTEND_TOO_HARD = (
    Path(__file__).resolve().parents[2] / "aether-frontend" / "src" / "game" / "sample-too-hard.json"
)

FAILED_REPORT = {
    "overall": "FAIL",
    "checks": [
        {"id": "canvas_visible", "critical": True, "patchable": False, "passed": True, "message": ""},
        {
            "id": "idle_survival_min_seconds",
            "critical": True,
            "patchable": True,
            "passed": False,
            "message": "Idle player died after 0.9s (< 4.0s required) with no input",
            "measured": {"survived_seconds": 0.9},
        },
        {
            "id": "flee_bot_survives",
            "critical": True,
            "patchable": True,
            "passed": False,
            "message": "Flee bot died after 1.7s (needed 12.0s)",
            "measured": {"survived_seconds": 1.7},
        },
    ],
}


class ScriptedProvider:
    """Returns pre-scripted replies in order; records the prompts it received."""

    model_name = "scripted-test-model"

    def __init__(self, replies: List[str]):
        self.replies = list(replies)
        self.calls: List[dict] = []

    def complete(self, system: str, user: str) -> CompletionResult:
        self.calls.append({"system": system, "user": user})
        text = self.replies.pop(0)
        return CompletionResult(text=text, model=self.model_name, latency_ms=5, usage={})


def _too_hard() -> GameIR:
    return GameIR.model_validate(TOO_HARD_SPEC)


# --------------------------------------------------------------------------
# Fixture integrity
# --------------------------------------------------------------------------
def test_too_hard_sample_is_valid_gameir_and_matches_frontend_file():
    assert validate_game_ir(TOO_HARD_SPEC).ok
    frontend = json.loads(FRONTEND_TOO_HARD.read_text(encoding="utf-8"))
    assert frontend == TOO_HARD_SPEC
    enemy = TOO_HARD_SPEC["enemies"][0]
    assert enemy["count"] == 12 and enemy["speed"] == 240
    assert TOO_HARD_SPEC["player"]["max_health"] == 1
    assert TOO_HARD_SPEC["difficulty"] == 5


# --------------------------------------------------------------------------
# Patch validation (extra=forbid) and prompt contract
# --------------------------------------------------------------------------
def test_system_prompt_lists_allowed_fields_and_forbids_theme_changes():
    prompt = build_repair_system_prompt()
    for key in (
        "player_move_speed",
        "player_max_health",
        "enemy_speed_multiplier",
        "enemy_count",
        "objective_target",
        "difficulty",
    ):
        assert key in prompt
    assert REPAIR_AGENT_MARKER in prompt
    assert "JSON" in prompt
    assert "theme" in prompt and "title" in prompt and "objective type" in prompt and "genre" in prompt
    assert "minimal" in prompt.lower()


@pytest.mark.parametrize("forbidden", ["theme", "title", "genre", "premise", "objective_type", "seed"])
def test_parse_patch_rejects_forbidden_or_unknown_keys(forbidden):
    patch, errors = parse_patch(json.dumps({"enemy_count": 4, forbidden: "x", "rationale": "r"}))
    assert patch is None
    assert errors and any(forbidden in e for e in errors)


def test_parse_patch_accepts_fenced_json_and_envelope():
    fenced = '```json\n{"enemy_count": 4, "rationale": "fewer enemies"}\n```'
    patch, errors = parse_patch(fenced)
    assert errors == [] and patch is not None and patch.enemy_count == 4

    enveloped = json.dumps({"patch": {"enemy_count": 3}, "rationale": "env"})
    patch2, errors2 = parse_patch(enveloped)
    assert errors2 == [] and patch2 is not None and patch2.enemy_count == 3 and patch2.rationale == "env"


def test_parse_patch_rejects_non_json_and_wrong_types():
    assert parse_patch("not json at all")[0] is None
    assert parse_patch("[1, 2, 3]")[0] is None
    patch, errors = parse_patch(json.dumps({"enemy_count": "lots"}))
    assert patch is None and errors


# --------------------------------------------------------------------------
# propose_repair: bounds, no-op rejection, retry, error handling
# --------------------------------------------------------------------------
def test_propose_repair_applies_valid_patch_and_computes_diff():
    reply = json.dumps(
        {"enemy_speed_multiplier": 0.5, "enemy_count": 6, "player_max_health": 3, "rationale": "easier"}
    )
    provider = ScriptedProvider([reply])
    result = propose_repair(_too_hard(), FAILED_REPORT, provider)

    assert result.ok and result.attempts == 1
    assert result.spec is not None
    assert result.rationale == "easier"
    assert result.spec.enemies[0].speed == 120.0
    assert result.spec.enemies[0].count == 6
    assert result.spec.player.max_health == 3
    assert result.diff["before"]["enemies[0].speed"] == 240.0
    assert result.diff["after"]["enemies[0].speed"] == 120.0
    assert result.diff["before"]["player.max_health"] == 1
    # Forbidden fields untouched
    assert result.spec.theme == "sci_fi" and result.spec.title == TOO_HARD_SPEC["title"]
    assert result.spec.objective.type == "survive_seconds" and result.spec.genre == "arena_survival"
    # The model saw the failed checks
    assert "idle_survival_min_seconds" in provider.calls[0]["user"]


def test_propose_repair_clamps_out_of_range_values_to_contract_bounds():
    reply = json.dumps(
        {
            "enemy_speed_multiplier": 0.0001,
            "player_max_health": 99,
            "player_move_speed": 9999,
            "enemy_count": 500,
            "difficulty": 0,
            "rationale": "extreme",
        }
    )
    result = propose_repair(_too_hard(), FAILED_REPORT, ScriptedProvider([reply]))
    assert result.ok
    assert result.spec is not None
    assert result.spec.enemies[0].speed == 20.0  # clamped to min
    assert result.spec.player.max_health == 10
    assert result.spec.player.move_speed == 300.0
    assert result.spec.enemies[0].count == 50
    assert result.spec.difficulty == 1


def test_noop_patch_rejected_then_one_retry_succeeds():
    provider = ScriptedProvider(
        [
            json.dumps({"enemy_count": 12, "rationale": "same as before"}),  # no-op
            json.dumps({"enemy_count": 6, "rationale": "now different"}),
        ]
    )
    result = propose_repair(_too_hard(), FAILED_REPORT, provider)
    assert result.ok and result.attempts == 2
    assert result.spec is not None
    assert "no-op" in provider.calls[1]["user"].lower()
    assert result.spec.enemies[0].count == 6


def test_noop_patch_twice_fails_without_exception():
    provider = ScriptedProvider(
        [json.dumps({"rationale": "nothing"}), json.dumps({"enemy_count": 12, "rationale": "still nothing"})]
    )
    result = propose_repair(_too_hard(), FAILED_REPORT, provider)
    assert not result.ok
    assert result.patch is None and result.spec is None
    assert result.attempts == 2
    assert result.error_code == "MODEL_OUTPUT_INVALID"
    assert any("no-op" in e.lower() for e in result.errors)


def test_theme_change_attempt_is_rejected_both_times():
    bad = json.dumps({"theme": "pirate", "enemy_count": 3, "rationale": "sneaky"})
    result = propose_repair(_too_hard(), FAILED_REPORT, ScriptedProvider([bad, bad]))
    assert not result.ok
    assert any("theme" in e for e in result.errors)


def test_provider_errors_are_returned_not_raised():
    class Boom:
        model_name = "boom"

        def __init__(self, exc):
            self.exc = exc

        def complete(self, system, user):
            raise self.exc

    http = propose_repair(_too_hard(), FAILED_REPORT, Boom(ModelHttpError("Model HTTP 429 error")))
    assert not http.ok and http.error_code == "MODEL_HTTP_ERROR"

    timeout = propose_repair(_too_hard(), FAILED_REPORT, Boom(ModelTimeoutError("slow")))
    assert not timeout.ok and timeout.error_code == "MODEL_TIMEOUT"


def test_compute_spec_diff_only_lists_changed_fields():
    before = _too_hard()
    after_data = before.model_dump()
    after_data["enemies"][0]["count"] = 6
    after = GameIR.model_validate(after_data)
    diff = compute_spec_diff(before, after)
    assert diff == {"before": {"enemies[0].count": 12}, "after": {"enemies[0].count": 6}}


# --------------------------------------------------------------------------
# Mock provider: labeled deterministic repair responder + 'repair demo' prompt
# --------------------------------------------------------------------------
def test_mock_planner_repair_demo_prompt_returns_too_hard_spec():
    result = plan_game("a repair demo please", MockModelProvider())
    assert result.ok
    assert result.spec is not None
    assert result.spec.model_dump() == GameIR.model_validate(TOO_HARD_SPEC).model_dump()
    assert any("MOCK PROVIDER" in lim for lim in result.limitations)


def test_mock_repair_responder_is_deterministic_labeled_and_effective():
    provider = MockModelProvider()
    first = propose_repair(_too_hard(), FAILED_REPORT, provider)
    again = propose_repair(_too_hard(), FAILED_REPORT, provider)
    assert first.ok and again.ok
    assert first.spec is not None and again.spec is not None
    assert first.spec.model_dump() == again.spec.model_dump()  # deterministic
    assert MOCK_LABEL in first.rationale

    spec = first.spec
    assert spec.enemies[0].speed <= 0.45 * spec.player.move_speed + 1e-6
    assert spec.enemies[0].count <= 6
    assert spec.player.max_health >= 3
    assert spec.difficulty <= 3


def test_mock_repair_never_returns_noop_on_repeated_repairs():
    provider = MockModelProvider()
    spec = _too_hard()
    seen = {json.dumps(spec.model_dump(), sort_keys=True)}
    for _ in range(3):
        result = propose_repair(spec, FAILED_REPORT, provider)
        assert result.ok
        assert result.spec is not None
        key = json.dumps(result.spec.model_dump(), sort_keys=True)
        assert key not in seen
        seen.add(key)
        spec = result.spec


# --------------------------------------------------------------------------
# Flee-bot steering helper (pure function used by the QA runner)
# --------------------------------------------------------------------------
def test_flee_vector_runs_away_from_nearest_enemy():
    vx, vy, nearest = _flee_vector({"x": 400, "y": 300}, [{"x": 500, "y": 300}])
    assert vx < 0 and abs(vy) < 1e-6
    assert nearest == pytest.approx(100.0)


def test_flee_vector_pushes_away_from_walls_toward_centre():
    # Player hugging the left wall with the enemy on the right: the wall term must reduce the push into the wall.
    vx_wall, _, _ = _flee_vector({"x": 20, "y": 300}, [{"x": 120, "y": 300}])
    vx_open, _, _ = _flee_vector({"x": 400, "y": 300}, [{"x": 500, "y": 300}])
    assert vx_wall > vx_open  # wall repulsion pushes toward +x (centre)


# --------------------------------------------------------------------------
# State machine tests: fail, fail, pass -> READY; fail x3 -> FAILED; non-patchable -> no repair
# --------------------------------------------------------------------------
import uuid
from unittest.mock import patch
from services import event_store, job_store
from services.orchestrator import get_artifacts_dir, run_single_job


@pytest.fixture
def repair_env(tmp_path, monkeypatch):
    test_db = tmp_path / "test_repair.db"
    test_artifacts = tmp_path / "artifacts"
    test_artifacts.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AETHER_DB_PATH", str(test_db))
    monkeypatch.setenv("AETHER_ARTIFACTS_DIR", str(test_artifacts))
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    job_store.init_job_store(test_db)
    event_store.init_event_store(test_db)
    return {"db": test_db, "artifacts": test_artifacts}


def _qa_report_sample(passed: bool, patchable: bool = True, check_id: str = "idle_survival_min_seconds"):
    return {
        "overall": "PASS" if passed else "FAIL",
        "checks": [
            {
                "id": check_id,
                "critical": True,
                "patchable": patchable,
                "passed": passed,
                "message": "" if passed else f"Simulated failure of {check_id}",
            }
        ],
        "page_errors": [],
    }


@pytest.mark.anyio
async def test_state_machine_fail_fail_pass_reaches_ready(repair_env):
    """Fail (attempt 1) -> Repair -> Fail (attempt 2) -> Repair -> Pass (attempt 3) -> READY."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "a repair demo game")

    reports = [
        _qa_report_sample(passed=False, patchable=True, check_id="idle_survival_min_seconds"),
        _qa_report_sample(passed=False, patchable=True, check_id="flee_bot_survives"),
        _qa_report_sample(passed=True, patchable=True, check_id="idle_survival_min_seconds"),
    ]

    async def mock_execute_qa(game_id, game_url, artifacts_dir, attempt):
        return reports[attempt - 1]

    with patch("services.orchestrator.execute_qa", side_effect=mock_execute_qa):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "READY"
    assert job["stage"] == "TESTING"
    assert job["error_code"] is None

    # Check versioned spec artifacts
    j_dir = get_artifacts_dir() / gid
    assert (j_dir / "game_ir_v1.json").exists()
    assert (j_dir / "game_ir_v2.json").exists()
    assert (j_dir / "game_ir_v3.json").exists()
    assert (j_dir / "qa_report_attempt_1.json").exists()
    assert (j_dir / "qa_report_attempt_2.json").exists()
    assert (j_dir / "qa_report_attempt_3.json").exists()

    events = event_store.get_events(gid)
    repair_events = [e for e in events if e["stage"] == "REPAIRING"]
    assert len(repair_events) >= 2


@pytest.mark.anyio
async def test_state_machine_fail_x3_ends_failed_repair_limit_reached(repair_env):
    """Fail x3 reaches bounded repair limit (2 repairs max) and ends FAILED with REPAIR_LIMIT_REACHED."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "unrepairable game")

    always_fail = _qa_report_sample(passed=False, patchable=True, check_id="idle_survival_min_seconds")

    async def mock_execute_qa(game_id, game_url, artifacts_dir, attempt):
        return always_fail

    with patch("services.orchestrator.execute_qa", side_effect=mock_execute_qa):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "REPAIR_LIMIT_REACHED"

    events = event_store.get_events(gid)
    failed_events = [e for e in events if e["result"] == "FAILED"]
    assert any("REPAIR_LIMIT_REACHED" in e["detail"] or "repair" in e["detail"].lower() for e in failed_events)


@pytest.mark.anyio
async def test_state_machine_non_patchable_skips_repair(repair_env):
    """A non-patchable check failure (runtime bug) does not trigger repair; logs needs developer and fails."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "broken runtime game")

    runtime_fail = _qa_report_sample(passed=False, patchable=False, check_id="canvas_visible")

    async def mock_execute_qa(game_id, game_url, artifacts_dir, attempt):
        return runtime_fail

    with patch("services.orchestrator.execute_qa", side_effect=mock_execute_qa):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "QA_FAILED"
    assert job["attempt"] == 1

    events = event_store.get_events(gid)
    skipped = [e for e in events if e["stage"] == "REPAIRING" and e["result"] == "SKIPPED"]
    assert len(skipped) == 1
    assert "Needs developer" in skipped[0]["detail"]

    # No second spec was produced
    j_dir = get_artifacts_dir() / gid
    assert not (j_dir / "game_ir_v2.json").exists()


@pytest.mark.anyio
async def test_state_machine_qa_crashed_when_runner_crashes(repair_env):
    """QA suite timeout or subprocess crash ends FAILED with QA_CRASHED and no repair."""
    gid = str(uuid.uuid4())
    job_store.create_job(gid, "runner crashed game")

    from services.orchestrator import QARunError

    async def mock_crashing_qa(game_id, game_url, artifacts_dir, attempt):
        raise QARunError("QA runner timed out after 120s", "TESTING_TIMEOUT", {"timeout": 120, "attempt": attempt})

    with patch("services.orchestrator.execute_qa", side_effect=mock_crashing_qa):
        await run_single_job(gid)

    job = job_store.get_job(gid)
    assert job is not None
    assert job["status"] == "FAILED"
    assert job["error_code"] == "QA_CRASHED"
    assert job["attempt"] == 1

    events = event_store.get_events(gid)
    failed_evts = [e for e in events if e["stage"] == "TESTING" and e["result"] == "FAILED"]
    assert len(failed_evts) == 1
    assert "timed out" in failed_evts[0]["detail"].lower()


