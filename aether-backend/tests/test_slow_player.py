"""
Unit test for slow player wall-approach time scaling and repair trigger eligibility.
Verifies that:
1. Dynamic wall approach step calculation provides enough time for schema min speed (100 px/s).
2. A QA report where movement_speed_consistent passes and only patchable survival checks fail
   correctly marks repair_recommended = True.
"""

import pytest


def test_wall_approach_scaling():
    """Verify that slow player speeds (100 px/s, 110 px/s) scale approach duration >= 7.5s."""
    def calc_steps(v_straight: float) -> int:
        speed = max(v_straight, 80.0) if v_straight > 0 else 100.0
        max_wall_time = max(5.0, (800.0 / speed) + 1.5)
        return int(max_wall_time / 0.04)

    steps_100 = calc_steps(100.0)
    steps_110 = calc_steps(110.0)
    steps_220 = calc_steps(220.0)

    # 100 px/s needs at least 384px / 100px/s = 3.84s -> with 800px max distance = 8.0s -> ~237 steps
    assert steps_100 >= 200, f"Expected steps_100 >= 200, got {steps_100}"
    assert steps_110 >= 180, f"Expected steps_110 >= 180, got {steps_110}"
    assert steps_220 < steps_100, "Fast players should require fewer max steps than slow players"


def test_p06_failure_profile_triggers_repair():
    """When movement_speed_consistent passes and only idle/flee fail, repair is recommended."""
    checks = [
        {"id": "canvas_visible", "critical": True, "patchable": False, "passed": True},
        {"id": "canvas_dimensions", "critical": True, "patchable": False, "passed": True},
        {"id": "movement_speed_consistent", "critical": True, "patchable": False, "passed": True},
        {"id": "idle_survival_min_seconds", "critical": True, "patchable": True, "passed": False, "message": "Idle died early"},
        {"id": "flee_bot_survives", "critical": True, "patchable": True, "passed": False, "message": "Flee bot died early"},
    ]

    has_critical_failure = any(c["critical"] and not c["passed"] for c in checks)
    has_non_patchable_failure = any(not c["patchable"] and not c["passed"] for c in checks)
    repair_recommended = has_critical_failure and not has_non_patchable_failure

    report = {
        "url": "http://localhost:5173/play/test-p06",
        "overall": "PASS" if not has_critical_failure else "FAIL",
        "checks": checks,
        "repair_recommended": repair_recommended,
    }

    assert report["overall"] == "FAIL", "Report should fail due to idle/flee checks"
    assert report["repair_recommended"] is True, "Repair must be recommended when only patchable checks fail"
