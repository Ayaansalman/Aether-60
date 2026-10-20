# AETHER Browser QA Test Hook Specification

> **Target Version:** 1.0 (60% Capstone Milestone)  
> **Reference:** Engineering Specification Section 7.1 (*Critical Smoke Checks*) & Section 7.2  
> **Global Identifier:** `window.__AETHER_GAME__`

---

## 1. Activation Policy

To protect production/demo integrity, the QA test hook is **conditionally enabled**.

* **Enabled Condition:** Only when the browser URL query parameter contains `?test=1` (e.g., `http://localhost:5173/play/demo?test=1`).
* **Disabled Condition:** When `?test=1` is absent, `window.__AETHER_GAME__` is strictly `undefined` (`delete window.__AETHER_GAME__`).
* **Design Rule:** Normal player keyboard input (`WASD`, Arrow keys, `Space`, `R`) and physics loops remain identical whether the hook is active or inactive.

---

## 2. API Contract & Surface

When active, `window.__AETHER_GAME__` exposes the following interface:

```typescript
interface AetherGameHook {
  ready: boolean;
  tick: number;
  getState: () => GameState;
  advanceTimer: (seconds: number) => void;
  simulatePickup: () => void;
  damagePlayer: (n: number) => void;
  getEnemyPositions: () => EnemyPosition[];
  pauseEnemies: (paused: boolean) => void;
}
```

---

## 3. Properties

### `ready: boolean`
* Set to `true` once Phaser has completed `ArenaScene.create()` and the game viewport is interactive.
* Used by Playwright to await startup:
  ```python
  page.wait_for_function("() => window.__AETHER_GAME__ && window.__AETHER_GAME__.ready === true")
  ```

### `tick: number`
* An integer counter incremented on every `ArenaScene.update()` frame tick.
* Used by QA smoke tests to prove the simulation loop is progressing and not frozen.

---

## 4. `getState()` Schema & Fields

Calling `window.__AETHER_GAME__.getState()` returns a synchronous, JSON-serializable snapshot of the active game state:

```json
{
  "status": "playing",
  "hp": 3,
  "maxHp": 3,
  "score": 0,
  "target": 8,
  "objectiveType": "collect_count",
  "timeElapsed": 4,
  "timeLeft": null,
  "attackMode": "projectile",
  "attacksPerformed": 1,
  "player": {
    "x": 400,
    "y": 300
  },
  "enemyCount": 5,
  "collectibleCount": 10,
  "projectileCount": 0,
  "hud": {
    "health": "HP: 3 / 3",
    "objective": "Crystals: 0 / 8",
    "controls": "Controls: WASD or arrow keys | Space"
  }
}
```

### Field Definitions

| Field | Type | Description |
|---|---|---|
| `status` | `'playing' \| 'won' \| 'lost'` | Current lifecycle state. Reaching 0 HP sets `'lost'`; fulfilling objective sets `'won'`. |
| `hp` | `number` | Current player health points. |
| `maxHp` | `number` | Maximum player health defined in GameIR (`player.max_health`). |
| `score` | `number` | Current crystals/items collected. |
| `target` | `number` | Target score (for `collect_count`) or target seconds (for `survive_seconds`). |
| `objectiveType` | `'collect_count' \| 'survive_seconds'` | Archetype objective mode. |
| `timeElapsed` | `number` | Wall-clock seconds elapsed since round start. |
| `timeLeft` | `number \| null` | Remaining seconds on countdown timer for `survive_seconds`; `null` for `collect_count`. |
| `attackMode` | `'projectile' \| 'melee' \| 'avoid_only'` | Active attack capability from GameIR (`player.attack_mode`). |
| `attacksPerformed` | `number` | Counter incrementing each time an attack fires (projectile spawned or melee swing executed). |
| `player` | `{ x: number, y: number }` | Current integer coordinates of the player center. |
| `enemyCount` | `number` | Count of currently active, alive enemies on screen. |
| `collectibleCount` | `number` | Count of uncollected items remaining in the arena. |
| `projectileCount` | `number` | Count of in-flight active player projectiles. |
| `hud.health` | `string` | Exact text rendered in top-left health HUD (e.g. `"HP: 3 / 3"`). |
| `hud.objective` | `string` | Exact text rendered in objective HUD (e.g. `"Crystals: 0 / 8"` or `"Time: 29s"`). |
| `hud.controls` | `string` | Exact text rendered in controls HUD (e.g. `"Controls: WASD or arrow keys | Space"`). |

---

## 5. Deterministic QA Helper Methods

All helper methods invoke the **identical runtime logic** as natural gameplay events, ensuring win/loss triggers, visual overlays, and HUD updates are authentic.

### `advanceTimer(seconds: number)`
* **Usage:** `window.__AETHER_GAME__.advanceTimer(5)`
* **Behavior:** Advances the survival countdown timer by `seconds`. If `timeLeft` reaches `0`, triggers `triggerGameWin()`, freezing motion and rendering the emerald `"YOU WIN, press R to restart"` overlay.

### `simulatePickup()`
* **Usage:** `window.__AETHER_GAME__.simulatePickup()`
* **Behavior:** Simulates collecting one item. Consumes an active collectible circle from the arena, increments `score`, updates the HUD, and triggers `triggerGameWin()` if `score >= target`.

### `damagePlayer(n: number)`
* **Usage:** `window.__AETHER_GAME__.damagePlayer(1)`
* **Behavior:** Deducts `n` HP through the normal damage pipeline. Triggers player invulnerability blinking and updates HUD. If HP hits `0`, triggers `triggerGameOver()`, halts simulation, and displays the dark `"YOU DIED, press R to restart"` overlay.

### `getEnemyPositions(): Array<{ x: number, y: number }>`
* **Usage:** `window.__AETHER_GAME__.getEnemyPositions()`
* **Behavior:** Returns array of integer coordinates for all alive enemies. Used by QA to verify seeded PRNG spawn distance ($\ge 200\text{px}$ from player center).

### `pauseEnemies(paused: boolean)`
* **Usage:** `window.__AETHER_GAME__.pauseEnemies(true)`
* **Behavior:** While paused, enemies halt all movement (velocity is set to zero) and cannot damage or knock back the player. Normal chase movement and damage checks resume when passed `false`.

---

## 6. Playwright Automation Example

```python
# Verify canvas loads and test hook is available
page.goto("http://localhost:5173/play/demo?test=1")
page.wait_for_function("() => window.__AETHER_GAME__ && window.__AETHER_GAME__.ready")

# Check initial tick progression
initial_tick = page.evaluate("() => window.__AETHER_GAME__.tick")
page.wait_for_timeout(200)
new_tick = page.evaluate("() => window.__AETHER_GAME__.tick")
assert new_tick > initial_tick, "Simulation update loop is stalled"

# Check initial state
state = page.evaluate("() => window.__AETHER_GAME__.getState()")
assert state["status"] == "playing"
assert state["hp"] == 3
assert state["enemyCount"] == 5

# Test deterministic loss
page.evaluate("() => window.__AETHER_GAME__.damagePlayer(3)")
lost_state = page.evaluate("() => window.__AETHER_GAME__.getState()")
assert lost_state["status"] == "lost"
assert lost_state["hp"] == 0

# Test real keyboard restart
page.keyboard.press("r")
page.wait_for_timeout(200)
reset_state = page.evaluate("() => window.__AETHER_GAME__.getState()")
assert reset_state["status"] == "playing"
assert reset_state["hp"] == 3
```

---

## 7. Known-Broken Fixture Modes (Blueprint Section 7.4)

When the URL contains **both** `?test=1` and `?bug=<name>`, the runtime intentionally activates known failure modes for QA runner validation:

* **`?test=1&bug=restart_keeps_hp`**:
  * Restarting the game (via keyboard `R`) retains the pre-restart player HP (e.g. 0 HP after losing) rather than restoring it to `max_health`.
  * Triggers failure in checks `restart_resets_after_lose` and `restart_resets_after_win`.

* **`?test=1&bug=no_win`**:
  * Fulfilling the level objective (collecting target crystals or surviving target seconds) never triggers the win condition (`status` remains `'playing'`, overlay does not appear).
  * Triggers failure in check `win_reachable`.

* **Safety Isolation Rule:** If `?test=1` is absent, the `bug` query parameter is strictly ignored, ensuring normal players are never exposed to broken behavior.

