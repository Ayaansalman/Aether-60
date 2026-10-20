"""
Playwright Synchronous Browser QA Test Runner.
Executes automated smoke tests and quality checks against the Phaser game runtime.
Conforms to Sections 7.1, 7.3, and 9.1 of the 60% Capstone Engineering Specification.

Check families (every check carries `critical` and `patchable` flags):
- Runtime checks (patchable=False): canvas, hook, movement, restart, etc. A parameter patch
  cannot fix a runtime bug, so a failure here means "needs developer".
- Spec-level playability checks (patchable=True): `idle_survival_min_seconds` and
  `flee_bot_survives`. These fail when the GameIR parameters make the game unplayable,
  which the bounded repair loop CAN fix with a parameter patch.
"""

import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from playwright.sync_api import Page, sync_playwright

# ---------------------------------------------------------------------------
# Spec-level playability thresholds, tuned against the four demo samples and
# sample-too-hard.json (measured values are recorded in docs/PROGRESS.md).
# Measured idle survival (no input): demo 4.80s, demo-melee 4.80s, demo-avoid 4.81s,
# demo-survive 3.69s, demo-too-hard 0.25s. 3.0s keeps >0.6s margin under the weakest demo.
# ---------------------------------------------------------------------------
IDLE_MIN_SECONDS = 3.0          # idle player (no input) must survive at least this long
IDLE_MAX_WAIT_SECONDS = 15.0    # upper bound of the observation window
FLEE_MAX_SECONDS = 12.0         # flee bot must survive min(this, objective target seconds)
ARENA_W, ARENA_H = 800.0, 600.0
# Flee-bot planning model (assumed constants, not read from the spec): look-ahead horizon and speeds
FLEE_HORIZON_S = 0.6
FLEE_ASSUMED_PLAYER_SPEED = 210.0
FLEE_ASSUMED_ENEMY_SPEED = 110.0


def _measure_full_idle_window() -> bool:
    """AETHER_QA_IDLE_FULL=1 observes the whole idle window (used to report real numbers)."""
    return os.getenv("AETHER_QA_IDLE_FULL", "").strip() == "1"


def _neutralize_enemies(page: Page) -> None:
    """
    Pauses enemies (no movement, no damage) through the QA hook. The runtime checks (movement,
    attack, win/lose, restart...) must not be affected by how lethal the *spec* is; otherwise a
    too-hard spec would make a runtime check fail and be misclassified as a non-patchable bug.
    """
    try:
        page.evaluate("() => window.__AETHER_GAME__ && window.__AETHER_GAME__.pauseEnemies(true)")
    except Exception:
        pass


def _ensure_test_param(url: str) -> str:
    """Ensures ?test=1 is appended to activate window.__AETHER_GAME__."""
    if "test=1" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}test=1"


def _slugify_url(url: str) -> str:
    """Generates a filesystem-friendly name from a URL."""
    parsed = urlparse(url)
    slug = parsed.path.strip("/").replace("/", "_") or "index"
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", slug)


def _get_game_time_seconds(page: Page) -> float:
    """Returns elapsed game time in seconds from the hook, falling back to tick/60."""
    try:
        val = page.evaluate("""() => {
            if (window.__AETHER_GAME__ && typeof window.__AETHER_GAME__.gameTimeMs === 'number' && window.__AETHER_GAME__.gameTimeMs > 0) {
                return window.__AETHER_GAME__.gameTimeMs / 1000.0;
            }
            if (window.__AETHER_GAME__ && typeof window.__AETHER_GAME__.tick === 'number') {
                return window.__AETHER_GAME__.tick / 60.0;
            }
            return null;
        }""")
        if val is not None:
            return float(val)
    except Exception:
        pass
    return time.monotonic()


def _reset_round(page: Page) -> None:
    """Restarts the scene cleanly, preserves enemiesPaused, and ensures playing state."""
    page.focus("canvas")
    _neutralize_enemies(page)
    page.keyboard.press("r")
    time.sleep(0.2)
    for _ in range(40):
        try:
            ready = page.evaluate("""() => {
                if (!window.__AETHER_GAME__ || !window.__AETHER_GAME__.ready) return false;
                const st = window.__AETHER_GAME__.getState();
                return st && st.status === 'playing';
            }""")
            if ready:
                break
        except Exception:
            pass
        time.sleep(0.03)

    _neutralize_enemies(page)
    try:
        t_start = page.evaluate("() => window.__AETHER_GAME__.tick")
        for _ in range(25):
            t_curr = page.evaluate("() => window.__AETHER_GAME__.tick")
            if t_curr >= t_start + 3:
                break
            time.sleep(0.02)
    except Exception:
        pass
    _neutralize_enemies(page)


def _sample_motion(page: Page, keys: List[str], min_game_duration: float = 0.35) -> Tuple[float, float, float]:
    """
    Measures speed in continuous motion by waiting for velocity to establish,
    sampling start coordinate and gameTimeMs, waiting for min_game_duration of
    game time while keys remain held down, then sampling end coordinate.
    Returns (distance, elapsed_game_time_seconds, speed_px_per_sec).
    """
    sample = lambda: page.evaluate("""() => {
        const p = window.__AETHER_GAME__ ? window.__AETHER_GAME__.getState().player : { x: 0, y: 0 };
        return {
            x: p.x,
            y: p.y,
            t: (window.__AETHER_GAME__ && typeof window.__AETHER_GAME__.gameTimeMs === 'number' && window.__AETHER_GAME__.gameTimeMs > 0)
                ? (window.__AETHER_GAME__.gameTimeMs / 1000.0)
                : ((window.__AETHER_GAME__ && window.__AETHER_GAME__.tick) ? window.__AETHER_GAME__.tick / 60.0 : 0.0),
        };
    }""")

    # 1. Press keys
    for k in keys:
        page.keyboard.down(k)

    # 2. Wait until motion has begun (at least 3px from initial)
    s_init = sample()
    t_wall_start = time.time()
    while time.time() - t_wall_start < 1.0:
        s_now = sample()
        if math.hypot(s_now["x"] - s_init["x"], s_now["y"] - s_init["y"]) >= 3.0:
            break
        time.sleep(0.01)

    # 3. Take s0 during confirmed steady motion
    s0 = sample()

    # 4. Wait for min_game_duration of game time while keys stay down
    while True:
        s1 = sample()
        if (s1["t"] - s0["t"]) >= min_game_duration:
            break
        if time.time() - t_wall_start > 3.0:
            break
        time.sleep(0.01)

    # 5. Release keys
    for k in keys:
        page.keyboard.up(k)
    time.sleep(0.05)

    dist = math.hypot(s1["x"] - s0["x"], s1["y"] - s0["y"])
    dt = s1["t"] - s0["t"]
    speed = dist / dt if dt > 0 else 0.0
    return dist, dt, speed


def run_movement_checks(page: Page) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Measures straight speed, diagonal speed, and wall-sliding speeds along all 4 arena walls.
    Calculates speed as distance divided by elapsed game time from the hook, moving in a
    direction with free space. Asserts diagonal and wall-sliding speeds are within 15%
    of straight speed.
    """
    page.focus("canvas")
    _neutralize_enemies(page)
    details: Dict[str, Any] = {}

    # 1. Measure straight speed in a direction with free space
    _reset_round(page)
    p_cur = page.evaluate("() => window.__AETHER_GAME__.getState().player")
    cur_x = p_cur.get("x", 400) if p_cur else 400
    straight_key = "ArrowRight" if (784 - cur_x) >= (cur_x - 16) else "ArrowLeft"

    d_straight, dt_straight, v_straight = _sample_motion(page, [straight_key])
    if dt_straight <= 0 or d_straight <= 10.0:
        return False, f"Straight movement too small or invalid: {d_straight:.2f}px in {dt_straight:.3f}s", details

    details["d_straight"] = round(d_straight, 2)
    details["dt_straight"] = round(dt_straight, 3)
    details["v_straight"] = round(v_straight, 2)

    # 2. Diagonal movement in quadrant with free space
    _reset_round(page)
    p_cur = page.evaluate("() => window.__AETHER_GAME__.getState().player")
    cur_x = p_cur.get("x", 400) if p_cur else 400
    cur_y = p_cur.get("y", 300) if p_cur else 300
    diag_kx = "ArrowRight" if (784 - cur_x) >= (cur_x - 16) else "ArrowLeft"
    diag_ky = "ArrowDown" if (584 - cur_y) >= (cur_y - 16) else "ArrowUp"

    d_diag, dt_diag, v_diag = _sample_motion(page, [diag_kx, diag_ky])
    diag_diff_pct = abs(v_diag - v_straight) / v_straight if v_straight > 0 else 0.0

    details["d_diagonal"] = round(d_diag, 2)
    details["dt_diagonal"] = round(dt_diag, 3)
    details["v_diagonal"] = round(v_diag, 2)
    details["diag_diff_pct"] = round(diag_diff_pct * 100, 1)
    details["diag_pass"] = diag_diff_pct <= 0.15

    if diag_diff_pct > 0.15:
        return (
            False,
            f"Diagonal speed {v_diag:.2f}px/s differs by {diag_diff_pct*100:.1f}% from straight {v_straight:.2f}px/s (>15%)",
            details,
        )

    # 3. Test each of the four walls
    def test_wall(toward_key: str, along_key: str, axis: str) -> Tuple[bool, float, float, float]:
        _reset_round(page)
        # Determine approach wait time dynamically based on player speed (schema min 100 px/s)
        # Max travel across arena is 800px. Allow travel time + margin, sampled every 40ms.
        speed = max(v_straight, 80.0) if v_straight > 0 else 100.0
        max_wall_time = max(5.0, (800.0 / speed) + 1.5)
        max_wall_steps = int(max_wall_time / 0.04)

        page.keyboard.down(toward_key)
        prev_coord = -999.0
        steady_count = 0
        for _ in range(max_wall_steps):
            time.sleep(0.04)
            curr = page.evaluate("() => window.__AETHER_GAME__.getState().player")
            if not curr:
                continue
            px = curr.get("x", 400)
            py = curr.get("y", 300)
            # Exit early as soon as player's position is within 22px of the target wall
            if toward_key == "ArrowRight" and (px >= (800 - 16 - 22) or px >= (800 - 22)):
                break
            elif toward_key == "ArrowLeft" and (px <= (16 + 22) or px <= 22):
                break
            elif toward_key == "ArrowDown" and (py >= (600 - 16 - 22) or py >= (600 - 22)):
                break
            elif toward_key == "ArrowUp" and (py <= (16 + 22) or py <= 22):
                break

            coord = px if toward_key in ("ArrowRight", "ArrowLeft") else py
            if abs(coord - prev_coord) < 0.5:
                steady_count += 1
                if steady_count >= 3:
                    break
            else:
                steady_count = 0
            prev_coord = coord

        sample = lambda: page.evaluate("""() => {
            const p = window.__AETHER_GAME__ ? window.__AETHER_GAME__.getState().player : { x: 0, y: 0 };
            return {
                x: p.x,
                y: p.y,
                t: (window.__AETHER_GAME__ && typeof window.__AETHER_GAME__.gameTimeMs === 'number' && window.__AETHER_GAME__.gameTimeMs > 0)
                    ? (window.__AETHER_GAME__.gameTimeMs / 1000.0)
                    : ((window.__AETHER_GAME__ && window.__AETHER_GAME__.tick) ? window.__AETHER_GAME__.tick / 60.0 : 0.0),
            };
        }""")

        page.keyboard.down(along_key)
        s_init = sample()
        t_w_start = time.time()
        while time.time() - t_w_start < 1.0:
            s_now = sample()
            if abs(s_now[axis] - s_init[axis]) >= 3.0:
                break
            time.sleep(0.01)

        s0 = sample()
        while True:
            s1 = sample()
            if (s1["t"] - s0["t"]) >= 0.35:
                break
            if time.time() - t_w_start > 3.0:
                break
            time.sleep(0.01)

        page.keyboard.up(along_key)
        page.keyboard.up(toward_key)
        time.sleep(0.05)

        d_along = abs(s1[axis] - s0[axis])
        dt_along = s1["t"] - s0["t"]
        v_along = d_along / dt_along if dt_along > 0 else 0.0
        diff_pct = abs(v_along - v_straight) / v_straight if v_straight > 0 else 0.0
        return (diff_pct <= 0.15), d_along, v_along, diff_pct

    walls = [
        ("right_wall", "ArrowRight", "ArrowDown", "y"),
        ("left_wall", "ArrowLeft", "ArrowDown", "y"),
        ("bottom_wall", "ArrowDown", "ArrowRight", "x"),
        ("top_wall", "ArrowUp", "ArrowRight", "x"),
    ]

    for name, toward, along, axis in walls:
        passed, d_along, v_along, diff_pct = test_wall(toward, along, axis)
        details[name] = {
            "d_along": round(d_along, 2),
            "v_along": round(v_along, 2),
            "diff_pct": round(diff_pct * 100, 1),
            "passed": passed,
        }
        if not passed:
            return (
                False,
                f"Wall sliding failed on {name}: {v_along:.2f}px/s ({diff_pct*100:.1f}% vs {v_straight:.2f}px/s)",
                details,
            )

    # Return player to center position
    _reset_round(page)
    return True, "", details


def _game_state(page: Page) -> Dict[str, Any]:
    return page.evaluate("() => window.__AETHER_GAME__.getState()")


def run_idle_survival_check(
    page: Page,
    min_seconds: float = IDLE_MIN_SECONDS,
    max_wait: float = IDLE_MAX_WAIT_SECONDS,
    measure_full: bool = False,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Restarts the round cleanly, unpauses enemies, and gives NO keyboard input while enemies chase.
    The player must still be alive after `min_seconds`. Observation window is at most `max_wait`
    seconds (the loop exits early once the threshold is met unless `measure_full` is set).
    """
    _reset_round(page)
    st0 = _game_state(page)

    if not st0 or st0.get("status") != "playing":
        return False, f"Round not in 'playing' state after restart: {st0.get('status') if st0 else 'none'}", {}

    start = time.monotonic()
    page.evaluate("() => window.__AETHER_GAME__.pauseEnemies(false)")
    died_at: Optional[float] = None
    last = st0
    elapsed = 0.0
    while True:
        elapsed = time.monotonic() - start
        last = _game_state(page)
        if last.get("status") == "lost":
            died_at = elapsed
            break
        if last.get("status") == "won":
            break
        if elapsed >= max_wait:
            break
        if not measure_full and elapsed >= min_seconds:
            break
        time.sleep(0.05)

    _neutralize_enemies(page)
    survived = died_at if died_at is not None else elapsed
    details: Dict[str, Any] = {
        "survived_seconds": round(survived, 2),
        "died": died_at is not None,
        "min_required_seconds": min_seconds,
        "window_seconds": max_wait,
        "hp_start": st0.get("hp"),
        "hp_end": last.get("hp"),
        "enemy_count": st0.get("enemyCount"),
    }
    if died_at is not None and died_at < min_seconds:
        return (
            False,
            f"Idle player died after {died_at:.2f}s (< {min_seconds:.1f}s required) with no input; "
            f"enemies={st0.get('enemyCount')}, max_hp={st0.get('maxHp')}",
            details,
        )
    return True, "", details


def _flee_vector(player: Dict[str, Any], enemies: List[Dict[str, Any]]) -> Tuple[float, float, float]:
    """
    Returns (vx, vy, nearest_distance): a unit steering direction chosen by a small look-ahead
    planner. For 16 candidate headings it predicts where the player would be after a short
    horizon (clamped inside the arena, so walls and corners are penalised automatically) and
    where every enemy would be if it chased that spot, then picks the heading that keeps the
    largest distance to the closest enemy. Ties lean toward the arena centre.
    """
    px, py = float(player["x"]), float(player["y"])
    nearest = min(
        (math.hypot(px - float(e["x"]), py - float(e["y"])) for e in enemies),
        default=1e9,
    )
    if not enemies:
        return 0.0, 0.0, nearest

    best_score = -1e18
    best_dir = (0.0, 0.0)
    for i in range(16):
        ang = (2.0 * math.pi * i) / 16.0
        dx, dy = math.cos(ang), math.sin(ang)
        fx = min(ARENA_W - 20.0, max(20.0, px + dx * FLEE_ASSUMED_PLAYER_SPEED * FLEE_HORIZON_S))
        fy = min(ARENA_H - 20.0, max(20.0, py + dy * FLEE_ASSUMED_PLAYER_SPEED * FLEE_HORIZON_S))
        worst = 1e18
        for e in enemies:
            ex, ey = float(e["x"]), float(e["y"])
            d = math.hypot(fx - ex, fy - ey)
            step = min(d, FLEE_ASSUMED_ENEMY_SPEED * FLEE_HORIZON_S)
            if d > 1e-6:
                ex += (fx - ex) / d * step
                ey += (fy - ey) / d * step
            worst = min(worst, math.hypot(fx - ex, fy - ey))
        centre_pull = math.hypot(fx - ARENA_W / 2.0, fy - ARENA_H / 2.0)
        score = worst - 0.05 * centre_pull
        if score > best_score:
            best_score = score
            best_dir = (dx, dy)
    return best_dir[0], best_dir[1], nearest


def run_flee_bot_check(
    page: Page,
    required_seconds: float,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    A simple bot uses real keyboard input and the hook's getEnemyPositions()/getState().player
    to steer away from the nearest enemies (toward the arena centre near walls). It must stay
    alive for `required_seconds`.
    """
    _reset_round(page)
    st0 = _game_state(page)

    if not st0 or st0.get("status") != "playing":
        return False, f"Round not in 'playing' state after restart: {st0.get('status') if st0 else 'none'}", {}

    held: Set[str] = set()

    def apply_keys(wanted: Set[str]) -> None:
        for k in list(held - wanted):
            page.keyboard.up(k)
            held.discard(k)
        for k in wanted - held:
            page.keyboard.down(k)
            held.add(k)

    start = time.monotonic()
    page.evaluate("() => window.__AETHER_GAME__.pauseEnemies(false)")
    died_at: Optional[float] = None
    min_nearest = 1e9
    last = st0
    elapsed = 0.0
    try:
        while True:
            elapsed = time.monotonic() - start
            last = _game_state(page)
            if last.get("status") == "lost":
                died_at = elapsed
                break
            if last.get("status") == "won" or elapsed >= required_seconds:
                break
            enemies = page.evaluate("() => window.__AETHER_GAME__.getEnemyPositions()")
            vx, vy, nearest = _flee_vector(last["player"], enemies)
            min_nearest = min(min_nearest, nearest)
            mag = math.hypot(vx, vy)
            wanted: Set[str] = set()
            if mag > 1e-6:
                nx, ny = vx / mag, vy / mag
                if nx > 0.45:
                    wanted.add("ArrowRight")
                elif nx < -0.45:
                    wanted.add("ArrowLeft")
                if ny > 0.45:
                    wanted.add("ArrowDown")
                elif ny < -0.45:
                    wanted.add("ArrowUp")
            apply_keys(wanted)
            time.sleep(0.03)
    finally:
        apply_keys(set())

    survived = died_at if died_at is not None else elapsed
    details: Dict[str, Any] = {
        "survived_seconds": round(survived, 2),
        "required_seconds": round(required_seconds, 2),
        "died": died_at is not None,
        "hp_start": st0.get("hp"),
        "hp_end": last.get("hp"),
        "enemy_count": st0.get("enemyCount"),
        "min_enemy_distance_px": round(min_nearest, 1) if min_nearest < 1e9 else None,
    }
    if died_at is not None:
        return (
            False,
            f"Flee bot died after {died_at:.2f}s (needed {required_seconds:.1f}s); "
            f"enemies={st0.get('enemyCount')}, max_hp={st0.get('maxHp')}",
            details,
        )
    return True, "", details


def run_qa(url: str, out_dir: str = "artifacts/qa") -> Dict[str, Any]:
    """
    Launches headless Chromium using Playwright Sync API, runs 13 critical checks
    plus a screenshot check, and returns a structured QA report dict.
    """
    target_url = _ensure_test_param(url)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    slug = _slugify_url(url)
    screenshot_file = out_path / f"{slug}.png"

    checks: List[Dict[str, Any]] = []
    page_errors: List[str] = []
    screenshot_path: str = ""

    def record_check(
        check_id: str,
        passed: bool,
        message: str = "",
        patchable: bool = False,
        measured: Optional[Dict[str, Any]] = None,
    ):
        entry: Dict[str, Any] = {
            "id": check_id,
            "critical": True,
            "patchable": patchable,
            "passed": passed,
            "message": message
        }
        if measured:
            entry["measured"] = measured
        checks.append(entry)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Capture page errors and console errors
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("console", lambda msg: page_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)

        try:
            # Navigate to the page
            page.goto(target_url, wait_until="networkidle", timeout=15000)

            try:
                page.wait_for_selector("canvas", timeout=7000)
                is_vis = False
                for _ in range(30):
                    is_vis = page.evaluate("""() => {
                        const c = document.querySelector('canvas');
                        if (!c) return false;
                        const rect = c.getBoundingClientRect();
                        return (rect.width > 0 && rect.height > 0) || (c.clientWidth > 0 && c.clientHeight > 0) || (c.width > 0 && c.height > 0);
                    }""")
                    if is_vis:
                        break
                    time.sleep(0.04)

                if is_vis:
                    record_check("canvas_visible", True)
                else:
                    record_check("canvas_visible", False, "Canvas found but has zero width or height")
            except Exception as e:
                record_check("canvas_visible", False, f"Canvas element not visible: {e}")

            # ---------------------------------------------------------
            # Check 2: hook_ready (window.__AETHER_GAME__.ready & tick progression)
            # ---------------------------------------------------------
            try:
                page.wait_for_function("() => window.__AETHER_GAME__ && window.__AETHER_GAME__.ready === true", timeout=7000)
                _neutralize_enemies(page)
                tick1 = page.evaluate("() => window.__AETHER_GAME__.tick")
                time.sleep(1.0)
                tick2 = page.evaluate("() => window.__AETHER_GAME__.tick")
                if tick2 > tick1:
                    record_check("hook_ready", True)
                else:
                    record_check("hook_ready", False, f"Simulation tick stalled: tick1={tick1}, tick2={tick2}")
            except Exception as e:
                record_check("hook_ready", False, f"QA hook failed readiness check: {e}")

            # ---------------------------------------------------------
            # Check 3: no_page_errors
            # ---------------------------------------------------------
            try:
                if len(page_errors) == 0:
                    record_check("no_page_errors", True)
                else:
                    record_check("no_page_errors", False, f"Page logged {len(page_errors)} error(s): {page_errors[0]}")
            except Exception as e:
                record_check("no_page_errors", False, str(e))

            # Read initial baseline state
            initial_state = page.evaluate("() => window.__AETHER_GAME__.getState()")
            initial_enemies = initial_state.get("enemyCount", 0)
            initial_collectibles = initial_state.get("collectibleCount", 0)
            initial_projectiles = initial_state.get("projectileCount", 0)
            max_hp = initial_state.get("maxHp", 3)
            target_obj = initial_state.get("target", 8)
            obj_type = initial_state.get("objectiveType", "collect_count")
            attack_mode = initial_state.get("attackMode", "avoid_only")

            # ---------------------------------------------------------
            # Check 4: player_present
            # ---------------------------------------------------------
            try:
                player = initial_state.get("player")
                if player and 0 < player.get("x", 0) < 800 and 0 < player.get("y", 0) < 600:
                    record_check("player_present", True)
                else:
                    record_check("player_present", False, f"Player coordinates invalid: {player}")
            except Exception as e:
                record_check("player_present", False, f"Player entity missing: {e}")

            # ---------------------------------------------------------
            # Check 5: player_moves (hold 'd' for 600ms, displacement > 5px)
            # ---------------------------------------------------------
            try:
                page.focus("canvas")
                p0 = page.evaluate("() => window.__AETHER_GAME__.getState().player")
                page.keyboard.down("d")
                time.sleep(0.6)
                page.keyboard.up("d")
                p1 = page.evaluate("() => window.__AETHER_GAME__.getState().player")
                dist = math.hypot(p1["x"] - p0["x"], p1["y"] - p0["y"])
                if dist > 5.0:
                    record_check("player_moves", True)
                else:
                    record_check("player_moves", False, f"Player movement insufficient: displacement={dist:.2f}px")
            except Exception as e:
                record_check("player_moves", False, f"Player movement test failed: {e}")

            # ---------------------------------------------------------
            # Check 6: movement_speed_consistent
            # ---------------------------------------------------------
            try:
                m_pass, m_msg, m_det = run_movement_checks(page)
                if m_pass:
                    record_check("movement_speed_consistent", True, measured=m_det)
                else:
                    record_check("movement_speed_consistent", False, m_msg, measured=m_det)
            except Exception as e:
                record_check("movement_speed_consistent", False, f"Movement consistency test failed: {e}")

            # ---------------------------------------------------------
            # Check 7: attack_responds
            # ---------------------------------------------------------
            try:
                page.click("canvas")
                atk0 = page.evaluate("() => window.__AETHER_GAME__.getState().attacksPerformed")
                page.keyboard.down("Space")
                time.sleep(0.08)
                page.keyboard.up("Space")
                time.sleep(0.2)
                atk1 = page.evaluate("() => window.__AETHER_GAME__.getState().attacksPerformed")

                if attack_mode in ("projectile", "melee"):
                    if atk1 > atk0:
                        record_check("attack_responds", True)
                    else:
                        record_check("attack_responds", False, f"Attack did not trigger for {attack_mode}: atk0={atk0}, atk1={atk1}")
                elif attack_mode == "avoid_only":
                    if atk1 == atk0:
                        record_check("attack_responds", True)
                    else:
                        record_check("attack_responds", False, f"Attack triggered unexpectedly in avoid_only mode: atk0={atk0}, atk1={atk1}")
                else:
                    record_check("attack_responds", False, f"Unrecognized attackMode: {attack_mode}")
            except Exception as e:
                record_check("attack_responds", False, f"Attack check failed: {e}")

            # ---------------------------------------------------------
            # Check 7: hud_consistent
            # ---------------------------------------------------------
            try:
                st = page.evaluate("() => window.__AETHER_GAME__.getState()")
                hud = st.get("hud", {})
                h_text = hud.get("health", "")
                o_text = hud.get("objective", "")

                has_hp = str(st["hp"]) in h_text and str(st["maxHp"]) in h_text
                has_obj = str(target_obj) in o_text or ("Time" in o_text and obj_type == "survive_seconds")

                if has_hp and has_obj:
                    record_check("hud_consistent", True)
                else:
                    record_check("hud_consistent", False, f"HUD inconsistent: health='{h_text}', objective='{o_text}'")
            except Exception as e:
                record_check("hud_consistent", False, f"HUD consistency check failed: {e}")

            # ---------------------------------------------------------
            # Check 8: win_reachable
            # ---------------------------------------------------------
            try:
                if obj_type in ("collect_count", "defeat_enemies"):
                    for _ in range(target_obj):
                        page.evaluate("() => window.__AETHER_GAME__.simulatePickup()")
                elif obj_type == "survive_seconds":
                    page.evaluate(f"() => window.__AETHER_GAME__.advanceTimer({target_obj})")

                win_st = page.evaluate("() => window.__AETHER_GAME__.getState()")
                if win_st.get("status") == "won":
                    record_check("win_reachable", True)
                else:
                    record_check("win_reachable", False, f"Expected status 'won', got '{win_st.get('status')}'")
            except Exception as e:
                record_check("win_reachable", False, f"Win condition check failed: {e}")

            # ---------------------------------------------------------
            # Check 9: no_actions_after_end (while in 'won' state)
            # ---------------------------------------------------------
            try:
                atk_before = page.evaluate("() => window.__AETHER_GAME__.getState().attacksPerformed")
                page.keyboard.press("Space")
                time.sleep(0.1)
                atk_after = page.evaluate("() => window.__AETHER_GAME__.getState().attacksPerformed")
                if atk_before == atk_after:
                    record_check("no_actions_after_end", True)
                else:
                    record_check("no_actions_after_end", False, f"Action executed after game end: atk_before={atk_before}, atk_after={atk_after}")
            except Exception as e:
                record_check("no_actions_after_end", False, f"End-state action lock failed: {e}")

            # ---------------------------------------------------------
            # Check 10: restart_resets_after_win
            # ---------------------------------------------------------
            try:
                page.keyboard.press("r")
                time.sleep(0.3)
                r_st = page.evaluate("() => window.__AETHER_GAME__.getState()")
                _neutralize_enemies(page)
                ok = (
                    r_st.get("status") == "playing"
                    and r_st.get("hp") == max_hp
                    and r_st.get("score") == 0
                    and r_st.get("enemyCount") == initial_enemies
                    and r_st.get("collectibleCount") == initial_collectibles
                    and r_st.get("projectileCount") == initial_projectiles
                )
                if ok:
                    record_check("restart_resets_after_win", True)
                else:
                    record_check(
                        "restart_resets_after_win",
                        False,
                        f"State not restored after win restart: status={r_st.get('status')}, hp={r_st.get('hp')}, score={r_st.get('score')}, enemies={r_st.get('enemyCount')}"
                    )
            except Exception as e:
                record_check("restart_resets_after_win", False, f"Restart after win failed: {e}")

            # ---------------------------------------------------------
            # Check 11: lose_reachable
            # ---------------------------------------------------------
            try:
                page.evaluate(f"() => window.__AETHER_GAME__.damagePlayer({max_hp})")
                lost_st = page.evaluate("() => window.__AETHER_GAME__.getState()")
                if lost_st.get("status") == "lost":
                    record_check("lose_reachable", True)
                else:
                    record_check("lose_reachable", False, f"Expected status 'lost', got '{lost_st.get('status')}'")
            except Exception as e:
                record_check("lose_reachable", False, f"Lose condition check failed: {e}")

            # ---------------------------------------------------------
            # Check 12: restart_resets_after_lose
            # ---------------------------------------------------------
            try:
                page.keyboard.press("r")
                time.sleep(0.3)
                r_lost_st = page.evaluate("() => window.__AETHER_GAME__.getState()")
                _neutralize_enemies(page)
                ok = (
                    r_lost_st.get("status") == "playing"
                    and r_lost_st.get("hp") == max_hp
                    and r_lost_st.get("score") == 0
                    and r_lost_st.get("enemyCount") == initial_enemies
                )
                if ok:
                    record_check("restart_resets_after_lose", True)
                else:
                    record_check(
                        "restart_resets_after_lose",
                        False,
                        f"State not restored after lose restart: status={r_lost_st.get('status')}, hp={r_lost_st.get('hp')}, enemies={r_lost_st.get('enemyCount')}"
                    )
            except Exception as e:
                record_check("restart_resets_after_lose", False, f"Restart after lose failed: {e}")

            # ---------------------------------------------------------
            # Check 13: no_duplicate_enemies_after_restart
            # ---------------------------------------------------------
            try:
                # Attack an enemy, immediately restart with 'R', wait 4 seconds (longer than 3s respawn)
                if attack_mode != "avoid_only":
                    page.keyboard.press("Space")
                    time.sleep(0.4)
                page.keyboard.press("r")
                time.sleep(0.25)
                _neutralize_enemies(page)
                time.sleep(3.75)

                final_st = page.evaluate("() => window.__AETHER_GAME__.getState()")
                final_enemies = final_st.get("enemyCount", 0)
                if final_enemies == initial_enemies:
                    record_check("no_duplicate_enemies_after_restart", True)
                else:
                    record_check(
                        "no_duplicate_enemies_after_restart",
                        False,
                        f"Zombie enemy respawn leak detected: expected {initial_enemies}, got {final_enemies}"
                    )
            except Exception as e:
                record_check("no_duplicate_enemies_after_restart", False, f"Duplicate enemy test failed: {e}")

            # ---------------------------------------------------------
            # Check 14: Screenshot saving
            # ---------------------------------------------------------
            try:
                page.screenshot(path=str(screenshot_file), full_page=False)
                if screenshot_file.exists() and screenshot_file.stat().st_size > 0:
                    screenshot_path = str(screenshot_file.resolve())
                    record_check("screenshot_captured", True)
                else:
                    record_check("screenshot_captured", False, "Screenshot file empty or missing")
            except Exception as e:
                record_check("screenshot_captured", False, f"Screenshot failed: {e}")

            # ---------------------------------------------------------
            # Check 15: idle_survival_min_seconds (spec-level, patchable)
            # ---------------------------------------------------------
            try:
                i_pass, i_msg, i_det = run_idle_survival_check(
                    page, measure_full=_measure_full_idle_window()
                )
                record_check("idle_survival_min_seconds", i_pass, i_msg, patchable=True, measured=i_det)
            except Exception as e:
                record_check("idle_survival_min_seconds", False, f"Idle survival check crashed: {e}")

            # ---------------------------------------------------------
            # Check 16: flee_bot_survives (spec-level, patchable)
            # ---------------------------------------------------------
            try:
                required = FLEE_MAX_SECONDS
                if obj_type == "survive_seconds":
                    required = min(FLEE_MAX_SECONDS, float(target_obj))
                f_pass, f_msg, f_det = run_flee_bot_check(page, required)
                record_check("flee_bot_survives", f_pass, f_msg, patchable=True, measured=f_det)
            except Exception as e:
                record_check("flee_bot_survives", False, f"Flee bot check crashed: {e}")

        finally:
            context.close()
            browser.close()

    overall_pass = all(c["passed"] for c in checks)

    return {
        "url": url,
        "overall": "PASS" if overall_pass else "FAIL",
        "checks": checks,
        "page_errors": page_errors,
        "screenshot_path": screenshot_path,
        "repair_recommended": not overall_pass
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m services.qa_runner <url> [out_dir]")
        sys.exit(1)

    target_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "artifacts/qa"

    report = run_qa(target_url, output_dir)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["overall"] == "PASS" else 1)
