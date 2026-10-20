# AETHER Browser QA Verification Suite (17 Spec-Level Checks)

This document provides the complete reference for all **17 automated QA smoke checks** executed by Playwright against the Phaser 3 client runtime (`services/qa_runner.py`).

---

## 1. Master QA Checks Summary Table

| # | Check Identifier (`id`) | Category | Description | Critical | Patchable |
|---|---|---|---|---|---|
| 1 | `canvas_visible` | Runtime / Engine | HTML `<canvas>` element exists, is visible, and has non-zero bounding dimensions. | **Yes** | **No** |
| 2 | `hook_ready` | Runtime / Engine | `window.__AETHER_GAME__.ready === true` and simulation `tick` increments steadily over 1.0s. | **Yes** | **No** |
| 3 | `no_page_errors` | Runtime / Engine | Page logged zero uncaught JavaScript errors, console error logs, or unhandled exceptions. | **Yes** | **No** |
| 4 | `player_present` | Entity Sanity | Player entity exists in `getState()` with valid coordinates strictly inside the 800x600 arena. | **Yes** | **No** |
| 5 | `player_moves` | Input & Physics | Holding down `d` key for 600ms produces measurable player displacement (> 5.0px). | **Yes** | **No** |
| 6 | `movement_speed_consistent` | Input & Physics | Player straight speed, diagonal normalized speed ($v / \sqrt{2}$), and wall-slide speed match GameIR `move_speed` within $\pm 15\%$ tolerance. | **Yes** | **No** |
| 7 | `attack_responds` | Combat Mechanic | Pressing `Space` increments `attacksPerformed` for projectile/melee modes, or correctly produces no attack for avoid-only mode. | **Yes** | **No** |
| 8 | `hud_consistent` | UI & HUD | HUD strings for health and objective reflect active GameIR spec parameters. | **Yes** | **No** |
| 9 | `win_reachable` | Objective Loop | Advancing survival timer or collecting items transitions `getState().status` to `'won'`. | **Yes** | **No** |
| 10 | `no_actions_after_end` | State Machine | Space bar presses after game end (`status === 'won'`) are locked and do not trigger attacks. | **Yes** | **No** |
| 11 | `restart_resets_after_win` | State Isolation | Pressing `R` key while in `'won'` state resets HP to max, score to 0, status to `'playing'`, and clears debris. | **Yes** | **No** |
| 12 | `lose_reachable` | Damage & Loss | Applying lethal damage (`damagePlayer(maxHp)`) transitions `getState().status` to `'lost'`. | **Yes** | **No** |
| 13 | `restart_resets_after_lose` | State Isolation | Pressing `R` key while in `'lost'` state restores HP to `maxHp`, score to 0, and restores initial enemy counts. | **Yes** | **No** |
| 14 | `no_duplicate_enemies_after_restart` | Memory / Leaks | Restarting immediately after killing an enemy produces zero zombie respawn leaks after 4.0s. | **Yes** | **No** |
| 15 | `screenshot_captured` | Visual Proof | Playwright saves non-empty PNG screenshot of the active canvas to disk. | **Yes** | **No** |
| 16 | `idle_survival_min_seconds` | Spec Playability | With enemies active and no player input, player survives at least 3.0s (recommended >= 4.0s). | **Yes** | **Yes** |
| 17 | `flee_bot_survives` | Spec Playability | An automated evasion bot steering away from nearest enemies survives for `min(12.0s, objective_target)`. | **Yes** | **Yes** |

---

## 2. Detailed Check Specifications

### 2.1 `canvas_visible` (Non-Patchable)
- **Method**: Evaluates `document.querySelector('canvas').getBoundingClientRect()`.
- **Pass Rule**: Canvas width and height must both be $> 0$.
- **Why Non-Patchable**: If the canvas fails to mount, Phaser crashed or WebGL is unsupported. Parameter tuning cannot fix a broken renderer.

### 2.2 `hook_ready` (Non-Patchable)
- **Method**: Polls `window.__AETHER_GAME__.ready` until `true` (timeout 7s), samples `tick`, sleeps 1.0s, and re-samples `tick`.
- **Pass Rule**: `tick2 > tick1`.
- **Why Non-Patchable**: Indicates the Phaser simulation loop is stalled or deadlocked.

### 2.3 `no_page_errors` (Non-Patchable)
- **Method**: Listens to Playwright `pageerror` and `console` error events throughout the entire test run.
- **Pass Rule**: `page_errors` list is empty.

### 2.4 `player_present` (Non-Patchable)
- **Method**: Queries `window.__AETHER_GAME__.getState().player`.
- **Pass Rule**: `0 < player.x < 800` and `0 < player.y < 600`.

### 2.5 `player_moves` (Non-Patchable)
- **Method**: Dispatches keyboard `page.keyboard.down("d")` for 600ms, then releases.
- **Pass Rule**: $\sqrt{(x_1 - x_0)^2 + (y_1 - y_0)^2} > 5.0\text{px}$.

### 2.6 `movement_speed_consistent` (Non-Patchable)
- **Method**: Runs `run_movement_checks(page)`:
  1. Measures straight horizontal velocity (`d` key held).
  2. Measures diagonal velocity (`d` + `s` keys held simultaneously), testing vector normalization ($v / \sqrt{2}$).
  3. Measures wall-sliding velocity by steering into the right boundary. The approach duration is dynamically scaled for slow player speeds down to the schema minimum of $100\text{ px/s}$ (`max_wall_time = max(5.0, (800.0 / speed) + 1.5)`) with an early exit upon coordinate stabilization.
- **Pass Rule**: Measured straight speed, diagonal speed, and wall-slide speed must all fall within $\pm 15\%$ of GameIR `player.move_speed`.

### 2.7 `attack_responds` (Non-Patchable)
- **Method**: Dispatches `Space` key press and compares `getState().attacksPerformed` before and after.
- **Pass Rule**:
  - For `projectile` and `melee`: `atk1 > atk0`.
  - For `avoid_only`: `atk1 === atk0`.

### 2.8 `hud_consistent` (Non-Patchable)
- **Method**: Inspects text in `hud.health` and `hud.objective`.
- **Pass Rule**: Health string contains `hp` and `maxHp`; objective string contains target number or survival time.

### 2.9 `win_reachable` (Non-Patchable)
- **Method**: Calls helper `advanceTimer(target)` (for survival) or `simulatePickup()` $\times$ target (for collection).
- **Pass Rule**: `getState().status === 'won'`.

### 2.10 `no_actions_after_end` (Non-Patchable)
- **Method**: Presses `Space` while in `'won'` state.
- **Pass Rule**: `attacksPerformed` does not increment.

### 2.11 `restart_resets_after_win` (Non-Patchable)
- **Method**: Presses `r` key while in `'won'` state.
- **Pass Rule**: State restored to `'playing'`, HP restored to `maxHp`, score reset to 0, entity counts restored.

### 2.12 `lose_reachable` (Non-Patchable)
- **Method**: Calls `damagePlayer(maxHp)`.
- **Pass Rule**: `getState().status === 'lost'` and `hp === 0`.

### 2.13 `restart_resets_after_lose` (Non-Patchable)
- **Method**: Presses `r` key while in `'lost'` state.
- **Pass Rule**: State restored to `'playing'`, HP fully restored to `maxHp`.

### 2.14 `no_duplicate_enemies_after_restart` (Non-Patchable)
- **Method**: Attacks an enemy, immediately restarts with `r`, and waits 3.75s (longer than the 3.0s enemy respawn timer).
- **Pass Rule**: `final_enemies === initial_enemies`. Catches delayed respawn callback leaks.

### 2.15 `screenshot_captured` (Non-Patchable)
- **Method**: Calls `page.screenshot()`.
- **Pass Rule**: Output file exists on disk and size $> 0$ bytes.

### 2.16 `idle_survival_min_seconds` (Patchable)
- **Method**: Enables active enemy chasing with zero player input. Samples player HP every 100ms.
- **Pass Rule**: Player survives at least 3.0s (recommended >= 4.0s).
- **Why Patchable**: Caused by high enemy count, excessive enemy speed, or inadequate player HP. Can be repaired by reducing enemy speed/count or increasing player HP.

### 2.17 `flee_bot_survives` (Patchable)
- **Method**: Deploys a closed-loop reactive bot that samples enemy positions from `getEnemyPositions()` and steers away from the nearest threat, redirecting toward arena center when near walls.
- **Pass Rule**: Flee-bot survives for `min(12.0s, objective_target)`.
- **Why Patchable**: Caused by impossible chase speeds (e.g. enemies moving faster than player with narrow dodging margins). Can be repaired by applying `GameIRPatch`.

---

## 3. Patchable vs. Non-Patchable Failure Policy

The orchestrator enforces a strict architectural boundary:
1. **If ANY non-patchable check fails**: The system does **not** call the LLM repair agent. Repair cannot fix client rendering, input listeners, or state machine reset bugs. The job immediately terminates as `FAILED` with error code `QA_FAILED` and logs `"needs developer"`.
2. **If ONLY patchable checks fail (`idle_survival_min_seconds` or `flee_bot_survives`)**: The system transitions to state `REPAIRING`, invoking the repair agent to synthesize a targeted `GameIRPatch`.
