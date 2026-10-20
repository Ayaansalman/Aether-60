"""
Unit and contract tests for GameIR v1.0 and Validator service.
Validates frontend sample JSON specifications and negative boundary conditions.
"""

import json
from pathlib import Path
import pytest

from schemas.game_ir import GameIR, GameIRPatch, apply_patch
from services.validator import validate_game_ir

# Path to aether-frontend sample JSON files
FRONTEND_GAME_DIR = Path(__file__).resolve().parent.parent.parent / "aether-frontend" / "src" / "game"


@pytest.fixture
def sample_collect_json():
    sample_path = FRONTEND_GAME_DIR / "sample-gameir.json"
    assert sample_path.exists(), f"sample-gameir.json not found at {sample_path}"
    with open(sample_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_survive_json():
    sample_path = FRONTEND_GAME_DIR / "sample-survive.json"
    assert sample_path.exists(), f"sample-survive.json not found at {sample_path}"
    with open(sample_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_sample_gameir_passes_unchanged(sample_collect_json):
    """The default Wizard Crystal Rush sample must pass validation completely."""
    result = validate_game_ir(sample_collect_json)
    assert result.ok is True, f"Validation failed unexpectedly: {result.errors}"
    assert result.spec is not None
    assert result.spec.title == "Wizard Crystal Rush"
    assert result.spec.objective.type == "collect_count"
    assert result.spec.objective.target == 8


def test_sample_survive_passes_unchanged(sample_survive_json):
    """The survival demo sample must pass validation completely."""
    result = validate_game_ir(sample_survive_json)
    assert result.ok is True, f"Validation failed unexpectedly: {result.errors}"
    assert result.spec is not None
    assert result.spec.title == "Neon Void Survival"
    assert result.spec.objective.type == "survive_seconds"
    assert result.spec.objective.target == 30


def test_out_of_range_speed_fails(sample_collect_json):
    """Move speed outside [100, 300] must fail validation."""
    # Under minimum
    sample_collect_json["player"]["move_speed"] = 50.0
    result_low = validate_game_ir(sample_collect_json)
    assert result_low.ok is False
    assert any("move_speed" in err for err in result_low.errors)

    # Over maximum
    sample_collect_json["player"]["move_speed"] = 450.0
    result_high = validate_game_ir(sample_collect_json)
    assert result_high.ok is False
    assert any("move_speed" in err for err in result_high.errors)


def test_too_many_enemies_fails(sample_collect_json):
    """More than 2 enemy types must fail validation."""
    sample_collect_json["enemies"] = [
        {"type": "chaser", "count": 3, "speed": 60},
        {"type": "chaser", "count": 5, "speed": 90},
        {"type": "chaser", "count": 2, "speed": 50},
    ]
    result = validate_game_ir(sample_collect_json)
    assert result.ok is False
    assert any("enemies" in err for err in result.errors)


def test_enemy_type_invalid_fails(sample_collect_json):
    """Unsupported enemy type like 'teleporter' must fail schema validation."""
    sample_collect_json["enemies"][0]["type"] = "teleporter"
    result = validate_game_ir(sample_collect_json)
    assert result.ok is False
    assert any("enemies" in err for err in result.errors)


def test_unknown_objective_type_fails(sample_collect_json):
    """An unrecognised objective type must fail validation."""
    sample_collect_json["objective"]["type"] = "destroy_boss"
    result = validate_game_ir(sample_collect_json)
    assert result.ok is False
    assert any("objective" in err for err in result.errors)


def test_unknown_key_rejected(sample_collect_json):
    """Unapproved arbitrary keys must be rejected because extra='forbid'."""
    sample_collect_json["unapproved_custom_field"] = "malicious_payload"
    result = validate_game_ir(sample_collect_json)
    assert result.ok is False
    assert any("unapproved_custom_field" in err for err in result.errors)


def test_target_greater_than_collectibles_fails(sample_collect_json):
    """Semantic check: collect target greater than available collectibles must fail."""
    # sample has 10 collectibles total; set target to 15
    sample_collect_json["objective"]["target"] = 15
    result = validate_game_ir(sample_collect_json)
    assert result.ok is False
    assert any("exceeds total available collectibles" in err for err in result.errors)


def test_premise_with_medieval_castle_passes(sample_collect_json):
    """A natural language premise containing 'a medieval castle' must pass without false positive alarms."""
    sample_collect_json["premise"] = "Escape a medieval castle while ghosts patrol the stone hallways."
    result = validate_game_ir(sample_collect_json)
    assert result.ok is True, f"Premise was falsely rejected: {result.errors}"


def test_url_or_code_in_premise_fails(sample_collect_json):
    """Safety check: URL or code injection patterns in premise must fail."""
    # HTTP URL http://evil.com
    sample_collect_json["premise"] = "Collect crystals at http://evil.com"
    result_url = validate_game_ir(sample_collect_json)
    assert result_url.ok is False
    assert any("https?://" in err or "http" in err.lower() for err in result_url.errors)

    # HTTPS URL
    sample_collect_json["premise"] = "See details at https://phishing.net/game"
    result_https = validate_game_ir(sample_collect_json)
    assert result_https.ok is False
    assert any("https?://" in err or "https" in err.lower() for err in result_https.errors)

    # Script tag
    sample_collect_json["premise"] = "Collect gems <script>alert(1)</script>"
    result_script = validate_game_ir(sample_collect_json)
    assert result_script.ok is False
    assert any("script" in err.lower() for err in result_script.errors)

    # Eval
    sample_collect_json["premise"] = "Player speed eval(100)"
    result_eval = validate_game_ir(sample_collect_json)
    assert result_eval.ok is False
    assert any("eval" in err.lower() for err in result_eval.errors)

    # Arrow operator
    sample_collect_json["premise"] = "Player => speedup"
    result_code = validate_game_ir(sample_collect_json)
    assert result_code.ok is False
    assert any("=>" in err.lower() for err in result_code.errors)


def test_apply_patch_clamps_values(sample_collect_json):
    """apply_patch must clamp out-of-range tuning values to legal contract boundaries."""
    base_spec = GameIR.model_validate(sample_collect_json)

    # Patch with extreme values
    patch = GameIRPatch(
        player_move_speed=999.0,   # Max legal is 300.0
        player_max_health=99,      # Max legal is 10
        difficulty=10,             # Max legal is 5
        enemy_count=100,           # Max legal is 50
        objective_target=50,       # Max legal for collect_count is 20
        rationale="Stress test bounding"
    )

    repaired_spec = apply_patch(base_spec, patch)

    assert repaired_spec.player.move_speed == 300.0
    assert repaired_spec.player.max_health == 10
    assert repaired_spec.difficulty == 5
    assert repaired_spec.enemies[0].count == 50
    assert repaired_spec.objective.target == 20
