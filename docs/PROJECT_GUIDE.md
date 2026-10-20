# AETHER Comprehensive Engineering & Project Guide

**Author**: AETHER Engineering Team  
**Audience**: Teammate Handover (Ayaan) & Independent Developer Onboarding  
**Milestone**: 60% Capstone Show-and-Tell Milestone  
**Repository Branch**: `main`  
**Document Status**: Authoritative Technical Manual  

---

## 1. What This Project Is

AETHER (*Autonomous Engine for Text-to-Heuristic Environmental Rendering*) is an automated software engineering pipeline that synthesizes playable, deterministic 2D video games directly from natural language prompts. Traditional approaches to AI game generation ask Large Language Models (LLMs) to write raw game engine code (such as JavaScript or GDScript), which almost inevitably results in syntax errors, runtime crashes, hallucinated APIs, and unplayable physics. AETHER eliminates these failure modes by decoupling natural language planning from game execution through an intermediate representation contract called `GameIR v1.0`.

Instead of generating unbounded code, the LLM acts purely as a high-level game designer that produces structured JSON conforming to strict Pydantic schemas (`schemas/game_ir.py`). This specification is validated deterministically (`services/validator.py`), rendered through a battle-tested Phaser 3 browser client (`aether-frontend/src/game/ArenaScene.ts`), and verified in a real headless browser using 17 automated Playwright smoke checks (`services/qa_runner.py`). If a generated game fails automated smoke checks or is lethal, an automated closed-loop parameter repair agent (`services/repair.py`) adjusts numeric attributes (such as speeds, counts, and health) to restore playability before delivering the game to the human player.

### The Safe Engineering Claim (Blueprint Section 17)
As formally documented in `docs/DOCUMENT4_OUTLINE.md` and `docs/LIMITATIONS.md`:

> *"We built a prompt-to-browser-game prototype with a structured game representation, automated smoke tests, and a bounded repair loop."*

### What AETHER Can and Cannot Do

| What AETHER Can Do | What AETHER Cannot Do |
|---|---|
| Autonomously translate English prompts into structured `GameIR v1.0` JSON specs (`services/orchestrator.py`). | Synthesize arbitrary new game genres (no platformers, RPGs, or 3D open worlds). |
| Render deterministic 2D top-down arena survival games in Phaser 3 Arcade physics (`aether-frontend/src/game/ArenaScene.ts`). | Generate raw JavaScript, TypeScript, or GLSL shader code from scratch. |
| Execute 5 distinct enemy AI behaviors (`chaser`, `bouncer`, `patroller`, `dasher`, `shooter`). | Implement complex stealth, line-of-sight vision cones, or flocking boids. |
| Construct 4 arena obstacle layouts (`open`, `pillars`, `lanes`, `maze`) with collision geometry. | Support multiplayer networking or peer-to-peer game synchronization. |
| Enforce 3 distinct victory objectives (`collect_count`, `survive_seconds`, `defeat_enemies`). | Guarantee subjective player fun, juice, emotional engagement, or narrative depth. |
| Execute 17 automated headless browser QA checks using Playwright (`services/qa_runner.py`). | Automatically repair runtime crashes, stalled canvases, or broken client event listeners. |
| Autonomously repair unplayable physics parameters within a bounded 2-iteration repair loop (`services/repair.py`). | Re-attempt repairs indefinitely (hard cap of 2 repairs / 3 test attempts). |
| Seamlessly fall back across backup LLMs on Google AI Studio HTTP 429 quota exhaustion (`providers/openai_compat.py`). | Bypass upstream provider API rate limits or resolve zero-credit billing lockouts. |
| Operate 100% offline with zero external API calls in mock mode or via bundled saved demos (`scripts/start_all.ps1 -Mock`). | Autonomously push code to remote Git repositories (strictly prohibited by project rules). |

---

## 2. The Big Picture

### 2.1 Pipeline Diagram
```
                    [ Natural Language User Prompt ]
                                   │
                                   ▼
                       [ Forge Frontend Page ]
                  (aether-frontend/src/pages/Forge.tsx)
                                   │
                       HTTP POST /api/v1/games
                                   │
                                   ▼
                       [ REST API Route Handler ]
                   (aether-backend/routes/games_v1.py)
                                   │
               Job record initialized in SQLite (status: QUEUED)
               (aether-backend/services/job_store.py)
                                   │
                                   ▼
                    [ Background Orchestrator Worker ]
                   (aether-backend/services/orchestrator.py)
                                   │
                        Transition to PLANNING
                                   │
                                   ▼
                         [ Model Provider Layer ]
                  (aether-backend/providers/factory.py)
                 ├── OpenAICompatProvider (Google Gemini API)
                 └── MockModelProvider (Deterministic Offline Mock)
                                   │
                      LLM returns raw JSON string
                                   │
                                   ▼
                        Transition to VALIDATING_SPEC
                                   │
                         [ Schema & Safety Validator ]
                    (aether-backend/services/validator.py)
                 ├── Pydantic v2 strict type checking (schemas/game_ir.py)
                 ├── Numeric range clamping & safety checks
                 └── (If invalid: up to 2 model retries before MODEL_OUTPUT_INVALID)
                                   │
                        Transition to BUILDING
                                   │
                 Saves validated spec to SQLite & artifacts folder
                                   │
                        Transition to TESTING
                                   │
                                   ▼
                       [ Headless Playwright QA Runner ]
                     (aether-backend/services/qa_runner.py)
                 Navigates to: http://localhost:5173/play/{id}?test=1
                 Hooks into: window.__AETHER_GAME__ (qaHook.ts)
                 Executes 17 spec-level smoke checks sequentially
                                   │
           ┌───────────────────────┴───────────────────────┐
           ▼                                               ▼
[ All 17 Checks PASS ]                       [ Check Failure Detected ]
           │                                               │
           │                                ┌──────────────┴──────────────┐
           │                                ▼                             ▼
           │                      [ Non-Patchable Failure ]    [ Only Patchable Failures ]
           │                      (e.g. canvas stalled,        (idle_survival or
           │                       restart broke)               flee_bot failed)
           │                                │                             │
           │                                ▼                             ▼
           │                         [ Job Status: FAILED ]       [ Attempt < 3? ]
           │                         Error: QA_FAILED                     │
           │                         ("needs developer")         ┌────────┴────────┐
           │                                                     ▼ (Yes)           ▼ (No)
           │                                            Transition to REPAIRING   [ Job Status: FAILED ]
           │                                                     │                Error: REPAIR_LIMIT_REACHED
           │                                                     ▼
           │                                         [ Bounded Repair Agent ]
           │                                         (services/repair.py)
           │                                         Applies GameIRPatch
           │                                         Increments attempt count
           │                                                     │
           │                                                     ▼
           │                                         [ Re-validate & Re-test ]
           │                                         (Loop back to VALIDATING)
           │                                                     │
           ▼                                                     ▼
[ Terminal State: READY ] ◄──────────────────────────────────────┘
(Or READY_WITH_WARNINGS if non-critical)
           │
           ▼
[ User Plays Game on Phaser Canvas ]
(aether-frontend/src/pages/PlayGame.tsx -> ArenaScene.ts)
```

### 2.2 Complete Job Lifecycle Statuses

Every job transitions through explicit states recorded in SQLite (`services/job_store.py`):

1. `QUEUED`: Job accepted by the API, recorded in database, waiting for orchestrator queue lock.
2. `PLANNING`: Model provider is actively processing prompt and generating GameIR specification.
3. `VALIDATING_SPEC`: Pydantic validator is verifying types, semantic rules, and regex safety boundaries.
4. `BUILDING`: Validated GameIR is mapped to the runtime URL and saved in SQLite and disk artifacts.
5. `TESTING`: Playwright headless Chromium is running the 17 automated verification checks.
6. `REPAIRING`: A playability failure occurred; the repair agent is generating a numeric `GameIRPatch`.
7. `READY`: Terminal success. All 17 QA checks passed. Game is playable.
8. `READY_WITH_WARNINGS`: Terminal success with non-critical warnings (e.g. minor HUD text mismatch).
9. `FAILED`: Terminal failure. Contains `error_code` and `error_message`. No further automated retries.

### 2.3 Step-by-Step Walkthrough of ONE Request

Here is the exact code execution path when a user types a prompt and clicks **Synthesize Game**:

1. **User Interaction (`aether-frontend/src/pages/Forge.tsx`)**:
   - The user enters a prompt (e.g. `"spooky wizard collecting crystals while ghosts chase"`) into the input textarea and clicks **Synthesize**.
   - `Forge.tsx:handleCreate()` validates that the prompt is between 5 and 1200 characters, clears previous errors, sets UI status to `QUEUED`, and calls `apiClient.createGame(trimmed)`.
2. **REST API Ingestion (`aether-backend/routes/games_v1.py`)**:
   - `POST /api/v1/games` receives `GameCreateRequest(prompt=...)`.
   - `create_game()` generates a new UUID `game_id`, writes the initial job record (`status='QUEUED'`) to SQLite via `job_store.create_job()`, emits a `QUEUED` event via `event_store.emit_event()`, and launches `asyncio.create_task(run_orchestrator(game_id, prompt))`.
   - Returns HTTP `202 Accepted` with payload `{"id": game_id, "status": "QUEUED"}`.
3. **Frontend Polling (`aether-frontend/src/pages/Forge.tsx`)**:
   - `Forge.tsx:startPolling(gameId)` sets up an interval that polls `GET /api/v1/games/{id}` and `GET /api/v1/games/{id}/events` every 1500ms via `apiClient.getGame()` and `apiClient.getEvents()`.
4. **Pipeline Orchestration (`aether-backend/services/orchestrator.py`)**:
   - `run_orchestrator()` acquires `_queue_lock = asyncio.Lock()` (concurrency limit 1).
   - Updates status to `PLANNING`, emits lifecycle start event, and calls `services.planner.plan_game(prompt, provider)`.
5. **Model Planning (`aether-backend/services/planner.py` & `providers/`)**:
   - `plan_game()` constructs the system prompt containing GameIR schema boundaries, enums, and few-shot examples.
   - Calls `provider.plan(prompt, system_prompt)`:
     - In live mode (`providers/openai_compat.py`), sends HTTP POST to Gemini endpoint with timeout handling and 429 quota detection.
     - In mock mode (`providers/mock.py`), returns a pre-authored deterministic GameIR matching the prompt keyword.
   - `strip_code_fences()` strips any markdown ```json wrapping.
6. **Schema & Semantic Validation (`aether-backend/services/validator.py`)**:
   - Orchestrator updates status to `VALIDATING_SPEC`.
   - `validate_game_ir()` runs `GameIR.model_validate(raw_dict)`:
     - Rejects unknown extra keys (`extra="forbid"`).
     - Validates numeric bounds: `player.move_speed` in `[100.0, 300.0]`, `max_health` in `[1, 10]`, `enemies` count in `[1, 50]`.
     - Validates semantic integrity: at least 1 total enemy; for `collect_count`, target $\le$ total collectibles; rejects `defeat_enemies` with `avoid_only`.
     - Validates safety: scans strings against `FORBIDDEN_REGEX_PATTERNS` (`<script`, `eval(`, URLs).
   - If invalid, orchestrator sends a targeted retry prompt with error feedback to the model (up to 2 retries).
   - Writes validated spec to `artifacts/{game_id}/game_ir_v1.json`.
7. **Runtime Assembly (`aether-backend/services/orchestrator.py`)**:
   - Orchestrator updates status to `BUILDING`.
   - Stores spec in SQLite `job_store.update_job(spec=...)`.
   - Sets `game_url = f"http://localhost:5173/play/{game_id}"`.
8. **Automated Headless Browser QA (`aether-backend/services/qa_runner.py`)**:
   - Orchestrator updates status to `TESTING` (Attempt 1).
   - Calls `QARunner.run_qa(url="http://localhost:5173/play/{game_id}?test=1", output_dir=...)`.
   - Launches headless Chromium via Playwright, sets viewport to 1280x800, and navigates to the test URL.
   - Waits for `window.__AETHER_GAME__.ready === true` in `aether-frontend/src/game/ArenaScene.ts`.
   - Sequentially executes all 17 checks:
     - Verifies canvas dimensions $> 0$.
     - Simulates keyboard inputs (`d` held 600ms) to measure straight, diagonal, and wall-slide velocities ($\pm 15\%$ tolerance).
     - Tests attack responsiveness and HUD string reflections.
     - Tests win reachability, loss reachability, and restart state isolation.
     - Runs 3.0s idle survival test and 12.0s flee-bot evasion test.
     - Captures PNG screenshot to `artifacts/{game_id}/play_{game_id}.png`.
   - Saves `artifacts/{game_id}/qa_report_attempt_1.json`.
9. **Repair Loop Trigger (`aether-backend/services/repair.py`)**:
   - If all 17 checks pass: skips repair.
   - If `idle_survival_min_seconds` or `flee_bot_survives` failed and attempt $< 3$:
     - Orchestrator updates status to `REPAIRING`.
     - `propose_repair()` sends failed check metrics and legal patch ranges to the model.
     - Model returns `GameIRPatch` JSON (e.g. reducing enemy count/speed, boosting player speed/health).
     - `apply_patch()` applies numeric diffs and clamps values.
     - Orchestrator re-validates, writes `game_ir_v2.json`, and re-runs `qa_runner.py` for Attempt 2.
10. **Terminal Completion & Handoff (`aether-backend/services/orchestrator.py`)**:
    - Updates job status to `READY` in SQLite with `qa_summary` populated.
    - Emits final completion event.
11. **User Plays Game (`aether-frontend/src/pages/PlayGame.tsx`)**:
    - Frontend poller detects `status === 'READY'`, stops polling, and displays green "READY" badge, QA report drawer, and **Launch Game** button.
    - User clicks **Launch Game** (navigates to `/play/{game_id}`).
    - `PlayGame.tsx` fetches validated spec via `apiClient.getSpec(game_id)`.
    - Mounts `<GameCanvas gameIR={spec} />`, which boots Phaser 3 `ArenaScene` on an 800x600 canvas.
    - User controls the player using WASD or arrow keys and Space bar.

---

## 3. What Was Built and In Which Order

### 3.1 Milestone Development History (Phases 0–10)

The project progressed phase-by-phase against `docs/MASTER_PLAN.md`. Every phase was validated with tests before committing:

| Phase | Milestone Objective | Date | Commit Hash | Key Deliverables & Test Results |
|---|---|:---:|:---:|---|
| **Phase 0** | Real-Model Planner Verification | 2026-10-12 | `7089f86` | Benchmarked Gemini planner (`gemini-3.8-flash`, `docs/eval/planner_gemini-3.8-flash_benchmark.json`): 90% first-valid schema rate, 100% theme honesty, median latency 17.3s. 24 pytest passed. |
| **Phase 1** | Jobs Pipeline Backend | 2026-10-12 | `4a0e715` | SQLite job store (`job_store.py`), event store (`event_store.py`), `/api/v1` routes (`games_v1.py`), background orchestrator. 38 pytest passed; `api_walk.py` 11/11 passed. |
| **Phase 2** | Frontend API Wiring | 2026-10-12 | `e70f8bd` | Replaced mock frontend with real API client (`apiClient.ts`). Wired Forge timeline, limitations list, and diff drawer. 38 pytest passed; `tsc` clean. |
| **Phase 3** | End-to-End Smoke (Mock) | 2026-10-12 | `1c177d4` | Live pipeline reached `READY` in 23.1s with mock provider; 15/15 initial QA checks passed; canvas 800x600 confirmed; screenshot saved. |
| **Phase 4** | Spec-Level QA & Repair Loop | 2026-10-13 | `3bade75` | 17 spec-level Playwright checks (`qa_runner.py`); fixture detection (`run_qa_fixtures.py`); bounded repair demo (`repair_demo.py`): Attempt 1 FAIL -> patch -> Attempt 2 PASS in 63.5s. 63 pytest passed. |
| **Phase 5** | 12-Prompt Benchmark Harness | 2026-10-14 | `dbed943` | Standardized evaluation runner (`scripts/run_eval.py`) with canonical prompts (`p01`–`p10`, `s01`–`s02`). Verified Playable@1 vs Playable@3 tracking. 77 pytest passed. |
| **Phase 5.5**| Model Fallback Chain | 2026-10-14 | `fbcf202` | Automatic fallback across `MODEL_FALLBACKS` on HTTP 429 quota exhaustion; process-level active model persistence; empty-response retry handling. 83 pytest passed. |
| **Phase 5.6**| Real-Model Evaluation (Run A/C)| 2026-10-14 | `528e17c` | Run A (`gemini-3.5-flash-lite`, 12 prompts): 91.7% first-valid, 75.0% Playable@1, 100% theme honesty, median end-to-end lat 45.8s (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`). Run C (`gemini-3.8-flash`): p01 READY (66.6s), p02 timed out (cause not established; `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json`). |
| **Phase 5.7**| Repair Prompt Tuning & Run A2 | 2026-10-14 | `5ecd8f9` | Enhanced repair prompt with measured vs. required thresholds; Run A2 re-run on 3 dev prompts repaired 2/2 (`s01`, `s02`) while `p06` was not repaired (tiny sample, dev cases; `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`). 86 pytest passed. |
| **Phase 6** | Operational Resilience | 2026-10-14 | `212d40e` | PowerShell launchers (`scripts/start_all.ps1`, `stop_all.ps1`); health checker (`demo_check.py`); offline fallback generator (`make_fallback.py`); zero-API offline demo row in Forge. |
| **Phase 6.5**| Standalone Eval Launcher | 2026-10-14 | `ff481f8` | `scripts/run_real_eval.ps1` with automated Vite server lifecycle, isolated model environment, artifact archiving to `docs/eval/`, and auto-updating `docs/EVAL_RESULTS.md`. |
| **Phase 6.6**| Visual Themes | 2026-10-14 | `6eca685` | Curated palettes & primitive geometric shapes for `fantasy`, `sci_fi`, `pirate`, `spooky`, `cozy` in `ArenaScene.ts`. HUD cards for title, premise, and controls. |
| **Phase 7** | System Documentation | 2026-10-14 | `b17f700` | Authoring of complete formal documentation suite (`architecture.md`, `GameIR-v1.md`, `QA_CHECKS.md`, `QA_HOOK.md`, `REPAIR_LOOP.md`, `LIMITATIONS.md`, `HOW_TO_RUN.md`). |
| **Phase 8** | Final Verification & Checklist| 2026-10-15 | `(merged)` | Cleared all project type diagnostics in Pyrefly (0 warnings across repo); full audit in `docs/FINAL_CHECKLIST.md` (42 verified, 1 partial, 5 human tasks). |
| **Phase 8.1**| Run C Evaluation Evidence | 2026-10-15 | `c8ef005` | Re-benchmarked `gemini-3.8-flash`; Run C preflight timed out at 60s (cause not established; `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`); updated comparative analysis in `docs/EVAL_RESULTS.md`. |
| **Phase 9** | Mechanic Variety Expansion | 2026-10-15 | `b22c97e` | Expanded engine: 5 enemy AI behaviors, 4 arena layouts, `defeat_enemies` objective, `visual_overrides`. 47 new unit tests in `test_mechanic_variety.py`. |
| **Phase 9.1**| Portable Paths & QA Dispatch | 2026-10-16 | `23df69b` | Removed hardcoded laptop paths; pyrefly 0 diagnostics; Check 8 QA dispatch for `defeat_enemies`; 137 pytest passed; 5/5 variety demos pass 17/17 QA. |
| **Phase 10** | Handover Guide & Cleanup | 2026-10-16 | `a78b4de` | Authoring `docs/HANDOVER.md`; untracked 35MB archive & PDF without disk deletion; updated .gitignore, README, and HOW_TO_RUN. |
| **Phase 12** | Real-Model Evaluation Run D | 2026-10-16 | `f72e53e` | Real eval of `gemini-3.5-flash-lite` on upgraded engine (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`): 12/12 complete, 12/12 first-valid, 9/12 Playable@1, 12/12 Playable@3, 3/3 repair, 18 model requests, 47,020.5 ms median latency. |

### 3.2 Key Architectural Decisions & Why They Were Made

Detailed rationale is recorded in `docs/DECISIONS.md` and `docs/LIMITATIONS.md`:

1. **GameIR Instead of Generated JavaScript/TypeScript Code**:
   - *Problem*: LLMs generating raw Phaser or Canvas code hallucinate non-existent methods, produce syntax errors, create variable scope leaks, and generate unpredictable collision bugs.
   - *Decision*: Constrain the model output to a declarative JSON intermediate representation (`GameIR v1.0`).
   - *Why*: Pydantic v2 enforces strict types and boundaries. Our Phaser client (`ArenaScene.ts`) executes the physics, collisions, and rendering deterministically.
2. **Single Gameplay Archetype (`arena_survival`)**:
   - *Problem*: Synthesizing multiple game genres (platformers, RPGs, racing) at 60% milestone produces shallow, unpolished, broken toys.
   - *Decision*: Restrict the engine strictly to 2D top-down arena survival on an 800x600 canvas with `free_2d` omnidirectional movement.
   - *Why*: Allows automated smoke bounding of movement velocities ($\pm 15\%$), evasion vectors, and survival times. Out-of-domain prompts (like 3D racing) are adapted into arena survival with explicit limitation disclosures.
3. **Bounded, Parameter-Only Self-Repair**:
   - *Problem*: Letting an LLM rewrite code in a repair loop introduces new bugs, creates infinite loops, and costs excessive API tokens.
   - *Decision*: The repair loop only tunes numeric attributes (`player_move_speed`, `player_max_health`, `enemy_count`, `enemy_speed_multiplier`, `objective_target`) with a hard maximum of 2 repairs (3 test runs).
   - *Why*: Parameter tuning solves playability (too hard / instant death) safely. If a non-patchable check fails (canvas crashed, restart broke), repair is skipped immediately and the job fast-fails as `QA_FAILED`.
4. **Unified OpenAI-Compatible Provider Adapter (ADR-001 in `docs/DECISIONS.md`)**:
   - *Problem*: Using vendor-specific Python SDKs (`google-generativeai`, `openai`, `anthropic`) creates vendor lock-in, bloated dependencies, and conflicting async event loops.
   - *Decision*: Use standard synchronous `httpx` communicating via OpenAI-compatible `/chat/completions` endpoints.
   - *Why*: Switches instantly between Google AI Studio Gemini, local vLLM, Tokenra, or mock mode via `.env` without changing application code.
5. **Automatic Model Fallback Chain**:
   - *Problem*: Google AI Studio free-tier accounts enforce a 15 RPM limit, causing HTTP 429 quota exhaustion during live demonstrations.
   - *Decision*: When a 429 quota exhaustion is detected, `openai_compat.py` cycles to the next model in `MODEL_FALLBACKS` and retains the new model for subsequent requests in that process.

---

## 4. Repository Map

### 4.1 Top-Level Directories

| Directory | Purpose | When You Would Touch It |
|---|---|---|
| [`aether-backend/`](../aether-backend) | Python 3.11 FastAPI backend service, orchestrator, planners, QA runner, and tests. | When modifying pipeline logic, schemas, validation rules, or test suites. |
| [`aether-frontend/`](../aether-frontend) | React 19 + Vite + TypeScript web application and Phaser 3 game engine client. | When modifying the game canvas, Phaser physics, UI pages, or saved offline demos. |
| [`docs/`](.) | Formal specifications, benchmark evaluation reports, runbooks, and handover guides. | When consulting specifications, checking benchmark evidence, or updating documentation. |
| [`scripts/`](../scripts) | Automation scripts, PowerShell launchers, QA runners, and evaluation harnesses. | When running tests, launching servers, executing evaluations, or generating fallbacks. |

---

### 4.2 Backend Files (`aether-backend/`)

| File / Subfolder | What It Does | When You Would Touch It |
|---|---|---|
| `main.py` | FastAPI application entry point, CORS middleware, API router mounting, and static asset mounting. | When registering new route modules or altering global middleware. |
| `database.py` | In-memory database mock for 30% prototype user auth and social features. | Rarely; legacy prototype code kept for route compatibility. |
| `models.py` | Pydantic models for user authentication, profiles, and social engagement. | When editing user authentication or social feed data schemas. |
| `auth.py` | JWT token creation, password hashing, and user credential verification. | When modifying authentication logic or token lifetimes. |
| `seed_data.py` | Seed data generator for public gallery mock games. | Rarely; used only for mock social feed population. |
| `pyrefly.toml` | Configuration for Pyrefly static type checker. | When altering search paths or project type-checking rules. |
| `pytest.ini` | Pytest test configuration and python path settings. | When configuring test flags or test markers. |
| `requirements.txt` | Minimal Python dependencies (`fastapi`, `uvicorn`, `pydantic`, `httpx`, `playwright`, `pytest`). | When adding new backend Python dependencies. |
| `.env.example` | Template for environment variables (`MODEL_PROVIDER`, `MODEL_API_KEY`, etc.). | When introducing a new configurable environment variable. |
| **`providers/base.py`** | Abstract base class `ModelProvider`, custom exceptions (`ModelHttpError`, `ModelTimeoutError`), and request counters. | When defining new model provider interfaces or error types. |
| **`providers/factory.py`** | Factory function `get_provider()` that instantiates the active provider based on environment variables. | When adding a new model provider option. |
| **`providers/mock.py`** | Deterministic offline mock model provider that returns keyword-matched specs with zero API usage. | When adding new deterministic offline test responses or repair mocks. |
| **`providers/openai_compat.py`**| OpenAI-compatible HTTP adapter supporting Google Gemini, exponential backoff, and model fallback chains. | When modifying LLM request logic, header formatting, or fallback handling. |
| **`routes/games_v1.py`** | REST API endpoints for `/api/v1/games`, spec retrieval, QA reports, event streams, and `/health`. | When adding or modifying `/api/v1` API endpoints. |
| `routes/auth.py` | Prototype authentication endpoints (`/api/auth/register`, `/api/auth/login`). | When modifying legacy prototype authentication. |
| `routes/games.py` | Prototype game library endpoints (`/api/games/library`, `/api/games/save`). | When modifying legacy prototype game management. |
| `routes/generate.py` | Prototype mock generation endpoint (`/api/generate/`). | Kept for backwards compatibility; real pipeline uses `games_v1.py`. |
| `routes/social.py` | Prototype social engagement endpoints (likes, comments, shares). | When editing legacy social features. |
| `routes/users.py` | Prototype user profile endpoints (`/api/users/me`). | When editing legacy user profile management. |
| **`schemas/game_ir.py`** | Authoritative Pydantic v2 `GameIR` schema, enums, `GameIRPatch`, and `apply_patch()` function. | When extending GameIR fields, enums, allowed ranges, or patch rules. |
| `schemas/api.py` | Pydantic models for API requests and responses (`GameCreateRequest`, `GameStatusResponse`, etc.). | When modifying API request or response structures. |
| **`services/orchestrator.py`** | Core state machine driver (`QUEUED` to `READY`), queue locking, attempt management, and lifecycle events. | When modifying pipeline state transitions or repair loop flow. |
| **`services/validator.py`** | Pydantic schema validation, numeric range clamping, semantic checks, and regex safety scanning. | When adding new validation rules, semantic constraints, or safety filters. |
| **`services/planner.py`** | System prompt builder for the natural language game planner and markdown fence stripper. | When improving planner prompt engineering or few-shot examples. |
| **`services/qa_runner.py`** | Playwright automated headless browser test harness executing the 17 spec-level smoke checks. | When adding new browser QA checks or modifying check tolerances. |
| **`services/repair.py`** | Parameter-only bounded repair agent prompt builder, response parser, and no-op patch detector. | When tuning the repair agent system prompt or patch validation rules. |
| **`services/job_store.py`** | SQLite persistence store managing the `games` table, job states, error codes, and spec JSON. | When altering database schema, state persistence, or query logic. |
| **`services/event_store.py`** | SQLite persistence store managing the `events` table for chronological timeline auditing. | When adding new timeline event fields or query methods. |
| `services/game_registry.py` | Prototype in-memory game registry for 30% social features. | Kept for legacy route compatibility. |
| **`bench/prompts.json`** | Canonical 10 diverse benchmark prompts (`p01`–`p10`) spanning various themes and objectives. | When updating benchmark evaluation prompts. |
| **`bench/stress_prompts.json`** | Canonical 2 lethal stress prompts (`s01`–`s02`) engineered to test the repair loop. | When modifying repair loop stress evaluation prompts. |
| **`tests/test_game_ir.py`** | Unit tests for GameIR validation, schema bounds, and patch clamping. | When adding new GameIR fields or patch tests. |
| **`tests/test_jobs.py`** | Unit tests for SQLite job store, event store, and API route validation. | When updating job store or route unit tests. |
| **`tests/test_orchestrator.py`** | Integration tests for orchestrator state transitions, error mappings, and queue locking. | When changing orchestrator state machine logic. |
| **`tests/test_planner.py`** | Unit tests for prompt generation, few-shot examples, and markdown stripping. | When updating planner prompt tests. |
| **`tests/test_repair.py`** | Unit tests for repair prompt generation, patch validation, and no-op rejection. | When updating repair agent unit tests. |
| **`tests/test_openai_compat.py`**| Unit tests for OpenAI-compatible adapter, 429 quota inspection, and fallback chains. | When updating model provider tests. |
| **`tests/test_eval.py`** | Unit tests for the evaluation benchmark runner and metric aggregation. | When updating evaluation harness unit tests. |
| **`tests/test_bench_runner.py`** | Unit tests for benchmark prompt loading and execution isolation. | When updating benchmark suite tests. |
| **`tests/test_slow_player.py`** | Regression tests for slow player movement and early wall-reach exit. | When testing slow player velocity tolerances. |
| **`tests/test_mechanic_variety.py`**| 47 unit tests for the 5 enemy behaviors, 4 layouts, `defeat_enemies`, and `visual_overrides`. | When extending mechanic variety or layout logic. |

---

### 4.3 Frontend Files (`aether-frontend/src/`)

| File / Subfolder | What It Does | When You Would Touch It |
|---|---|---|
| `main.tsx` | React 19 application mounting point and DOM root binding. | Rarely; standard React bootstrap. |
| `App.tsx` | React Router route configuration (`/`, `/forge`, `/play/:game_id`, `/nexus`, `/vault`, `/auth`). | When registering new application routes or top-level navigation links. |
| `index.css` | Global Tailwind CSS imports, base styling, and custom scrollbar rules. | When altering global typography or base CSS styles. |
| `App.css` | Global utility classes, animations, and glow effects. | When modifying button styles or glassmorphic glow effects. |
| **`game/ArenaScene.ts`** | Core Phaser 3 Arcade physics game engine: player movement, 5 enemy AIs, 4 layouts, 5 themes, HUD, and QA hook. | When modifying gameplay physics, AI behaviors, layouts, visual themes, or QA hook APIs. |
| **`game/gameir.ts`** | TypeScript type definitions mirroring backend GameIR v1.0 schema. | When updating GameIR types to match backend schema updates. |
| **`game/qaHook.ts`** | TypeScript interfaces for `window.__AETHER_GAME__` and `GameState`. | When adding new inspection or simulation methods to the QA hook. |
| **`game/savedDemos.ts`** | Bundled offline generation artifacts (Spooky, Pirate, Repaired) for zero-API demonstration. | When updating pre-recorded offline demonstration artifacts. |
| `game/sample-*.json` | Static GameIR specifications for demo and test routes (`sample-gameir.json`, `sample-bouncer-pillars.json`, etc.). | When modifying default static demo parameters. |
| **`pages/Forge.tsx`** | Game synthesis laboratory UI: prompt input, timeline tracker, QA report drawer, and saved demo cards. | When improving generation UI, timeline visualization, or repair diff presentation. |
| **`pages/PlayGame.tsx`** | Canvas hosting page: fetches spec from API, resolves demo routes, and mounts `<GameCanvas>`. | When adding new demo routes, theme aliases, or canvas container styling. |
| `pages/Nexus.tsx` | Community showcase gallery displaying public games and play counts. | When editing community feed UI. |
| `pages/Vault.tsx` | User profile dashboard showing saved games and generation statistics. | When editing user library UI. |
| `pages/Auth.tsx` | User login and registration modal page. | When editing prototype authentication UI. |
| **`components/GameCanvas.tsx`** | React wrapper component that initializes, configures, and destroys the Phaser 3 `Game` instance. | When altering Phaser game configuration (renderer, dimensions, parent DOM node). |
| `components/GlassPanel.tsx` | Reusable glassmorphic UI container with frosted-glass backdrop filter. | When adjusting glass panel aesthetics. |
| `components/ManifestationCard.tsx`| Card component for displaying game blueprints in Nexus and Vault. | When modifying game card styling. |
| `components/ProfileModal.tsx` | User profile information and settings modal. | When editing user profile modal UI. |
| `components/Sidebar.tsx` | Collapsible left-hand navigation sidebar. | When updating sidebar links or icons. |
| `components/CommentsModal.tsx` | Modal for viewing and submitting user comments on games. | When editing social comments UI. |
| `components/SystemTerminal.tsx` | Decorative CRT terminal component displaying animated synthesis logs. | When editing terminal styling. |
| **`lib/apiClient.ts`** | Client API wrapper for real backend endpoints (`/api/v1/games`, `/spec`, `/qa`, `/events`, `/health`). | When adding new client-side API helper functions. |
| `lib/api.ts` | Legacy client API wrapper for 30% prototype endpoints. | Kept for backwards compatibility with legacy pages. |
| `lib/mockApi.ts` | Mock client API simulating backend responses when operating fully offline. | When editing client-side mock data. |
| `lib/supabase.ts` | Optional Supabase client configuration. | Unused in local capstone scope. |
| `lib/utils.ts` | Tailwind class merging utility (`clsx` + `tailwind-merge`). | Rarely; standard UI utility. |
| `store/store.ts` | Zustand store managing client-side authentication state and user profile. | When modifying auth state management. |
| `store/sidebarStore.ts` | Zustand store managing sidebar expanded/collapsed state. | When modifying sidebar state. |

---

### 4.4 Scripts Directory (`scripts/`)

| Script Name | What It Does | When You Would Touch It |
|---|---|---|
| **`start_all.ps1`** | One-click PowerShell launcher: starts backend on 8000, Vite on 5173, displays model banner, opens browser to `/forge`. Pass `-Mock` for offline mode. | When altering launcher startup logic, port defaults, or banner formatting. |
| **`stop_all.ps1`** | Clean PowerShell terminator: identifies and kills processes listening on ports 8000 and 5173. | When updating cleanup logic or port lists. |
| **`run_real_eval.ps1`** | Standalone benchmark runner: manages Vite lifecycle, disables fallbacks, runs 12 prompts, archives to `docs/eval/`, updates `EVAL_RESULTS.md`. | When modifying standalone benchmark execution parameters. |
| **`demo_check.py`** | Environment health checker: validates Python venv, Node dependencies, backend `/health`, and API key presence without printing secrets. | When adding pre-demo environment checks. |
| **`run_qa_all.py`** | Playwright QA runner that executes all 17 checks against the 4 baseline demo routes (`/demo`, `/demo-survive`, `/demo-melee`, `/demo-avoid`). | When validating baseline QA check compliance. |
| **`run_variety_qa.py`** | Playwright QA runner that executes all 17 checks against the 5 mechanic variety demo routes. | When validating variety demo compliance. |
| **`run_qa_fixtures.py`** | Playwright runner that tests 3 known-broken fixtures (`restart_keeps_hp`, `no_win`, `demo-too-hard`) to verify failure detection. | When adding new deliberate failure fixtures. |
| **`e2e_smoke.py`** | End-to-end smoke verification script: starts servers, submits prompt, waits for `READY`, runs browser QA, captures screenshot. | When verifying full-pipeline health from the command line. |
| **`repair_demo.py`** | Demonstrates the self-repair loop: submits lethal spec, verifies Attempt 1 FAIL, verifies patch application, verifies Attempt 2 PASS. | When demonstrating or testing the repair loop in isolation. |
| **`run_eval.py`** | Core evaluation harness that runs canonical benchmark prompts against real or mock models with configurable delays and timeouts. | When adding evaluation metrics or modifying benchmark execution logic. |
| **`aggregate_eval_results.py`** | Aggregates raw JSON evaluation runs into comparative Markdown tables and updates `docs/EVAL_RESULTS.md`. | When modifying evaluation report formatting or metric calculations. |
| **`make_fallback.py`** | Bundles real evaluation artifacts into `aether-frontend/src/game/savedDemos.ts` for zero-API offline presentation. | When refreshing bundled offline demonstration artifacts. |
| **`api_walk.py`** | Acceptance test script that exercises all `/api/v1` endpoints and error codes in mock mode. | When verifying REST API contract compliance. |
| `check_movement.py` | Standalone diagnostic helper for measuring player movement speeds on a live canvas. | When debugging player velocity sampling issues. |
| `verify_slow_player_qa.py` | Diagnostic script verifying QA Check 6 wall-slide reachability on slow player speeds (100 px/s). | When testing slow player velocity regressions. |
| `verify_pipeline_e2e.py` | Pipeline verification script checking job transitions and SQLite records. | When debugging pipeline state persistence. |
| `run_planner_bench.py` | Lightweight planner-only benchmark evaluating prompt-to-GameIR synthesis without browser QA. | When testing model schema validity in isolation. |
| `try_planner.py` | CLI tool to send a single natural language prompt to the planner and print the resulting GameIR JSON. | When interactively testing planner prompt outputs. |
| `capture_theme_screenshots.py`| Helper script that captures high-resolution screenshots of all 5 themes. | When generating documentation theme visual assets. |
| `ui_smoke.py` | Headless Playwright script verifying that Forge and Play frontend pages mount without errors. | When testing frontend UI smoke regressions. |

---

### 4.5 Documentation Directory (`docs/`)

| Document Name | Primary Contents | When You Would Consult It |
|---|---|---|
| **`PROJECT_GUIDE.md`** | This document: authoritative, plain-language onboarding manual for the entire codebase. | When understanding, operating, testing, or extending any part of AETHER. |
| **`HANDOVER.md`** | Targeted handover summary for teammate Ayaan (Windows setup, routes catalog, ownership). | For quick setup commands and milestone summary. |
| **`HOW_TO_RUN.md`** | Step-by-step PowerShell operational guide for running, testing, and evaluating AETHER. | When copying exact terminal commands for daily development. |
| **`architecture.md`** | Formal system architecture, state machine specification, and data flow diagrams. | When studying the orchestrator state machine or concurrency model. |
| **`GameIR-v1.md`** | Formal specification of GameIR v1.0 JSON schema, allowed types, and patch limits. | When inspecting schema definitions or adding new GameIR attributes. |
| **`api-contract.md`** | REST API contract for `/api/v1` routes, payload examples, and error code taxonomy. | When integrating external clients or verifying endpoint responses. |
| **`QA_CHECKS.md`** | Comprehensive reference of all 17 Playwright checks, formulas, and patchability policy. | When investigating QA check failures or check implementation details. |
| **`QA_HOOK.md`** | Specification of `window.__AETHER_GAME__` test harness hook and security isolation. | When integrating automated test runners with the game canvas. |
| **`REPAIR_LOOP.md`** | Detailed specifications, empirical evidence, and diffs for the bounded self-repair loop. | When studying repair prompt engineering or patch application logic. |
| **`LIMITATIONS.md`** | Honest disclosure of engineering boundaries, single archetype scope, and rate limits. | When writing capstone reports or preparing viva limitation defenses. |
| **`EVAL_RESULTS.md`** | Comparative multi-model benchmark report across Run A, Run A2, and Run C. | When reviewing empirical accuracy, Playable@1/Playable@3 rates, or latencies. |
| **`FINAL_CHECKLIST.md`** | 60% milestone readiness audit and tracking of remaining human-dependent tasks. | When verifying milestone deliverables or assigning human rehearsal tasks. |
| **`MODULE_OWNERSHIP.md`** | Subsystem breakdown, blank ownership matrices, and 15 viva defense questions. | When preparing for capstone viva presentations and team role defense. |
| **`DECISIONS.md`** | Architectural Decision Records (ADRs) explaining key design choices (e.g. ADR-001). | When reviewing why specific architectural trade-offs were made. |
| **`DOCUMENT4_OUTLINE.md`** | Outline for Capstone Final Document 4 and artifact traceability matrix. | When writing the final capstone report narrative. |
| **`TEST_REPORT.md`** | Unified testing dashboard summarizing pytest, browser QA, and fixture detection passes. | When inspecting overall test suite coverage and pass rates. |
| **`PROGRESS.md`** | Phase-by-phase autonomous progress tracker recording commit hashes and dates. | When reviewing the chronological timeline of what was built. |
| **`MASTER_PLAN.md`** | Original engineering blueprint roadmap for the 60% milestone. | When referencing initial project milestone requirements. |
| **`CODEBASE_MAP.md`** | Historical gap analysis from Phase 0 when the project was at the 30% prototype stage. | When reviewing how the codebase evolved from prototype to 60%. |
| **`DEMO_RUNBOOK.md`** | Rehearsal guide and contingency procedures for live presentation demonstrations. | When preparing for live evaluation presentations. |

---

## 5. GameIR Reference (v1.0)

`GameIR v1.0` is the declarative intermediate representation schema defined in `aether-backend/schemas/game_ir.py` and validated in `aether-backend/services/validator.py`. Every field is strictly typed; unrecognized keys are rejected (`extra="forbid"`).

### 5.1 Complete Field & Type Reference

| Field Path | Type | Allowed Values / Ranges | Default | Runtime Action in `ArenaScene.ts` |
|---|---|---|:---:|---|
| `schema_version` | Literal | `"1.0"` | `"1.0"` | Identifies schema version for forward compatibility. |
| `title` | String | 1 to 50 characters | *Required* | Displayed in HUD banner, browser tab, and Forge timeline. |
| `genre` | Literal | Strictly `"arena_survival"` | *Required* | Enforces single supported gameplay archetype. |
| `premise` | String | 1 to 240 characters | *Required* | Displayed in HUD card and Forge summary. |
| `theme` | Enum | `"fantasy"`, `"sci_fi"`, `"pirate"`, `"spooky"`, `"cozy"` | *Required* | Selects background color, obstacle colors, player/enemy tints, and particle effects. |
| `arena_layout` | Enum | `"open"`, `"pillars"`, `"lanes"`, `"maze"` | `"open"` | Generates static obstacle geometry and collision boundaries. |
| `visual_overrides` | Object | Optional `VisualOverrides` model | `None` | Overrides geometric shapes, custom HUD labels, and accent colors. |
| `visual_overrides.player_label` | String | Max 24 characters | `None` | Replaces `"PLAYER"` in top-left HUD card. |
| `visual_overrides.enemy_label` | String | Max 24 characters | `None` | Replaces `"ENEMY"` in top-left HUD card. |
| `visual_overrides.collectible_label`| String | Max 24 characters | `None` | Replaces `"ITEM"` in top-left HUD card. |
| `visual_overrides.player_shape` | Enum | `"circle"`, `"square"`, `"triangle"`, `"diamond"` | `None` | Renders player using geometric primitive shape. |
| `visual_overrides.enemy_shape` | Enum | `"circle"`, `"square"`, `"triangle"`, `"diamond"` | `None` | Renders enemies using geometric primitive shape. |
| `visual_overrides.accent_hex` | String | Regex pattern `^#[0-9a-fA-F]{6}$` | `None` | Sets custom accent stroke color on player and HUD borders. |
| `player.move_speed` | Float | `100.0` to `300.0` px/s | *Required* | Sets Arcade physics maximum velocity (`playerBody.setVelocity`). |
| `player.max_health` | Integer | `1` to `10` hit points | *Required* | Sets starting and maximum HP (`currentHealth = maxHealth`). |
| `player.attack_mode` | Enum | `"avoid_only"`, `"melee"`, `"projectile"` | *Required* | Determines whether player can attack and which weapon spawns on `Space`. |
| `enemies` | List | 1 to 2 `EnemyConfig` items | *Required* | Spawns configured enemy groups in arena quadrants. |
| `enemies[i].type` | Enum | `"chaser"`, `"bouncer"`, `"patroller"`, `"dasher"`, `"shooter"` | *Required* | Assigns update tick behavior and collision physics. |
| `enemies[i].count` | Integer | `1` to `50` | *Required* | Number of enemies spawned for this type. |
| `enemies[i].speed` | Float | `20.0` to `250.0` px/s | *Required* | Base movement speed for this enemy type. |
| `collectibles` | List | 0 to 2 `CollectibleConfig` items | `[]` | Spawns collectible items randomly across arena floor. |
| `collectibles[i].type` | Enum | `"crystal"`, `"battery"`, `"coin"`, `"gem"`, `"star"` | *Required* | Determines visual rendering primitive and theme alignment. |
| `collectibles[i].count` | Integer | `0` to `50` | *Required* | Quantity of collectible items placed on floor. |
| `objective.type` | Enum | `"survive_seconds"`, `"collect_count"`, `"defeat_enemies"` | *Required* | Defines victory evaluation logic in game loop. |
| `objective.target` | Integer | Clamped by type (see below) | *Required* | Target threshold required to achieve status `'won'`. |
| `difficulty` | Integer | `1` to `5` | `2` | Informational difficulty rating shown on Forge badge. |
| `controls.movement` | String | 1 to 50 characters | `"WASD or arrow keys"` | Controls reminder text rendered in footer. |
| `controls.attack` | String | Max 50 characters (or `null`) | `"Space"` / `None` | Attack reminder text rendered in footer (`null` for `avoid_only`). |
| `seed` | Integer | Optional integer | `None` | Seeds Phaser's deterministic pseudorandom generator (`this.rng`). |

### 5.2 The 5 Enemy AI Behaviors (`ArenaScene.ts`)

Every frame in `ArenaScene.ts:update()`, enemy velocities are updated based on their assigned AI archetype:

1. **`chaser` (`ArenaScene.ts:1363-1373`)**:
   - Calculates angle directly between enemy $(x, y)$ and player $(x, y)$ using `Phaser.Math.Angle.Between()`.
   - Sets velocity vector straight toward player: $v_x = \cos(\theta) \cdot \text{speed}$, $v_y = \sin(\theta) \cdot \text{speed}$.
2. **`bouncer` (`ArenaScene.ts:1374-1391`)**:
   - Spawns with a random diagonal angle. Enables full restitution (`setBounce(1, 1)`).
   - Ricochets off arena boundary walls and static obstacle pillars.
   - Normalizes velocity vector each frame to prevent deceleration after collisions.
3. **`patroller` (`ArenaScene.ts:1392-1413`)**:
   - Constrained to linear oscillation along an assigned axis (`x` or `y`).
   - Moves at constant speed until colliding with an obstacle, wall, or reaching the arena padding boundary (28px), then reverses direction.
4. **`dasher` (`ArenaScene.ts:1414-1450`)**:
   - Implements a 3-state finite state machine:
     - *Stalking* (2400ms): Stalks player slowly at $0.4\times$ base speed.
     - *Wind-up* (400ms): Freezes in place ($v = 0$), flashes warning tint, locks `lungeAngle` toward player's current position.
     - *Lunging* (500ms): Accelerates forward in locked direction at $2.2\times$ base speed, then resets to stalking.
5. **`shooter` (`ArenaScene.ts:1451-1490`)**:
   - Maintains tactical standoff distance:
     - If distance $< 220\text{px}$: Retreats backward away from player at $0.8\times$ speed.
     - If distance $> 340\text{px}$: Closes distance toward player at $0.7\times$ speed.
     - If between 220px and 340px: Strafes perpendicular to player at $0.4\times$ speed.
   - Periodically fires avoidable projectile bullets (speed 220 px/s) toward player position every 2.0s.

### 5.3 The 4 Arena Layouts (`ArenaScene.ts:280-326`)

Obstacles are static physics bodies in `this.obstaclesGroup` that block player, enemy, and bullet movement:

1. **`open`**: Zero interior obstacles. Completely open $800 \times 600$ arena bounded by outer perimeter walls.
2. **`pillars`**: 4 symmetrical rectangular pillars ($60 \times 60\text{px}$) centered at $(220, 160)$, $(580, 160)$, $(220, 440)$, and $(580, 440)$. Provides cover against ranged shooters and creates bounce angles for bouncers.
3. **`lanes`**: 4 horizontal wall partitions ($260 \times 24\text{px}$) placed at $(190, 200)$, $(610, 200)$, $(190, 400)$, and $(610, 400)$. Leaves wide central and side corridors, creating tactical evasion lanes for patrollers.
4. **`maze`**: 8 interior wall segments forming corner pockets while leaving the central region open. Prevents dead-ends and ensures player is never trapped at spawn.

### 5.4 The 3 Objectives & Attack Modes

- **Objectives**:
  - `survive_seconds`: Target between 5 and 120 seconds. Counts down `survivalTimeRemaining`. Player wins when timer reaches 0.
  - `collect_count`: Target between 1 and 20 items. Collectibles scatter across arena floor. Player wins when items collected $\ge$ target.
  - `defeat_enemies`: Target between 1 and 30 enemies. Defeating an enemy increments `enemiesDefeated`. If total active enemies drops below 2, new enemies respawn until target is reached. Player wins when `enemiesDefeated` $\ge$ target.
- **Attack Modes**:
  - `avoid_only`: Player has no weapon. Space bar does nothing. Player must survive purely through dodging.
  - `melee`: Pressing Space swings a close-range curved energy arc around the player for 180ms, destroying any colliding enemies.
  - `projectile`: Pressing Space fires linear bullets in the player's current facing direction (bullet speed 450 px/s, cooldown 250ms).

### 5.5 The 5 Visual Themes (`ArenaScene.ts:20-117`)

Each theme defines curated colors, primitive shapes, and particles:

| Theme | Background Hex | Border / Obstacle Hex | Player Hex / Shape | Enemy Hex / Shape | Collectible Hex / Shape | HUD Accent |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`fantasy`** | `#0b0914` | `#6366f1` / `#a855f7` | `#4f46e5` (Square) | `#ef4444` (Square) | `#10b981` (Crystal) | `#818cf8` |
| **`sci_fi`** | `#050c14` | `#0284c7` / `#38bdf8` | `#0284c7` (Circle) | `#e11d48` (Circle) | `#10b981` (Battery) | `#06b6d4` |
| **`pirate`** | `#071524` | `#b45309` / `#f59e0b` | `#b91c1c` (Square) | `#57534e` (Square) | `#eab308` (Gold Coin)| `#f59e0b` |
| **`spooky`** | `#090610` | `#7c3aed` / `#a855f7` | `#4338ca` (Diamond)| `#059669` (Triangle)| `#c084fc` (Ghost Gem) | `#a855f7` |
| **`cozy`** | `#0f1715` | `#84cc16` / `#a3e635` | `#d97706` (Circle) | `#9f1239` (Circle) | `#fde047` (Star) | `#a3e635` |

### 5.6 Two Real Example GameIR Specifications

#### Example 1: Baseline Projectile Survival (`aether-frontend/src/game/sample-gameir.json`)
```json
{
  "schema_version": "1.0",
  "title": "Arcane Grove Survival",
  "genre": "arena_survival",
  "premise": "Defend the enchanted grove against corrupted woodland beasts.",
  "theme": "fantasy",
  "player": {
    "move_speed": 220.0,
    "max_health": 3,
    "attack_mode": "projectile"
  },
  "enemies": [
    {
      "type": "chaser",
      "count": 6,
      "speed": 85.0
    }
  ],
  "collectibles": [
    {
      "type": "crystal",
      "count": 8
    }
  ],
  "objective": {
    "type": "collect_count",
    "target": 8
  },
  "difficulty": 2,
  "controls": {
    "movement": "WASD or arrow keys",
    "attack": "Space"
  },
  "seed": 1337
}
```

#### Example 2: Mechanic Variety with Bouncers & Pillars (`aether-frontend/src/game/sample-bouncer-pillars.json`)
```json
{
  "schema_version": "1.0",
  "title": "Pinball Pillar Arena",
  "genre": "arena_survival",
  "premise": "Dodge high-speed ricocheting bouncers amidst solid pillars.",
  "theme": "sci_fi",
  "arena_layout": "pillars",
  "player": {
    "move_speed": 210.0,
    "max_health": 3,
    "attack_mode": "avoid_only"
  },
  "enemies": [
    {
      "type": "bouncer",
      "count": 4,
      "speed": 75.0
    }
  ],
  "collectibles": [
    {
      "type": "gem",
      "count": 10
    }
  ],
  "objective": {
    "type": "collect_count",
    "target": 8
  },
  "visual_overrides": {
    "player_label": "DRONE",
    "enemy_label": "BOUNCER",
    "collectible_label": "ENERGY",
    "player_shape": "square",
    "enemy_shape": "diamond",
    "accent_hex": "#06b6d4"
  },
  "difficulty": 3,
  "controls": {
    "movement": "WASD or arrow keys",
    "attack": null
  },
  "seed": 42
}
```

---

## 6. The 17 QA Checks & The QA Hook

Automated browser QA verification is implemented in `aether-backend/services/qa_runner.py` and executed via Playwright against the Phaser 3 client.

### 6.1 Master QA Checks Table

| # | Check Identifier (`id`) | Category | Description | Critical | Patchable |
|---|---|---|---|:---:|:---:|
| 1 | `canvas_visible` | Runtime / Engine | HTML `<canvas>` element exists in DOM, is visible, and has dimensions $> 0$. | **Yes** | **No** |
| 2 | `hook_ready` | Runtime / Engine | `window.__AETHER_GAME__.ready === true` and simulation `tick` increments steadily over 1.0s. | **Yes** | **No** |
| 3 | `no_page_errors` | Runtime / Engine | Page logged zero uncaught JavaScript exceptions or console errors during test execution. | **Yes** | **No** |
| 4 | `player_present` | Entity Sanity | Player entity exists in `getState()` with coordinates strictly within arena bounds ($0 < x < 800, 0 < y < 600$). | **Yes** | **No** |
| 5 | `player_moves` | Input & Physics | Holding down `d` key for 600ms produces measurable player displacement ($> 5.0\text{px}$). | **Yes** | **No** |
| 6 | `movement_speed_consistent` | Input & Physics | Straight velocity, diagonal velocity ($v / \sqrt{2}$), and wall-slide velocity match `player.move_speed` within $\pm 15\%$. | **Yes** | **No** |
| 7 | `attack_responds` | Combat Mechanic | Pressing `Space` increments `attacksPerformed` for melee/projectile, or produces no attack for `avoid_only`. | **Yes** | **No** |
| 8 | `hud_consistent` | UI & HUD | HUD strings for health and objective reflect active GameIR spec parameters. | **Yes** | **No** |
| 9 | `win_reachable` | Objective Loop | Reaching objective target transitions `getState().status` to `'won'`. | **Yes** | **No** |
| 10 | `no_actions_after_end` | State Machine | Space bar presses after game end (`status === 'won'`) are locked and do not trigger attacks. | **Yes** | **No** |
| 11 | `restart_resets_after_win` | State Isolation | Pressing `R` key while in `'won'` state resets HP to max, score to 0, status to `'playing'`, and clears debris. | **Yes** | **No** |
| 12 | `lose_reachable` | Damage & Loss | Applying lethal damage (`damagePlayer(maxHp)`) transitions `getState().status` to `'lost'`. | **Yes** | **No** |
| 13 | `restart_resets_after_lose` | State Isolation | Pressing `R` key while in `'lost'` state restores HP to `maxHp`, score to 0, and restores initial enemy counts. | **Yes** | **No** |
| 14 | `no_duplicate_enemies_after_restart` | Memory / Leaks | Restarting immediately after killing an enemy produces zero zombie respawn leaks after 4.0s. | **Yes** | **No** |
| 15 | `screenshot_captured` | Visual Proof | Playwright saves non-empty PNG screenshot of the active canvas to disk. | **Yes** | **No** |
| 16 | `idle_survival_min_seconds` | Spec Playability | With enemies active and zero player input, player survives at least 3.0s without dying. | **Yes** | **Yes** |
| 17 | `flee_bot_survives` | Spec Playability | An automated evasion bot steering away from nearest threats survives for `min(12.0s, objective_target)`. | **Yes** | **Yes** |

### 6.2 How the QA Hook Works (`qaHook.ts` & `ArenaScene.ts`)

When Playwright loads a game URL containing the query parameter `?test=1` (`http://localhost:5173/play/{id}?test=1`), `ArenaScene.ts` attaches the test interface `window.__AETHER_GAME__`:

```typescript
// Exposed methods on window.__AETHER_GAME__ (qaHook.ts):
interface AetherGameHook {
  ready: boolean;                             // True when game assets loaded and physics running
  tick: number;                              // Increments every frame
  getState: () => GameState;                 // Snapshot of hp, score, status, player x/y, counts, hud text
  advanceTimer: (seconds: number) => void;   // Adds seconds to survival timer
  simulatePickup: () => void;                // Simulates item collection or enemy defeat
  damagePlayer: (n: number) => void;         // Directly inflicts damage to test loss state
  getEnemyPositions: () => EnemyPosition[];  // Returns array of {x, y} coordinates for flee-bot
  pauseEnemies: (paused: boolean) => void;   // Pauses enemy AI during velocity calibration
}
```

- **Security & Performance Isolation**: In production (without `?test=1`), this hook is completely inactive, preventing cheat injection or memory leaks during normal gameplay.

### 6.3 What the 17 QA Checks Do NOT Prove

1. **Not Proof of Fun or Compelling Game Feel**:
   - The checks prove *mechanical reachability* (canvas renders, inputs register, velocities are accurate within $\pm 15\%$, win/loss triggers, and player does not die instantaneously).
   - They do **not** evaluate subjective fun, juice, screen shake, compelling narrative, aesthetic pleasure, or replayability.
2. **Defeat Enemies Reachability Uses Instrumented Hook**:
   - For `objective.type === 'defeat_enemies'`, Check 8 (`win_reachable`) calls `window.__AETHER_GAME__.simulatePickup()` up to the target number of times to prove that the engine transitions to `'won'` upon reaching the kill quota.
   - It does **not** deploy a dynamic human-aimbot AI that navigates the arena and shoots moving targets in real time. Full beatability by a human player remains a subjective gameplay attribute.

---

## 7. The Bounded Self-Repair Loop

Implemented in `aether-backend/services/repair.py` and managed by `aether-backend/services/orchestrator.py`.

### 7.1 Allowed `GameIRPatch` Fields & Ranges

The repair agent can **only** tune numeric attributes. Arbitrary keys are rejected (`extra="forbid"`):

| Patch Field | Type | Allowed Boundary | Description |
|---|:---:|:---:|---|
| `player_move_speed` | Float | `100.0` to `300.0` px/s | Increases player speed to outrun pursuers. |
| `player_max_health` | Integer | `1` to `10` hit points | Increases health pool to absorb chip damage. |
| `enemy_speed_multiplier` | Float | `0.1` to `2.0` | Multiplies enemy speeds (clamped to `[20.0, 250.0]` px/s). |
| `enemy_count` | Integer | `1` to `50` | Lowers crowding and attack density. |
| `objective_target` | Integer | Clamped by objective type | Reduces survival duration or collection count. |
| `difficulty` | Integer | `1` to `5` | Updates display difficulty rating. |
| `rationale` | String | String explanation | Documents why changes resolve the measured failure. |

### 7.2 Strict Rules & What Is NEVER Repaired

1. **Hard Attempt Cap**: Maximum of 2 repairs (= 3 test attempts maximum). If the game still fails after Attempt 3, the job terminates as `FAILED` with error code `REPAIR_LIMIT_REACHED`.
2. **Non-Patchable Failures Fast-Fail**: If ANY non-patchable check fails (such as `canvas_visible`, `player_moves`, or `restart_resets_after_win`), the repair loop is **never** invoked. The job immediately terminates as `FAILED` (`QA_FAILED`).
3. **No-Op Rejection**: The repair agent must propose at least one numeric change that actually alters the spec. If the diff is empty, the patch is rejected and one model retry is granted.
4. **Forbidden Mutability**: The repair loop **cannot** change `theme`, `title`, `premise`, `genre`, `objective.type`, `attack_mode`, `collectibles`, `arena_layout`, or write code.

### 7.3 Real Before/After Repair Example (Stress Prompt `s01`)

From evaluation artifact `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json` (Run A2):

- **Prompt (`s01`)**: *"an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point"*
- **Initial Spec (Attempt 1 — FAIL)**:
  - `player.move_speed`: `150.0` px/s
  - `player.max_health`: `1` HP
  - `enemies[0].count`: `50`
  - `enemies[0].speed`: `250.0` px/s
  - *QA Result*: Attempt 1 failed patchable checks:
    - `idle_survival_min_seconds`: Survived **0.27s** ($< 3.0\text{s}$ required) -> **FAIL**
    - `flee_bot_survives`: Survived **0.45s** ($< 12.0\text{s}$ required) -> **FAIL**
- **Repair Agent Action**:
  - *Diagnosis*: Player is overwhelmed instantly by 50 fast enemies ($250\text{ px/s} > 150\text{ px/s}$) with only 1 HP.
  - *Rationale*: `"Decreased enemy count to 8 and speed multiplier to 0.4 while increasing player move speed to 280.0 and max health to 8, allowing player to outrun enemies and exceed survival thresholds."`
- **Patched Spec (Attempt 2 — PASS)**:
  - `player.move_speed`: `280.0` px/s (Diff: $+130.0$)
  - `player.max_health`: `8` HP (Diff: $+7$)
  - `enemies[0].count`: `8` (Diff: $-42$)
  - `enemies[0].speed`: `100.0` px/s (Diff: $-150.0$)
  - *QA Result*: Attempt 2 passed all 17 checks:
    - `idle_survival_min_seconds`: Survived **3.00s** -> **PASS**
    - `flee_bot_survives`: Survived **12.02s** -> **PASS**
    - Job transitioned to **`READY`** in 63.5s.

---

## 8. REST API Reference (`/api/v1`)

Base URL: `http://localhost:8000/api/v1` (CORS configured for `http://localhost:5173`). Defined in `aether-backend/routes/games_v1.py`.

### 8.1 Endpoints

#### 1. Submit Generation Request
- **Method / Path**: `POST /api/v1/games`
- **Status Code**: `202 Accepted`
- **Request Body**:
  ```json
  {
    "prompt": "a cybernetic ninja dodging laser drones in a neon rooftop arena"
  }
  ```
- **Response (`202 Accepted`)**:
  ```json
  {
    "id": "7b0b69fb-13c5-430c-96b6-3c0516ca8371",
    "status": "QUEUED"
  }
  ```
- **Error**: `400 Bad Request` if prompt is empty or $> 1200$ characters (`PROMPT_INVALID`).

#### 2. Get Game Status & Summary
- **Method / Path**: `GET /api/v1/games/{id}`
- **Response (`200 OK`)**:
  ```json
  {
    "id": "7b0b69fb-13c5-430c-96b6-3c0516ca8371",
    "prompt": "a cybernetic ninja dodging laser drones in a neon rooftop arena",
    "status": "READY",
    "stage": "TESTING",
    "attempt": 1,
    "max_attempts": 3,
    "created_at": 1728901200.0,
    "updated_at": 1728901245.0,
    "game_url": "http://localhost:5173/play/7b0b69fb-13c5-430c-96b6-3c0516ca8371",
    "qa_summary": {
      "passed": ["canvas_visible", "hook_ready", "player_present", "player_moves", "..."],
      "failed": [],
      "critical_failed": []
    },
    "limitations": ["Adapted 3D rooftop into 2D top-down arena survival."],
    "error_code": null,
    "error_message": null
  }
  ```
- **Error**: `404 Not Found` (`GAME_NOT_FOUND`).

#### 3. Get Validated GameIR Specification
- **Method / Path**: `GET /api/v1/games/{id}/spec`
- **Response (`200 OK`)**: Complete `GameIR` JSON document.
- **Error**: `404 Not Found` if job does not exist or spec is not yet validated (`SPEC_UNSUPPORTED`).

#### 4. Get Latest QA Report
- **Method / Path**: `GET /api/v1/games/{id}/qa`
- **Response (`200 OK`)**:
  ```json
  {
    "url": "http://localhost:5173/play/7b0b69fb-13c5-430c-96b6-3c0516ca8371?test=1",
    "overall": "PASS",
    "checks": [
      {
        "id": "canvas_visible",
        "critical": true,
        "patchable": false,
        "passed": true,
        "message": ""
      },
      {
        "id": "idle_survival_min_seconds",
        "critical": true,
        "patchable": true,
        "passed": true,
        "message": ""
      }
    ],
    "page_errors": [],
    "screenshot_path": "artifacts/7b0b69fb-13c5-430c-96b6-3c0516ca8371/play_7b0b69fb-13c5-430c-96b6-3c0516ca8371.png",
    "repair_recommended": false
  }
  ```
- **Error**: `404 Not Found` if QA has not yet completed.

#### 5. Get Chronological Lifecycle Events Stream
- **Method / Path**: `GET /api/v1/games/{id}/events`
- **Response (`200 OK`)**:
  ```json
  [
    {
      "timestamp": 1728901201.2,
      "stage": "PLANNING",
      "result": "START",
      "detail": "Initiating model game planning",
      "attempt": 1
    },
    {
      "timestamp": 1728901218.5,
      "stage": "PLANNING",
      "result": "SUCCESS",
      "detail": "Specification generated by model ('Cyber Ninja')",
      "attempt": 1
    }
  ]
  ```

#### 6. Safe Whitelisted Artifact Download
- **Method / Path**: `GET /api/v1/games/{id}/artifacts/{name}`
- **Description**: Downloads verified generation artifacts.
- **Whitelisted Names**: `game_ir_v1.json`, `game_ir_v2.json`, `game_ir_v3.json`, `qa_report_attempt_1.json`, `qa_report_attempt_2.json`, `qa_report_attempt_3.json`, `agent_trace.jsonl`, `screenshot.png`, `qa_screenshot.png`, and `*.png` filenames matching `^[a-zA-Z0-9_\-\.]+\.png$`.
- **Errors**:
  - `400 Bad Request`: Invalid UUID format.
  - `403 Forbidden`: Artifact name is not on the whitelist.
  - `404 Not Found`: File does not exist on disk.

#### 7. System Health Check
- **Method / Path**: `GET /api/v1/health`
- **Description**: Returns system status, active model, and key status. **Never exposes secrets or API keys**.
- **Response (`200 OK`)**:
  ```json
  {
    "status": "ok",
    "provider": "openai_compat",
    "model": "gemini-3.5-flash-lite",
    "key_configured": true
  }
  ```

### 8.2 Standardized Error Codes Registry

| Error Code | HTTP Status | Description & Root Cause |
|---|:---:|---|
| `PROMPT_INVALID` | `400` | User prompt was empty, whitespace-only, or exceeded 1200 characters. |
| `MODEL_TIMEOUT` | `504` | Model provider failed to respond within `MODEL_TIMEOUT_SECONDS` (default 60s). |
| `MODEL_HTTP_ERROR` | `502` | Upstream provider returned HTTP 5xx or unresolvable 429 after retries & fallback exhaustion. |
| `MODEL_OUTPUT_INVALID` | `422` | Output was invalid JSON or failed Pydantic validation after 2 retries. |
| `SPEC_UNSUPPORTED` | `422` | Spec requested unsupported mechanics outside 60% GameIR boundary. |
| `QA_CRASHED` | `500` | Headless Playwright subprocess crashed, timed out (>180s), or threw an unexpected exception. |
| `QA_FAILED` | `422` | Critical non-patchable check failed (e.g. canvas stalled, restart broke). |
| `REPAIR_LIMIT_REACHED` | `422` | Spec remained unplayable after maximum allowed repair iterations (2 repairs = 3 tests). |
| `GAME_NOT_FOUND` | `404` | Requested `game_id` was not found in SQLite store. |
| `INTERNAL_ERROR` | `500` | Backend restarted while job was in-flight, or uncaught server exception. |

---

## 9. Environment Configuration (`.env`)

Configuration is managed via `aether-backend/.env` (parsed by `python-dotenv` and `os.getenv`). A template is provided at `aether-backend/.env.example`.

### 9.1 Environment Variables Reference

| Variable Name | Purpose & Meaning | Default Value | Example Value |
|---|---|:---:|---|
| `MODEL_PROVIDER` | Active model provider adapter (`mock` or `openai_compat`). | `"mock"` | `"openai_compat"` |
| `MODEL_API_KEY` | Google AI Studio Gemini API key. Secret: never commit to git. | `""` | `"AIzaSyD-..."` |
| `MODEL_BASE_URL` | Base URL for the OpenAI-compatible `/chat/completions` endpoint. | Gemini endpoint | `"https://generativelanguage.googleapis.com/v1beta/openai/"` |
| `MODEL_NAME` | Primary model identifier sent in completion payload. | `"gemini-3.5-flash-lite"` | `"gemini-3.5-flash-lite"` |
| `MODEL_FALLBACKS` | Comma-separated list of fallback models on HTTP 429 quota exhaustion. | 4 Gemini models | `"gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite"` |
| `MODEL_TIMEOUT_SECONDS`| Network timeout for model requests in seconds. | `60.0` | `60.0` |
| `AETHER_PYTHON` | Optional path to custom Python executable (avoids path issues). | System default | `"path/to/venv/Scripts/python.exe"` |
| `AETHER_ARTIFACTS_DIR` | Optional custom directory for job artifact files. | `aether-backend/artifacts` | `"aether-backend/artifacts"` |

### 9.2 Getting Your Own Gemini API Key from Google AI Studio

1. Navigate to [Google AI Studio](https://aistudio.google.com/) in your browser.
2. Sign in with your Google account.
3. Click **Get API key** in the left sidebar navigation.
4. Click **Create API key** and select a Google Cloud project.
5. Copy the generated key (starts with `AIzaSy...`).
6. Paste the key into `aether-backend/.env`:
   ```dotenv
   MODEL_API_KEY=AIzaSyYourGeneratedKeyHere
   ```
7. **Security Warning**: Never share your key, never print it in terminal outputs, and never commit `.env` to git (it is protected by `.gitignore`).

### 9.3 Model Fallback Chain Behavior

The fallback chain is implemented in `aether-backend/providers/openai_compat.py`:
- When a model request returns an HTTP 429 quota exhaustion or exhausts retryable 503/timeout attempts, the provider inspects the response.
- If quota is exhausted or rate limit persists, `_trigger_fallback()` switches to the next model in `MODEL_FALLBACKS`.
- The new active model is cached at the process level (`_PROCESS_ACTIVE_MODEL`) so subsequent requests in the same process do not repeat the failed model call.
- To disable fallbacks (e.g. during isolated benchmark runs), set `MODEL_FALLBACKS=` (which `scripts/run_real_eval.ps1` does automatically).

> [!WARNING]
> **Free-Tier Quota & Rate Limit Notice**: Google AI Studio free-tier accounts enforce strict rate limits (typically 15 Requests Per Minute for Flash models). Upstream quotas and availability change dynamically without notice. Always use inter-prompt delays (5s–13s) during evaluations to avoid triggering HTTP 429 errors.

---

## 10. Windows Setup from a Fresh Clone (Step by Step)

Follow these exact steps in Windows PowerShell to set up a clean, working environment:

### Step 1: Clone Repository
```powershell
git clone <repository_url>
cd AETHER_V3
```
*Expected Output*: Git clones objects and creates working tree on branch `main`.

### Step 2: Set Up Backend Virtual Environment
```powershell
cd aether-backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*Expected Output*: PowerShell prompt displays `(venv)`.

### Step 3: Install Backend Dependencies
```powershell
pip install -r requirements.txt
```
*Expected Output*: Successfully installed `fastapi`, `uvicorn`, `pydantic`, `httpx`, `playwright`, `pytest`.

### Step 4: Install Playwright Chromium Browser
```powershell
playwright install chromium
```
*Expected Output*: Downloads and installs Chromium headless browser binaries.

### Step 5: Install Frontend Dependencies
```powershell
cd ..\aether-frontend
npm ci
cd ..
```
*Expected Output*: Node packages installed cleanly from `package-lock.json` with zero errors.

### Step 6: Configure Environment File
```powershell
copy .\aether-backend\.env.example .\aether-backend\.env
```
*Expected Output*: `1 file(s) copied.` Open `.env` and add your `MODEL_API_KEY`.

### Step 7: Verify Environment Health
```powershell
.\aether-backend\venv\Scripts\python.exe scripts\demo_check.py
```
*Expected Output*:
```
============================================================
             AETHER PRE-DEMO VERIFICATION SUITE             
============================================================
[1/5] Checking Provider & Model Configuration... OK
[2/5] Checking Backend Health... (warn if stopped, pass if running)
[3/5] Checking Frontend Accessibility... OK
[4/5] Checking Offline Fallback Demos & GameIR Schema... PASS
============================================================
  RESULT: DEMO ENVIRONMENT READY
============================================================
```

---

## 11. How to Generate Games as a User

### 11.1 Mock Mode vs. Live Mode

- **Mock Mode (Offline / Zero API Calls)**:
  - Command: `.\scripts\start_all.ps1 -Mock`
  - Sets `MODEL_PROVIDER=mock`.
  - Uses `MockModelProvider` (`providers/mock.py`).
  - Returns deterministic, instant GameIR specs matching prompt keywords.
  - Takes $\sim 23\text{s}$ total (dominated by Playwright's 15s survival margin test).
- **Live Mode (Real Gemini Synthesis)**:
  - Command: `.\scripts\start_all.ps1`
  - Uses `aether-backend/.env` with your real Google AI Studio Gemini API key.
  - Calls Gemini 3.5 Flash Lite via OpenAI-compatible endpoint.
  - Takes $\sim 45\text{s}$ total (median end-to-end latency 45.8s in Run A `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` and 47,020.5 ms in Run D `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`; planner-only median was 17.3s with gemini-3.8-flash in Phase 0 bench `docs/eval/planner_gemini-3.8-flash_benchmark.json`). If repair is triggered, Run A2 median was $\sim 75.3\text{s}$ (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`).

### 11.2 What to Type: Example Prompts

Type any natural language game premise into the Forge prompt box:
- *"a spooky wizard collecting glowing crystals in a dark crypt while ghosts chase"*
- *"a cybernetic ninja dodging security laser drones and collecting energy cells"*
- *"a pirate captain collecting gold doubloons in a cove while skeleton ships pursue"*
- *"repair demo: an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point"* (triggers the repair loop).

### 11.3 What Each Timeline Stage Means

1. **`QUEUED`**: Prompt is queued in SQLite; waiting for worker lock.
2. **`PLANNING`**: Model is generating JSON specification.
3. **`VALIDATING_SPEC`**: Pydantic schema validation and safety regex checks running.
4. **`BUILDING`**: Spec mapped to runtime URL and stored in SQLite.
5. **`TESTING`**: Playwright headless browser executing 17 QA checks.
6. **`REPAIRING`** *(conditional)*: Playability failed; repair agent applying numeric patch.
7. **`READY`**: All checks passed! Game is ready to play.

### 11.4 Where Artifacts Are Saved

All generation artifacts are saved under `aether-backend/artifacts/{game_id}/`:
- `game_ir_v1.json`: Initial validated GameIR specification.
- `game_ir_v2.json`: Patched GameIR specification (if repair occurred).
- `qa_report_attempt_1.json`: Complete 17-check Playwright test report for Attempt 1.
- `qa_report_attempt_2.json`: Test report for Attempt 2 (if repair occurred).
- `play_{game_id}.png`: Full-resolution PNG screenshot captured by Playwright.
- `agent_trace.jsonl`: Chronological audit log with timestamps, latency, and model fallbacks.

### 11.5 Replaying a Saved Demo (Zero API Calls)

To demonstrate the system instantly with zero API calls and the backend stopped:
1. Start frontend (`cd aether-frontend; npm run dev`).
2. Open `http://localhost:5173/forge`.
3. Click any button under **Load saved demo** (badge: **Saved result (offline demo)**):
   - **Spooky Crystal Dungeon** (`gemini-3.5-flash-lite Run A p01`)
   - **Pirate Cove Treasure Hunt** (`gemini-3.5-flash-lite Run A p03`)
   - **Shadow Pursuit (Repaired)** (`gemini-3.5-flash-lite Run A2 s01 repaired`)
4. The full timeline, GameIR spec, QA checks, and Launch button populate instantly from `savedDemos.ts`.

### 11.6 Complete Catalog of Demo & Theme Routes

Open directly in your browser with frontend running on `http://localhost:5173`:

- **Baseline Archetypes**:
  - `/play/demo` — Projectile attack with chaser enemies.
  - `/play/demo-survive` — Timed survival objective (survive 30s).
  - `/play/demo-melee` — Melee arc sweep attack demo.
  - `/play/demo-avoid` — Pacifist avoid-only survival demo.
- **5 Mechanic Variety Demos**:
  - `/play/demo-bouncer-pillars` — Bouncer AI (diagonal ricochet) + 4 pillar obstacles.
  - `/play/demo-patrol-lanes` — Patroller AI (horizontal lane oscillation) + horizontal partition wall lanes, avoid-only movement, collect 8 berries objective.
  - `/play/demo-dasher-defeat` — Dasher AI (stalk, wind-up, lunge) + defeat_enemies objective.
  - `/play/demo-shooter-pillars` — Shooter AI (standoff distance, bullets) + pillars layout.
  - `/play/demo-maze-collect` — Maze layout with safe central corridors + crystal collection.
- **Visual Themes**:
  - `/play/theme-fantasy` — Arcane Crystal Grove (purple/gold palette).
  - `/play/theme-sci-fi` — Cyber Void Surge (cyan/neon palette).
  - `/play/theme-pirate` — Treasure Cove Hunt (emerald/gold palette).
  - `/play/theme-spooky` — Spooky Crypt Haunt (green/purple palette).
  - `/play/theme-cozy` — Enchanted Meadow Gathering (warm amber palette).
- **Offline Fallbacks**:
  - `/play/fallback-spooky`, `/play/fallback-pirate`, `/play/fallback-repaired`.
- **Test Fixture**:
  - `/play/demo-too-hard` — Deliberately lethal fixture (12 enemies @ 240 px/s, 1 HP) that fails QA.

---

## 12. How to Run Tests, QA Scripts & Evaluations

### 12.1 Backend Pytest Suite (137 Tests)
```powershell
# From repository root:
.\aether-backend\venv\Scripts\python.exe -m pytest aether-backend\tests -v
```
*Expected Result*: `137 passed in ~28s`. Covers schemas, validators, jobs, orchestrator, repair agent, fallback chains, evaluation harnesses, and 47 mechanic variety tests.

### 12.2 Frontend Linting & Production Build
```powershell
cd aether-frontend
npm run lint          # Runs ESLint across all TypeScript files (0 errors)
npx tsc --noEmit      # Runs strict TypeScript type checking (0 errors)
npm run build         # Produces optimized production bundle in dist/ (~19s)
cd ..
```

### 12.3 Automated Browser QA Scripts
```powershell
# Run 17 checks on 4 baseline demo modes:
.\aether-backend\venv\Scripts\python.exe scripts\run_qa_all.py

# Run 17 checks on 5 mechanic variety modes:
.\aether-backend\venv\Scripts\python.exe scripts\run_variety_qa.py

# Test detection on 3 deliberate failure fixtures:
.\aether-backend\venv\Scripts\python.exe scripts\run_qa_fixtures.py
```
*Expected Result*: Baseline passes 4/4 (17/17 checks); Variety passes 5/5 (17/17 checks); Fixtures correctly detects and rejects all 3 seeded bugs (`restart_keeps_hp`, `no_win`, `demo-too-hard`).

### 12.4 Pipeline Smoke Test & Repair Demo
```powershell
# End-to-end smoke verification:
.\aether-backend\venv\Scripts\python.exe scripts\e2e_smoke.py

# Bounded repair loop demonstration:
.\aether-backend\venv\Scripts\python.exe scripts\repair_demo.py
```

### 12.5 Full Benchmark Evaluation (`run_real_eval.ps1`)
```powershell
# Run mock evaluation benchmark:
.\scripts\run_real_eval.ps1 -Mock

# Run live benchmark evaluation with Gemini 3.5 Flash Lite:
.\scripts\run_real_eval.ps1 -ModelId "gemini-3.5-flash-lite" -Delay 5.0 -MaxRequests 60
```

### 12.6 Reading Evaluation Results (`docs/EVAL_RESULTS.md`)
Open `docs/EVAL_RESULTS.md` to review the empirical benchmark results across evaluation runs:

- **Run A Baseline Engine (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`)**:
  - 12/12 prompts completed, 14 model requests, median latency 45,807.6 ms.
  - First-Response Schema Validity: **11/12 (91.7%)** (`s02` failed Pydantic validation).
  - Playable@1: **9/12 (75.0%)**; Playable@3: **9/12 (75.0%)**.
  - Repair Success: **0/2 (0.0%)** (`p06`, `s01` failed repair; `s02` skipped due to schema failure).

- **Run A2 Repair Prompt Tuning (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`)**:
  - Re-run of 3 dev stress prompts (`p06`, `s01`, `s02`) after tuning the repair prompt; 7 model requests, median latency 75,266.5 ms.
  - Playable@1: **0/3 (0.0%)**; Playable@3: **2/3 (66.7%)**.
  - Repair Success: **2/2 (100.0%)** (`s01`, `s02` repaired to READY; `p06` was not repaired).

- **Run D Upgraded Engine (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`)**:
  - 12/12 prompts completed, 18 model requests, median latency **47,020.5 ms**.
  - First-Response Schema Validity: **12/12 (100.0%)**.
  - Playable@1: **9/12 (75.0%)**; Playable@3: **12/12 (100.0%)**.
  - Repair Success: **3/3 (100.0%)** (`p06`, `s01`, `s02` repaired to READY).

- **Evaluation Caveats and Analysis Context**:
  - Playable@1 equals Run A (9/12).
  - `p06`, `s01`, and `s02` failed first in Runs A, A2, and D and were also the cases used to tune the QA check and repair prompt, so Run D is a development-set result, not a held-out estimate.
  - One run per prompt, results can vary between runs.
  - Run D prompts are the same 12 as Run A and do not measure the new enemy types and layouts.
  - The engine, QA runner, and repair prompt differ from Run A, so the comparison is not single-variable.

---

## 13. Extension Guide (Numbered Recipes)

Follow these exact step-by-step recipes to extend the system:

### Recipe 1: Add a New Enemy Type (e.g. `splitter`)
1. **Schema (`aether-backend/schemas/game_ir.py`)**:
   - Add `"splitter"` to the `EnemyType` literal:
     ```python
     EnemyType = Literal["chaser", "bouncer", "patroller", "dasher", "shooter", "splitter"]
     ```
2. **Frontend Type (`aether-frontend/src/game/gameir.ts`)**:
   - Add `'splitter'` to the `EnemyType` union:
     ```typescript
     export type EnemyType = 'chaser' | 'bouncer' | 'patroller' | 'dasher' | 'shooter' | 'splitter';
     ```
3. **Planner Prompt (`aether-backend/services/planner.py`)**:
   - Add `"splitter"` to the allowed enemy type list in `build_planner_system_prompt()`.
4. **Phaser Engine Runtime (`aether-frontend/src/game/ArenaScene.ts`)**:
   - In `createEnemies()`, add spawn data initialization for `splitter`.
   - In `updateEnemies()`, implement movement logic (e.g. splits into 2 smaller enemies upon hit).
5. **Update Tests**:
   - Add a test case in `aether-backend/tests/test_game_ir.py` verifying `"splitter"` validates.
   - Run `pytest aether-backend/tests` and `npx tsc --noEmit`.

### Recipe 2: Add a New Arena Layout (e.g. `cross`)
1. **Schema (`aether-backend/schemas/game_ir.py`)**:
   - Add `"cross"` to `ArenaLayout`:
     ```python
     ArenaLayout = Literal["open", "pillars", "lanes", "maze", "cross"]
     ```
2. **Frontend Type (`aether-frontend/src/game/gameir.ts`)**:
   - Add `'cross'` to `ArenaLayout` union.
3. **Phaser Obstacle Builder (`aether-frontend/src/game/ArenaScene.ts:280`)**:
   - Add `else if (layout === 'cross')` block:
     ```typescript
     } else if (layout === 'cross') {
       const crossBars = [
         { x: 400, y: 300, w: 200, h: 24 },
         { x: 400, y: 300, w: 24, h: 200 },
       ];
       crossBars.forEach((seg) => {
         const wall = this.add.rectangle(seg.x, seg.y, seg.w, seg.h, theme.borderColor, 0.45);
         wall.setStrokeStyle(2, theme.borderAccent, 0.85);
         this.physics.add.existing(wall, true);
         this.obstaclesGroup.add(wall);
       });
     }
     ```
4. **Update Tests**:
   - Add test in `aether-backend/tests/test_mechanic_variety.py`.
   - Verify with `pytest aether-backend/tests`.

### Recipe 3: Add a New Visual Theme (e.g. `underwater`)
1. **Schema (`aether-backend/schemas/game_ir.py`)**:
   - Add `"underwater"` to `GameTheme`:
     ```python
     GameTheme = Literal["fantasy", "sci_fi", "pirate", "spooky", "cozy", "underwater"]
     ```
2. **Frontend Theme Palettes (`aether-frontend/src/game/ArenaScene.ts:20`)**:
   - Add `underwater` palette definition to `THEME_PALETTES`:
     ```typescript
     underwater: {
       name: 'underwater',
       bgColor: 0x031b29,
       borderColor: 0x0284c7,
       borderAccent: 0x38bdf8,
       playerColor: 0x06b6d4,
       playerAccent: 0x67e8f9,
       enemyColor: 0xec4899,
       enemyAccent: 0xf472b6,
       collectibleColor: 0x14b8a6,
       collectibleAccent: 0x5eead4,
       projectileColor: 0x38bdf8,
       projectileAccent: 0xe0f2fe,
       hudAccent: '#38bdf8',
       hudAccentNum: 0x38bdf8,
     },
     ```
3. **Route Resolver (`aether-frontend/src/pages/PlayGame.tsx:50`)**:
   - Add theme metadata in `themeMeta` map for route `/play/theme-underwater`.
4. **Update Tests**:
   - Add test in `test_game_ir.py`.
   - Run `pytest aether-backend/tests` and `npm run lint`.

### Recipe 4: Add a New Victory Objective (e.g. `reach_exit`)
1. **Schema (`aether-backend/schemas/game_ir.py`)**:
   - Add `"reach_exit"` to `ObjectiveType`. Add target validator in `ObjectiveConfig`.
2. **Validator (`aether-backend/services/validator.py`)**:
   - Add validation bounds (e.g. target always `1`).
3. **Phaser Game Engine (`aether-frontend/src/game/ArenaScene.ts`)**:
   - Spawn exit portal zone in `create()`.
   - Add overlap between player and exit portal:
     ```typescript
     this.physics.add.overlap(this.player, this.exitPortal, () => { this.handleWin(); });
     ```
4. **QA Runner (`aether-backend/services/qa_runner.py`)**:
   - In Check 8 (`win_reachable`), add simulation dispatch:
     ```python
     elif obj_type == "reach_exit":
         page.evaluate("() => window.__AETHER_GAME__.simulateExitReached()")
     ```
5. **QA Hook (`aether-frontend/src/game/qaHook.ts` & `ArenaScene.ts`)**:
   - Expose `simulateExitReached: () => void` on `window.__AETHER_GAME__`.
6. **Update Tests**:
   - Add unit tests in `test_game_ir.py` and `test_orchestrator.py`.

### Recipe 5: Add a New QA Check (e.g. Check 18: `obstacle_collision_blocks`)
1. **Documentation (`docs/QA_CHECKS.md`)**:
   - Document check ID `obstacle_collision_blocks`, description, critical status (`True`), and patchability (`False`).
2. **QA Runner (`aether-backend/services/qa_runner.py`)**:
   - In `run_qa()`, add Check 18:
     - Direct player into an obstacle pillar, verify coordinate displacement stops at obstacle boundary.
     - Call `record_check("obstacle_collision_blocks", passed, msg, patchable=False)`.
3. **Frontend QA Drawer (`aether-frontend/src/pages/Forge.tsx`)**:
   - Add display badge for Check 18.
4. **Update Tests**:
   - Verify that all demo routes pass Check 18 in `run_qa_all.py` and `run_variety_qa.py`.

### Recipe 6: Add a New Model Provider (e.g. Local Ollama)
1. **Provider Implementation (`aether-backend/providers/ollama_provider.py`)**:
   - Create class `OllamaProvider(ModelProvider)` implementing `plan()` and `repair()` via HTTP POST to `http://localhost:11434/api/generate`.
2. **Provider Factory (`aether-backend/providers/factory.py`)**:
   - In `get_provider()`, add branch:
     ```python
     elif provider_name == "ollama":
         from providers.ollama_provider import OllamaProvider
         return OllamaProvider()
     ```
3. **Environment Template (`aether-backend/.env.example`)**:
   - Document `MODEL_PROVIDER=ollama`.
4. **Update Tests**:
   - Add test in `aether-backend/tests/test_openai_compat.py` (or new test file `test_ollama.py`).

---

## 14. Troubleshooting Table

Built from real engineering challenges encountered during milestone development (recorded in `docs/PROGRESS.md`):

| Symptom | Root Cause | Exact Fix |
|---|---|---|
| **Port 8000 or 5173 busy (`EADDRINUSE` / socket error)** | Leftover background Python, Uvicorn, or Node processes holding file locks. | Run `powershell -ExecutionPolicy Bypass -File scripts\stop_all.ps1`. |
| **`npm : The term 'npm' is not recognized` on Windows** | Node.js is installed in `C:\Program Files\nodejs` but not on current session `$env:PATH`. | Run `$env:PATH = "C:\Program Files\nodejs;" + $env:PATH`. |
| **Playwright browser missing (`Executable doesn't exist`)** | Chromium browser binaries were not installed after creating venv. | Run `playwright install chromium` inside the active venv. |
| **HTTP 429 Quota Exhausted (`MODEL_HTTP_ERROR`)** | Google AI Studio free-tier 15 RPM limit exceeded. | Add cooldown delay in evaluation (`-Delay 13`), or configure `MODEL_FALLBACKS` in `.env`. |
| **Model Timeout (`MODEL_TIMEOUT` after 60s)** | Upstream Gemini endpoint timed out (Run C timed out in both attempts: `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` and `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`, cause not established). | Switch primary model to lightweight `MODEL_NAME=gemini-3.5-flash-lite`, or increase `MODEL_TIMEOUT_SECONDS=90.0`. |
| **Stale `.env` configuration** | Backend server already running and cached old environment variables in memory. | Stop servers with `scripts\stop_all.ps1` and restart with `scripts\start_all.ps1`. |
| **Python path errors with special characters in workspace path** | VS Code Python extension cannot parse special characters or symbols in folder paths. | Create a venv in a folder without special characters, and set `"python.defaultInterpreterPath": "path\\to\\clean\\venv\\Scripts\\python.exe"` in `.vscode/settings.json`. |
| **Mock vs. Live mode confusion** | Developer runs `start_all.ps1` expecting mock mode, but `.env` specifies `openai_compat`. | Check console banner upon startup. Pass `-Mock` switch explicitly: `.\scripts\start_all.ps1 -Mock`. |
| **Slow player movement QA timeout (>180s)** | Spec has player speed $\approx 100\text{ px/s}$, taking too long to hit arena wall in Check 6. | `qa_runner.py` includes dynamic approach timing and early-exit tolerance when within 22px of target wall. |
| **Empty HTTP 200 response from Gemini** | Upstream model returns HTTP 200 with empty choices content. | `providers/openai_compat.py` automatically retries once with higher `max_tokens=16384`. |

---

## 15. Glossary & 15 Likely Viva Defense Questions

### 15.1 Glossary

- **GameIR (Game Intermediate Representation)**: Declarative, strictly typed JSON schema (`v1.0`) defining game parameters (player, enemies, layouts, objectives, themes) without executable code.
- **Arena Survival**: The single gameplay archetype supported: 2D top-down survival on an 800x600 canvas with `free_2d` movement.
- **Playwright QA**: Automated headless browser testing executing 17 spec-level checks against the live Phaser game canvas.
- **Bounded Parameter Repair**: Automated repair loop that adjusts numeric attributes (speeds, counts, health) with a hard cap of 2 repairs (3 test runs).
- **Playable@1**: Percentage of games passing all 17 QA checks on the very first synthesis attempt without repair.
- **Playable@3**: Percentage of games passing all 17 QA checks within 3 attempts (including up to 2 repair iterations).
- **QA Hook (`window.__AETHER_GAME__`)**: JavaScript test harness hook mounted on `window` when `?test=1` is in the URL.
- **Model Fallback Chain**: Resilience mechanism that automatically cycles to backup LLMs (`MODEL_FALLBACKS`) upon encountering HTTP 429 quota exhaustion.
- **OpenAI-Compatible Adapter**: Generic HTTP provider targeting any endpoint implementing OpenAI's `/chat/completions` specification.
- **Seeded RNG**: Deterministic pseudorandom number generator (`Phaser.Math.RND`) seeded by `GameIR.seed` to ensure reproducible enemy spawns.

### 15.2 15 Likely Viva Questions & Short Grounded Answers

1. **Why did you use GameIR instead of asking the LLM to write JavaScript / Phaser code?**  
   *Answer*: LLMs hallucinate syntax and runtime bugs when generating raw code. GameIR is a declarative JSON contract validated by Pydantic that guarantees syntax validity and renders through our battle-tested Phaser engine (`services/validator.py`).
2. **How do you guarantee the synthesized game is actually playable?**  
   *Answer*: We launch a real headless Chromium browser via Playwright (`services/qa_runner.py`) and execute 17 automated checks verifying rendering, movement velocities ($\pm 15\%$), attack responses, win/loss reachability, and survival margins.
3. **Why are only 2 of the 17 QA checks patchable?**  
   *Answer*: Only `idle_survival_min_seconds` and `flee_bot_survives` are caused by unbalanced numeric parameters (enemy speed/count, player health). The other 15 checks test runtime code integrity (canvas crashes, input listeners, state resets), which cannot be repaired by tuning numbers (`docs/QA_CHECKS.md`).
4. **What happens if the LLM generates an impossible or lethal game?**  
   *Answer*: The browser QA runner detects that idle survival ($< 3.0\text{s}$) or flee survival ($< 12.0\text{s}$) failed. The orchestrator transitions to `REPAIRING`, and the repair agent applies a `GameIRPatch` to reduce enemy speeds/counts and boost player health (`services/repair.py`).
5. **What is the difference between Playable@1 and Playable@3?**  
   *Answer*: Playable@1 measures first-shot generation success (Run A: 75.0%). Playable@3 measures success after up to 2 automated repair iterations (Run A: 75.0%; Run A2 stress prompts: 100.0%) (`docs/EVAL_RESULTS.md`).
6. **How does the QA runner interact with the browser without human input?**  
   *Answer*: It navigates to the game URL with `?test=1`, which mounts `window.__AETHER_GAME__` (`ArenaScene.ts:993`). Playwright calls hook methods like `simulatePickup()`, `damagePlayer()`, and samples `getState()` directly from the running Phaser simulation.
7. **Why is the engine restricted to a single archetype (2D top-down arena survival)?**  
   *Answer*: Constraining the scope to arena survival enables automated smoke-check bounding of movement velocities, collision responses, and survival times. Attempting multiple genres at 60% leads to shallow, unverified prototypes (`docs/LIMITATIONS.md`).
8. **How does the system handle an out-of-domain prompt (e.g. "make a 3D racing game")?**  
   *Answer*: The planner honestly adapts the premise into an arena survival representation (e.g. dodging racing drones) and explicitly records this in the `limitations` list displayed in the UI (`services/orchestrator.py`).
9. **How does the model fallback chain work during API quota exhaustion?**  
   *Answer*: When an HTTP 429 quota exhaustion is detected, `openai_compat.py` cycles to the next model in `MODEL_FALLBACKS`, updates `_PROCESS_ACTIVE_MODEL`, and logs the event in `agent_trace.jsonl` and `/api/v1/health`.
10. **Why did Run C (Gemini 3.8 Flash) yield incomplete results compared to Run A (Gemini 3.5 Flash Lite)?**  
    *Answer*: Run C timed out in both attempts (documented in `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` where `p02` timed out after 121.9s, and `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json` where the preflight ping timed out at 60s); cause not established. In contrast, Run A (`gemini-3.5-flash-lite`, `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`) completed all 12 benchmark prompts with a median end-to-end latency of 45.8s, and Run D on the upgraded engine (`gemini-3.5-flash-lite`, `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`) completed all 12 with a median latency of 47,020.5 ms (planner-only median in Phase 0 benchmark with gemini-3.8-flash was 17.3s, `docs/eval/planner_gemini-3.8-flash_benchmark.json`).
11. **How does the frontend stay synchronized with backend job execution?**  
    *Answer*: The Forge page polls `GET /api/v1/games/{id}` and `/events` every 1.5 seconds (`Forge.tsx:startPolling()`), updating the timeline, QA badges, and spec drawer until a terminal status (`READY` or `FAILED`) is reached.
12. **Can the repair loop get stuck in an infinite loop?**  
    *Answer*: No. The orchestrator enforces a hard maximum of 2 repairs (`MAX_REPAIRS = 2`, max 3 test runs). Furthermore, no-op patches with empty diffs are rejected immediately (`services/repair.py`).
13. **How does the system ensure test-restart state isolation?**  
    *Answer*: QA Check 14 (`no_duplicate_enemies_after_restart`) kills an enemy, immediately restarts with `R`, and waits 4.0s (longer than the 3.0s respawn timer) to prove that pending respawn callbacks do not leak duplicate enemies across scenes (`services/qa_runner.py`).
14. **How does the offline demonstration work when the backend is completely turned off?**  
    *Answer*: Real generation artifacts were bundled into `aether-frontend/src/game/savedDemos.ts`. Clicking a saved demo card in Forge populates the timeline, validated spec, and Play button directly in React state with zero network calls (`scripts/make_fallback.py`).
15. **What are the engineering boundaries of this 60% milestone?**  
    *Answer*: The 60% milestone establishes the verified prompt-to-GameIR-to-QA-to-repair pipeline. Second genres, 3D graphics, platformer physics, raw code synthesis, and multiplayer networking are explicitly reserved for future work (`docs/LIMITATIONS.md`).

---

## 16. Known Limitations, Human Tasks & Inconsistencies

### 16.1 Known Engineering Limitations
Refer to `docs/LIMITATIONS.md` for exhaustive disclosures:
- Single gameplay genre (`arena_survival`) with `free_2d` movement on an 800x600 canvas.
- Bounded enemy AI: maximum 2 enemy types per spec; 5 deterministic AI behaviors.
- Parameter-only repair: cannot rewrite engine logic or synthesize new shaders/code.
- Mechanical sanity $\ne$ subjective fun: 17 checks verify sanity and reachability, not player enjoyment.
- Free-tier rate limits: requires inter-prompt delays (5s–13s) to prevent HTTP 429 quota exhaustion.

### 16.2 Remaining Human Tasks (From `docs/FINAL_CHECKLIST.md` Section 9)
These deliverables require physical human volunteers, displays, or team sign-off:

| # | Task Description | Designated Owner | Required Action |
|---|---|:---:|---|
| **9.1** | **Non-Programmer Usability Evaluation** | Owner: to be assigned by Zain and Ayaan | Conduct usability evaluation sessions with 3–5 non-programmer volunteers; record qualitative feedback on prompt clarity, error understandability, and gameplay feel. |
| **9.2** | **Hardware & Projector Display Rehearsal** | Owner: to be assigned by Zain and Ayaan | Connect evaluation laptop to the actual presentation display/projector; verify 800x600 canvas scaling, theme contrast, font readability, and audio/visual hardware compatibility. |
| **9.3** | **Offline Backup Screencast Video Recording** | Owner: to be assigned by Zain and Ayaan | Record high-definition backup screen capture showing Forge generation, stage transitions, repair drawer, and gameplay; store on local USB flash drive for offline demo contingency. |
| **9.4** | **Capstone Document 4 Narrative Writing** | Owner: to be assigned by Zain and Ayaan | Author full narrative prose chapters for Final Capstone Document 4 matching `docs/DOCUMENT4_OUTLINE.md`, populating all tables with empirical benchmark metrics. |
| **9.5** | **Final Remote GitHub Repository Push** | Done | Completed: GitHub remote push and submission release tag finalized. |

### 16.3 Ayaan's Separate QA Agent
Ayaan's QA agent is an external, independently developed subsystem and is **currently separate and not part of this repository**. Connecting it in the future will require establishing a formal REST API contract or shared JSON schema. AETHER makes no assumptions regarding its internal architecture.

### 16.4 Known Inconsistencies in the Repository

1. **QA Check Numbering in Comments vs. Documentation**:
   - In `docs/QA_CHECKS.md`, `hud_consistent` is listed as Check 8 and `win_reachable` as Check 9. In `services/qa_runner.py`, `hud_consistent` is commented as Check 7 and `win_reachable` as Check 8 due to how player movement checks were grouped in early code comments. Both total exactly 17 checks.
2. **Historical Pytest Counts in Legacy Docs**:
   - Earlier documentation (`docs/CODEBASE_MAP.md`, `docs/FINAL_CHECKLIST.md` line 112) recorded 88 or 89 tests. Phase 9 added `test_mechanic_variety.py` (47 new unit tests), bringing the actual passing count to 137 tests (`pytest aether-backend/tests`).
3. **Artifact Download Route HTTP Status Code**:
   - In `docs/api-contract.md` Section 2.6, unapproved artifact names were described as returning `400 Bad Request`. In actual backend code (`aether-backend/routes/games_v1.py` line 273), unapproved artifact names raise `HTTPException(status_code=403, detail="Requested artifact name is not permitted")`, while invalid UUIDs return 400.
4. **`defeat_enemies` QA Reachability Simulation**:
   - In `aether-backend/services/qa_runner.py` line 710, Check 8 (`win_reachable`) verifies the win transition for `defeat_enemies` by invoking the test hook `window.__AETHER_GAME__.simulatePickup()`, which increments `enemiesDefeated` and updates the HUD without simulating dynamic enemy aimbot combat.
