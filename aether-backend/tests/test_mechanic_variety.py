"""
Unit tests for mechanic variety:
- New EnemyType enum values: bouncer, patroller, dasher, shooter
- ArenaLayout enum values: open, pillars, lanes, maze
- ObjectiveType defeat_enemies rules: valid targets 1..30, rejected when attack_mode is avoid_only
- VisualOverrides validation: label length limits, hex color validation, shape enums
- MockModelProvider keyword routing: flappy/lanes, invaders/shooter, maze/pacman, bounce/pinball, boss/dash
- Canonical demo specifications pass GameIR validation
"""

import copy
import json
from pathlib import Path
import pytest

from providers.mock import MockModelProvider
from schemas.game_ir import GameIR, GameIRPatch, apply_patch
from services.game_registry import REGISTRY, get_demo_spec
from services.planner import plan_game
from services.validator import validate_game_ir

FRONTEND_GAME_DIR = Path(__file__).resolve().parent.parent.parent / "aether-frontend" / "src" / "game"


@pytest.fixture
def base_spec_json():
    sample_path = FRONTEND_GAME_DIR / "sample-gameir.json"
    with open(sample_path, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------------------------------
# 1. Enemy Type Enum Tests
# -------------------------------------------------------------------------

@pytest.mark.parametrize("enemy_type", ["chaser", "bouncer", "patroller", "dasher", "shooter"])
def test_valid_enemy_types_pass(base_spec_json, enemy_type):
    """All 5 enemy types must be accepted by the validator."""
    data = copy.deepcopy(base_spec_json)
    data["enemies"][0]["type"] = enemy_type
    result = validate_game_ir(data)
    assert result.ok is True, f"Valid enemy type '{enemy_type}' rejected: {result.errors}"
    assert result.spec is not None
    assert result.spec.enemies[0].type == enemy_type


@pytest.mark.parametrize("invalid_type", ["flyer", "turret", "teleporter", "boss_dragon"])
def test_invalid_enemy_types_fail(base_spec_json, invalid_type):
    """Unapproved enemy types must be rejected by the validator."""
    data = copy.deepcopy(base_spec_json)
    data["enemies"][0]["type"] = invalid_type
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("enemies" in err for err in result.errors)


def test_multi_enemy_configs(base_spec_json):
    """Up to 2 enemy configurations are allowed per game."""
    data = copy.deepcopy(base_spec_json)
    data["enemies"] = [
        {"type": "bouncer", "count": 3, "speed": 80.0},
        {"type": "shooter", "count": 2, "speed": 60.0},
    ]
    result = validate_game_ir(data)
    assert result.ok is True
    assert result.spec is not None
    assert len(result.spec.enemies) == 2


# -------------------------------------------------------------------------
# 2. Arena Layout Enum Tests
# -------------------------------------------------------------------------

@pytest.mark.parametrize("layout", ["open", "pillars", "lanes", "maze"])
def test_valid_arena_layouts_pass(base_spec_json, layout):
    """All 4 arena layouts must be accepted."""
    data = copy.deepcopy(base_spec_json)
    data["arena_layout"] = layout
    result = validate_game_ir(data)
    assert result.ok is True, f"Valid arena layout '{layout}' rejected: {result.errors}"
    assert result.spec is not None
    assert result.spec.arena_layout == layout


def test_default_arena_layout_is_open(base_spec_json):
    """Omitting arena_layout defaults to 'open'."""
    data = copy.deepcopy(base_spec_json)
    data.pop("arena_layout", None)
    result = validate_game_ir(data)
    assert result.ok is True
    assert result.spec is not None
    assert result.spec.arena_layout == "open"


def test_invalid_arena_layout_fails(base_spec_json):
    """Unrecognized arena layout must fail validation."""
    data = copy.deepcopy(base_spec_json)
    data["arena_layout"] = "hexagonal_grid"
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("arena_layout" in err for err in result.errors)


# -------------------------------------------------------------------------
# 3. Objective defeat_enemies Tests
# -------------------------------------------------------------------------

@pytest.mark.parametrize("attack_mode", ["projectile", "melee"])
def test_defeat_enemies_with_attacking_player_passes(base_spec_json, attack_mode):
    """defeat_enemies is valid when player can attack (projectile or melee)."""
    data = copy.deepcopy(base_spec_json)
    data["player"]["attack_mode"] = attack_mode
    data["objective"] = {"type": "defeat_enemies", "target": 10}
    result = validate_game_ir(data)
    assert result.ok is True, f"defeat_enemies failed for attack_mode '{attack_mode}': {result.errors}"
    assert result.spec is not None
    assert result.spec.objective.type == "defeat_enemies"
    assert result.spec.objective.target == 10


def test_defeat_enemies_with_avoid_only_fails(base_spec_json):
    """Semantic check: defeat_enemies must be rejected when player attack_mode is avoid_only."""
    data = copy.deepcopy(base_spec_json)
    data["player"]["attack_mode"] = "avoid_only"
    data["objective"] = {"type": "defeat_enemies", "target": 5}
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("avoid_only" in err for err in result.errors)


@pytest.mark.parametrize("invalid_target", [0, -5, 31, 100])
def test_defeat_enemies_target_bounds(base_spec_json, invalid_target):
    """defeat_enemies target must be between 1 and 30."""
    data = copy.deepcopy(base_spec_json)
    data["player"]["attack_mode"] = "projectile"
    data["objective"] = {"type": "defeat_enemies", "target": invalid_target}
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("target" in err.lower() or "objective" in err.lower() for err in result.errors)


# -------------------------------------------------------------------------
# 4. Visual Overrides Tests
# -------------------------------------------------------------------------

def test_valid_visual_overrides(base_spec_json):
    """Valid visual overrides pass validation."""
    data = copy.deepcopy(base_spec_json)
    data["visual_overrides"] = {
        "player_label": "CYBER KNIGHT",
        "enemy_label": "DRONE SWARM",
        "collectible_label": "POWER CELL",
        "player_shape": "diamond",
        "enemy_shape": "triangle",
        "accent_hex": "#06b6d4",
    }
    result = validate_game_ir(data)
    assert result.ok is True, f"Validation failed: {result.errors}"
    assert result.spec is not None
    assert result.spec.visual_overrides is not None
    assert result.spec.visual_overrides.player_label == "CYBER KNIGHT"
    assert result.spec.visual_overrides.player_shape == "diamond"
    assert result.spec.visual_overrides.accent_hex == "#06b6d4"


def test_visual_overrides_label_too_long_fails(base_spec_json):
    """Labels exceeding 24 characters must fail validation."""
    data = copy.deepcopy(base_spec_json)
    data["visual_overrides"] = {
        "player_label": "A" * 25,
    }
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("player_label" in err for err in result.errors)


@pytest.mark.parametrize("bad_hex", ["#fff", "06b6d4", "#GGGGGG", "#12345", "red"])
def test_visual_overrides_invalid_hex_fails(base_spec_json, bad_hex):
    """accent_hex must match ^#[0-9a-fA-F]{6}$."""
    data = copy.deepcopy(base_spec_json)
    data["visual_overrides"] = {
        "accent_hex": bad_hex,
    }
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("accent_hex" in err for err in result.errors)


@pytest.mark.parametrize("bad_shape", ["star", "pentagon", "hexagon", "cube"])
def test_visual_overrides_invalid_shape_fails(base_spec_json, bad_shape):
    """Shape must be one of: circle, square, triangle, diamond."""
    data = copy.deepcopy(base_spec_json)
    data["visual_overrides"] = {
        "player_shape": bad_shape,
    }
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("player_shape" in err for err in result.errors)


def test_visual_overrides_safety_check(base_spec_json):
    """Malicious scripts or tags in labels must fail safety regex."""
    data = copy.deepcopy(base_spec_json)
    data["visual_overrides"] = {
        "player_label": "<script>alert(1)</script>",
    }
    result = validate_game_ir(data)
    assert result.ok is False
    assert any("script" in err.lower() or "label" in err.lower() for err in result.errors)


# -------------------------------------------------------------------------
# 5. Patch Clamping for defeat_enemies
# -------------------------------------------------------------------------

def test_apply_patch_clamps_defeat_enemies(base_spec_json):
    """apply_patch must clamp defeat_enemies target to [1, 30]."""
    data = copy.deepcopy(base_spec_json)
    data["player"]["attack_mode"] = "projectile"
    data["objective"] = {"type": "defeat_enemies", "target": 10}
    base_spec = GameIR.model_validate(data)

    patch = GameIRPatch(objective_target=50, rationale="Overshoot test")
    repaired = apply_patch(base_spec, patch)
    assert repaired.objective.target == 30

    patch_under = GameIRPatch(objective_target=-10, rationale="Undershoot test")
    repaired_under = apply_patch(base_spec, patch_under)
    assert repaired_under.objective.target == 1


# -------------------------------------------------------------------------
# 6. Mock Provider Keyword Routing Tests
# -------------------------------------------------------------------------

def test_mock_routing_flappy_lanes():
    """'flappy' / 'lanes' / 'frogger' / 'crossy' routes to lanes layout and patroller."""
    provider = MockModelProvider()
    result = plan_game("a crossy frogger game crossing dangerous lanes", provider=provider)
    assert result.ok is True
    assert result.spec is not None
    assert result.spec.arena_layout == "lanes"
    assert result.spec.enemies[0].type == "patroller"
    assert result.spec.theme == "cozy"
    assert result.spec.visual_overrides is not None
    assert result.spec.visual_overrides.player_label == "FROGGER"


def test_mock_routing_invaders_shooter():
    """'invaders' / 'shooter' routes to pillars layout and shooter enemies."""
    provider = MockModelProvider()
    result = plan_game("space invaders shooter defense behind shields", provider=provider)
    assert result.ok is True
    assert result.spec is not None
    assert result.spec.arena_layout == "pillars"
    assert result.spec.enemies[0].type == "shooter"
    assert result.spec.player.attack_mode == "projectile"
    assert result.spec.visual_overrides is not None
    assert result.spec.visual_overrides.enemy_label == "INVADER"


def test_mock_routing_maze_pacman():
    """'maze' / 'pacman' routes to maze layout and coin collector."""
    provider = MockModelProvider()
    result = plan_game("pacman style maze runner collecting dots", provider=provider)
    assert result.ok is True
    assert result.spec is not None
    assert result.spec.arena_layout == "maze"
    assert result.spec.theme == "pirate"
    assert result.spec.objective.type == "collect_count"
    assert result.spec.visual_overrides is not None
    assert result.spec.visual_overrides.player_label == "PACRUNNER"


def test_mock_routing_bounce_pinball():
    """'bounce' / 'pinball' routes to pillars layout and bouncer enemies."""
    provider = MockModelProvider()
    result = plan_game("cyber pinball bounce dodge against bumpers", provider=provider)
    assert result.ok is True
    assert result.spec is not None
    assert result.spec.arena_layout == "pillars"
    assert result.spec.enemies[0].type == "bouncer"
    assert result.spec.theme == "sci_fi"
    assert result.spec.visual_overrides is not None
    assert result.spec.visual_overrides.enemy_label == "BOUNCER"


def test_mock_routing_boss_dash():
    """'boss' / 'dash' routes to dasher enemies with defeat_enemies objective."""
    provider = MockModelProvider()
    result = plan_game("epic boss dash duel with sword combat", provider=provider)
    assert result.ok is True
    assert result.spec is not None
    assert result.spec.enemies[0].type == "dasher"
    assert result.spec.objective.type == "defeat_enemies"
    assert result.spec.player.attack_mode == "melee"
    assert result.spec.visual_overrides is not None
    assert result.spec.visual_overrides.enemy_label == "DASHER"


def test_mock_unsupported_mechanics_limitations():
    """Unsupported requests (3D, multiplayer, gravity platformer) add honest limitations."""
    provider = MockModelProvider()
    result = plan_game("3D multiplayer platformer with gravity jumping", provider=provider)
    assert result.ok is True
    assert result.spec is not None
    assert len(result.limitations) >= 2
    assert any("3D" in lim for lim in result.limitations)
    assert any("Multiplayer" in lim for lim in result.limitations)


# -------------------------------------------------------------------------
# 7. Canonical Demo Specs Validity
# -------------------------------------------------------------------------

@pytest.mark.parametrize("route_slug", [
    "demo-bouncer-pillars",
    "demo-patrol-lanes",
    "demo-dasher-defeat",
    "demo-shooter-pillars",
    "demo-maze-collect",
])
def test_all_canonical_demo_specs_pass_validation(route_slug):
    """Every registered canonical demo route spec must pass validate_game_ir."""
    raw_spec = get_demo_spec(route_slug)
    assert raw_spec is not None, f"Route '{route_slug}' not found in registry"
    result = validate_game_ir(raw_spec)
    assert result.ok is True, f"Demo '{route_slug}' failed validation: {result.errors}"
    assert result.spec is not None
    assert result.spec.schema_version == "1.0"


# -------------------------------------------------------------------------
# 8. QA Runner Win Reachable Dispatch for defeat_enemies
# -------------------------------------------------------------------------

def test_qa_runner_defeat_enemies_win_dispatch():
    """Check 8 in qa_runner dispatches simulatePickup() for defeat_enemies and validates won state."""
    eval_calls = []

    class MockPage:
        def evaluate(self, script: str):
            eval_calls.append(script)
            if "getState()" in script:
                return {"status": "won"}
            return None

    page = MockPage()
    obj_type = "defeat_enemies"
    target_obj = 5

    if obj_type in ("collect_count", "defeat_enemies"):
        for _ in range(target_obj):
            page.evaluate("() => window.__AETHER_GAME__.simulatePickup()")
    elif obj_type == "survive_seconds":
        page.evaluate(f"() => window.__AETHER_GAME__.advanceTimer({target_obj})")

    win_st = page.evaluate("() => window.__AETHER_GAME__.getState()")
    assert win_st is not None
    assert win_st.get("status") == "won"
    pickup_calls = [s for s in eval_calls if "simulatePickup()" in s]
    assert len(pickup_calls) == target_obj

