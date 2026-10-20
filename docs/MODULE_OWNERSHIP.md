# AETHER Module Ownership & Viva Examination Guide

This document maps all repository modules and subsystems to functional ownership groups and provides **3 defense/viva exam questions ("explain in your own words")** per module group.

---

## 1. Master Module Inventory Table

| Module Group | File Path | Core Purpose | Assigned Owner |
|---|---|---|---|
| **Group 1: Backend & Jobs** | `aether-backend/main.py` | FastAPI application initialization, CORS, static mounts, restart cleanup | `[Owner Name]` |
| | `aether-backend/routes/games_v1.py` | REST endpoints for game submission, status, spec, QA reports, events | `[Owner Name]` |
| | `aether-backend/services/orchestrator.py` | State machine governing lifecycle from prompt to test, repair, and ready | `[Owner Name]` |
| | `aether-backend/services/job_store.py` | SQLite persistence for game job records in `data/app.db` | `[Owner Name]` |
| | `aether-backend/services/event_store.py` | Append-only SQLite event stream recording transitions and diffs | `[Owner Name]` |
| | `aether-backend/schemas/api.py` | Pydantic request and response schemas for REST endpoints | `[Owner Name]` |
| **Group 2: LLM & Repair** | `aether-backend/providers/base.py` | Abstract model provider interface | `[Owner Name]` |
| | `aether-backend/providers/openai_compat.py` | OpenAI-compatible HTTP client with backoff and fallback chain | `[Owner Name]` |
| | `aether-backend/providers/mock.py` | Deterministic offline provider for tests and CI | `[Owner Name]` |
| | `aether-backend/providers/factory.py` | Provider instantiation factory respecting process environment | `[Owner Name]` |
| | `aether-backend/services/planner.py` | Prompt engineering translating natural language into GameIR | `[Owner Name]` |
| | `aether-backend/services/repair.py` | Self-repair agent diagnosing QA failures into `GameIRPatch` | `[Owner Name]` |
| **Group 3: GameIR & Validation**| `aether-backend/schemas/game_ir.py` | Versioned Pydantic v1.0 schema with strict bounds and patch model | `[Owner Name]` |
| | `aether-backend/services/validator.py` | Syntactic and semantic validator for GameIR contracts | `[Owner Name]` |
| **Group 4: Playwright QA** | `aether-backend/services/qa_runner.py` | Headless Playwright runner executing 17 spec-level smoke checks | `[Owner Name]` |
| | `scripts/run_qa_all.py` | Test harness running QA across all 4 demo routes | `[Owner Name]` |
| | `scripts/run_qa_fixtures.py` | Test harness verifying detection of 3 seeded failure traps | `[Owner Name]` |
| | `scripts/verify_slow_player_qa.py` | Automated verification of slow-player dynamic wall approach | `[Owner Name]` |
| **Group 5: Phaser Game Engine**| `aether-frontend/src/game/main.ts` | Phaser 3 Game configuration, canvas resolution, and scene setup | `[Owner Name]` |
| | `aether-frontend/src/game/scenes/ArenaScene.ts` | Arcade Physics simulation loop, entity spawning, win/loss logic | `[Owner Name]` |
| | `aether-frontend/src/game/hook.ts` | `window.__AETHER_GAME__` test hook exposed conditionally for `?test=1` | `[Owner Name]` |
| | `aether-frontend/src/game/savedDemos.ts` | Pre-recorded offline fallback demos requiring zero API calls | `[Owner Name]` |
| | `aether-frontend/src/game/palette.ts` | Theme-based color palettes and visual styling | `[Owner Name]` |
| **Group 6: Frontend UI** | `aether-frontend/src/pages/Forge.tsx` | Synthesis laboratory UI with timeline, trace drawer, and offline demos | `[Owner Name]` |
| | `aether-frontend/src/pages/PlayGame.tsx` | Game canvas wrapper with HUD overlay and restart listeners | `[Owner Name]` |
| | `aether-frontend/src/lib/apiClient.ts` | Axios/fetch client communicating with backend `/api/v1/` routes | `[Owner Name]` |
| | `aether-frontend/src/lib/mockApi.ts` | Client-side mock API for isolated frontend development | `[Owner Name]` |
| **Group 7: Harness & Ops** | `scripts/start_all.ps1` | Unified launcher starting servers and browser with banner | `[Owner Name]` |
| | `scripts/stop_all.ps1` | Failsafe teardown freeing ports 8000 and 5173 | `[Owner Name]` |
| | `scripts/run_real_eval.ps1` | Standalone evaluation runner with fallback enforcement | `[Owner Name]` |
| | `scripts/run_eval.py` | Full-pipeline evaluation script computing Playable@1 and @3 | `[Owner Name]` |
| | `scripts/e2e_smoke.py` | Headless end-to-end integration smoke test | `[Owner Name]` |
| | `scripts/repair_demo.py` | Interactive verification script demonstrating self-repair loop | `[Owner Name]` |

---

## 2. Viva Examination Questions ("Explain In Your Own Words")

### Group 1: Backend Architecture, Job Lifecycle & SQLite Persistence
1. **Question**: *"Why did you design the backend to accept generation requests with HTTP 202 Accepted and an explicit SQLite job queue rather than having the client wait synchronously for the game to generate?"*  
   **Model Answer**: Generating a game requires multi-step LLM planning, schema validation, and running a headless browser QA session with Playwright. This process takes between 20 to 60 seconds. A synchronous HTTP request would risk socket timeouts, browser disconnects, and server thread starvation. By persisting the job in SQLite and returning HTTP 202 immediately, the client can poll the job status and stream live timeline events, while allowing the backend to enforce a strict concurrency limit of 1 active job to avoid GPU/resource thrashing.
2. **Question**: *"How does the system ensure jobs are never left permanently stuck in an in-flight state if the backend server crashes or is restarted?"*  
   **Model Answer**: During the FastAPI lifespan startup event in `main.py`, the orchestrator queries SQLite for any jobs in active non-terminal states (`PLANNING`, `VALIDATING_SPEC`, `BUILDING`, `TESTING`, `REPAIRING`). Any found jobs are immediately marked as `FAILED` with error code `INTERNAL_ERROR` and a clear message stating the job was interrupted by server restart.
3. **Question**: *"What information is stored in the `events` table and why is it separated from the `games` table?"*  
   **Model Answer**: The `games` table stores current mutable state (status, current attempt, error code). The `events` table is an immutable, append-only audit log. Every state transition, validation outcome, and parameter repair patch (including rationale and before/after diffs) is recorded as a distinct chronological event. This provides complete auditability and powers the live visual timeline in the Forge UI.

---

### Group 2: LLM Providers, Planning & Parameter Self-Repair
1. **Question**: *"How does your OpenAI-compatible adapter handle API rate limiting and model overload when using Google AI Studio Gemini API?"*  
   **Model Answer**: Google AI Studio provides an OpenAI-compatible endpoint. Our adapter implements exponential backoff with jitter for HTTP 429 and 503 errors. In addition, when free-tier quota is exhausted, the provider automatically falls back through a configured chain of alternative models (`MODEL_FALLBACKS`) without failing the overall user experience.
2. **Question**: *"Why does the self-repair agent modify only numeric physics parameters rather than rewriting JavaScript or Phaser code?"*  
   **Model Answer**: LLMs writing raw executable code frequently introduce syntax errors, broken imports, and unpredictable bugs that are unsafe to run and difficult to verify automatically. By constraining the repair agent to a strict `GameIRPatch` schema, the system guarantees that all repairs remain structurally valid, deterministic, and easily validated by Pydantic before touching the browser runtime.
3. **Question**: *"What happens if the repair agent proposes an empty patch or parameters identical to the failing game?"*  
   **Model Answer**: The repair service detects no-op patches by diffing the proposed parameters against the failing GameIR. If no meaningful change is proposed, the patch is rejected and the LLM is prompted one additional time with an explicit instruction to differentiate parameters.

---

### Group 3: GameIR Schema & Pydantic Validation
1. **Question**: *"Why did you use `model_config = ConfigDict(extra='forbid')` across all Pydantic GameIR models?"*  
   **Model Answer**: LLMs often hallucinate attributes (such as `shield`, `gravity`, or `boss_phase`) that our Phaser client runtime does not implement. Using `extra='forbid'` ensures that any unmapped key causes immediate validation failure during the `VALIDATING_SPEC` stage, allowing the planner to retry before wasting time on browser QA.
2. **Question**: *"Explain the cross-field validation rules implemented in `ObjectiveConfig`."*  
   **Model Answer**: In `ObjectiveConfig`, the bounds on the `target` field depend on the `type` field. For survival games (`survive_seconds`), the target must be between 5 and 120 seconds. For collection games (`collect_count`), the target must be between 1 and 20 items. A Pydantic `model_validator` executes after field parsing to ensure this semantic coherence.
3. **Question**: *"How does GameIR ensure deterministic entity spawning across repeated runs?"*  
   **Model Answer**: The GameIR schema contains an optional `seed` integer. When present, the Phaser client initializes its pseudo-random number generator (PRNG) with this seed, ensuring that enemy spawn positions and collectible placements are 100% reproducible for QA testing.

---

### Group 4: Playwright QA Automation & Check Suite
1. **Question**: *"Explain the difference between patchable and non-patchable QA checks and why the distinction is critical."*  
   **Model Answer**: Non-patchable checks test engine and runtime stability (e.g. canvas visibility, input response, velocity consistency, restart isolation). If these fail, there is a bug in the client codebase or physics loops, which no parameter tweak can solve. Patchable checks test gameplay survivability (`idle_survival_min_seconds` and `flee_bot_survives`). If these fail, the game is physically functional but mechanically unbalanced, which is precisely what the LLM parameter repair loop is designed to fix.
2. **Question**: *"How does the QA runner verify player movement speed without interference from active enemies?"*  
   **Model Answer**: The QA runner invokes `_neutralize_enemies()` via the test harness hook, which pauses enemy motion and disables contact damage. It then drives the player with keyboard events and samples displacement and elapsed game time across steady-state movement, diagonal movement ($v / \sqrt{2}$), and wall sliding.
3. **Question**: *"How did you fix the slow-player wall-reach bug where players with move_speed = 100 px/s failed movement_speed_consistent?"*  
   **Model Answer**: The original test waited a fixed 1.6s for the player to reach the right arena wall. At 100 px/s, travelling from x=400 to x=784 requires ~3.8s, meaning the player was sampled in open space rather than sliding against the wall. We resolved this by dynamically scaling the approach timeout based on measured speed ($\max(5.0, (800 / v) + 1.5)$) with coordinate stabilization early-exit.

---

### Group 5: Phaser 3 Game Engine Client & Test Hook
1. **Question**: *"Why is the `window.__AETHER_GAME__` hook only accessible when `?test=1` is in the URL?"*  
   **Model Answer**: Exposing internal simulation hooks in production creates security risks and allows players to tamper with health, timers, or score. By deleting `window.__AETHER_GAME__` unless `?test=1` is present, the test surface is completely inaccessible to normal players.
2. **Question**: *"How does the `no_duplicate_enemies_after_restart` test verify that Phaser timers are properly cleaned up?"*  
   **Model Answer**: When an enemy is destroyed, Phaser schedules a delayed respawn event (3.0s). If the player presses 'R' to restart, a naïve implementation might reset the enemy count to initial count while leaving the pending timer active, resulting in extra "zombie" enemies appearing 3 seconds later. The test restarts after a kill, waits 3.75s, and asserts that the enemy count does not exceed the initial count.
3. **Question**: *"How does the client ensure the game runs at a consistent physics tick rate regardless of monitor refresh rate (60Hz vs 144Hz)?"*  
   **Model Answer**: Phaser Arcade Physics uses delta-time scaling in entity velocity updates (`velocity * delta / 1000`), ensuring that movement speed in pixels per second is identical whether the user has a 60Hz or 144Hz monitor.

---

### Group 6: Frontend UI, Forge Laboratory & Offline Demo
1. **Question**: *"How does the Forge UI communicate with the backend during game generation?"*  
   **Model Answer**: The Forge UI submits the prompt via `POST /api/v1/games` and begins polling `GET /api/v1/games/{id}` and `GET /api/v1/games/{id}/events` at 1-second intervals. This powers the real-time stage progression pills, the live agent trace drawer, and the before/after parameter diff display during repairs.
2. **Question**: *"How do the offline saved demos work, and why can they run without the backend server?"*  
   **Model Answer**: The offline demos are stored as static JSON files in `aether-frontend/public/fallback/`. When a user clicks a saved demo on the Forge page, the client loads the pre-validated GameIR specification, QA report, and event timeline directly into React state and local storage, enabling instant replay with zero network requests.
3. **Question**: *"What information is surfaced to the user when the model discloses a limitation?"*  
   **Model Answer**: When the planner adapts an impossible or out-of-domain prompt (e.g. 3D racing into 2D arena survival), it returns a list of limitations. The Forge UI renders these in an amber "What We Adapted" banner, providing full transparency to the player.

---

### Group 7: Harnesses, Evaluation & Operational Launchers
1. **Question**: *"Explain what `Playable@1` and `Playable@3` measure in your evaluation harness."*  
   **Model Answer**: `Playable@1` measures the percentage of games where the model's very first generated specification passes all 17 critical QA checks. `Playable@3` measures the percentage of games that become fully playable within a maximum of 2 repair attempts (up to 3 test runs total). The gap between `Playable@1` and `Playable@3` quantifies the effectiveness of the self-repair loop.
2. **Question**: *"Why must model fallback be disabled during scientific evaluation runs (`run_real_eval.ps1`)?"*  
   **Model Answer**: If fallback were enabled, a quota limit or error on `gemini-3.5-flash-lite` could silently fall back to `gemini-3.7-flash` or another model, polluting the evaluation dataset. Disabling fallback ensures that every row in the benchmark reflects only the exact model under test.
3. **Question**: *"How does `scripts/stop_all.ps1` reliably terminate running instances on Windows PowerShell?"*  
   **Model Answer**: It queries the active network listeners using `Get-NetTCPConnection` for ports 8000 and 5173, extracts their owning Process IDs (PIDs), and terminates them using `Stop-Process -Force`. This prevents port collision errors on subsequent launches.
