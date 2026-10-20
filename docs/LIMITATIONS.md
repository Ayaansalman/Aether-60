# AETHER System Limitations & Engineering Boundaries

This document provides an honest disclosure of the engineering boundaries, architectural constraints, and operational limitations of the AETHER Game Synthesis and Self-Repair Engine (60% Milestone).

---

## 1. Single Gameplay Archetype (`arena_survival`)

- **Scope**: The Phaser 3 client runtime and GameIR v1 schema strictly support a single core gameplay archetype: **2D top-down arena survival** in an 800x600 pixel bounding box with `free_2d` movement.
- **Excluded Movement & Genre Modes**:
  - No flappy/gravity movement modes or platformer physics.
  - No horizontal-lock or single-axis constraint modes (e.g. Space Invaders or Frogger horizontal locks).
  - No 3D rendering or open-world traversal.
  - No multiplayer networking.
- **Handling of Out-of-Domain Prompts**:
  - If a user prompt requests a 3D open-world game, platformer, racing game, or multiplayer RPG, the planner honestly states in limitations that 3D, gravity/platformer physics, and multiplayer are not supported and adapts the premise into an arena survival representation (e.g. survival racing against drone pursuers in a 2D arena).
  - The system explicitly records and displays this limitation in the Forge UI (`limitations` list).
  - Second genres are explicitly out of scope for the 60% milestone.

---

## 2. Enemy AI Behaviors and Constraints

- **Supported AI Archetypes**: The runtime supports 5 deterministic enemy AI behaviors:
  - `chaser`: Direct pursuit toward player coordinates.
  - `bouncer`: Constant diagonal velocity with obstacle/wall ricochet.
  - `patroller`: Lane-constrained linear oscillation.
  - `dasher`: Stalking, wind-up freeze, and high-velocity lunge.
  - `shooter`: Standoff distance keeping with avoidable ranged projectiles.
- **Constraints**:
  - Maximum of 2 enemy types per game spec.
  - No complex stealth, field-of-view cones, or flocking boids.
  - No multi-phase procedural boss encounters.
- **Reasoning**: Keeping enemy behaviors deterministic and bounded ensures that automated QA checks (such as flee-bot evasion and idle survival) remain reproducible and testable via automated smoke tests.

---

## 3. Parameter-Only Self-Repair Boundary

- **Tuning vs. Coding**: The self-repair loop is strictly **parameter-level**. It adjusts numeric physics attributes (player speed, player health, enemy count, enemy speed multiplier, objective targets).
- **Prohibited Code Modifications**:
  - The repair loop **cannot** synthesize new JavaScript or TypeScript code, rewrite client shaders, fix broken event listeners, or modify physics engine logic.
  - `GameIRPatch` schema remains unchanged; repair does not mutate layout architecture or inject unmapped keys.
  - Runtime or renderer bugs (such as canvas stalling or state reset failures) are classified as non-patchable (`patchable: false`), causing the orchestrator to immediately fast-fail with status `FAILED` and log `"needs developer"`.

---

## 4. Automated Smoke Tests Are Not Proof of Fun

- **Mechanical vs. Subjective Verification**: The 17 Playwright browser checks establish **mechanical sanity and reachability**:
  - They prove that the canvas renders, ticks progress, player inputs register, velocities match specs within $\pm 15\%$, win/lose conditions trigger, and survival is not instantaneous suicide.
  - They do **not** prove subjective player enjoyment, compelling game feel, juiciness, narrative depth, or long-term engagement.
- **Human Testing Role**: Human playtesting remains essential to evaluate whether a mechanically balanced game is enjoyable or aesthetically pleasing; automated QA checks are smoke checks, not mathematical proof of fun.

---

## 5. Model Provider Quota & Rate Limit Constraints

- **Free-Tier Limits**: Deployments targeting Google AI Studio Gemini API operate under free-tier constraints (e.g. 15 RPM for Flash models).
- **Required Cooldown Delays**:
  - Evaluation scripts require inter-prompt delays (`BENCH_DELAY_SECONDS = 5.0` to `13.0` seconds) to avoid triggering HTTP 429 quota exhaustion.
  - Real-model synthesis latency averages 45.8s end-to-end median in Run A (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`) and 47,020.5 ms in Run D (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), while planner-only median in Phase 0 bench with gemini-3.8-flash was 17.3s (`docs/eval/planner_gemini-3.8-flash_benchmark.json`); with repair in Run A2, median was ~75.3s (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`).
- **Model Timeout & Availability Boundaries**:
  - Run C with `gemini-3.8-flash` timed out in both attempts (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` and `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`), cause not established.
  - Lightweight models such as `gemini-3.5-flash-lite` (Run A, Run D) are significantly more stable and responsive for top-down synthesis pipelines.
- **Resilience Solutions**: The backend implements exponential backoff with jitter and an automatic fallback chain (`MODEL_FALLBACKS`). For offline demonstrations, saved zero-API fallback games ensure complete demo reliability.

---

## 6. Evaluation Sample Size & Generalizability

- **Benchmark Suite**: Empirical evaluation was conducted on a curated 12-prompt benchmark (10 standard diverse prompts + 2 lethal stress prompts).
- **Sample Scale & Multi-Run Evidence**:
  - In Run A (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`), 0 of 2 repairs succeeded (0.0%), with 91.7% first-response validation and 75% Playable@1/Playable@3 (median latency 45,807.6 ms, 14 model requests).
  - In Run A2 (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`), a re-run of 3 dev prompts after tuning the repair prompt repaired 2 of 2 (`s01`, `s02`) and `p06` was not repaired (tiny sample, dev cases, not an unbiased estimate; median latency 75,266.5 ms, 7 model requests).
  - Run C (`gemini-3.8-flash`) timed out in both attempts (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` and `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`, cause not established).
  - In Run D (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json` on the upgraded engine), 12/12 completed, first-valid was 12/12 (100.0%), Playable@1 was 9/12 (75.0%), Playable@3 was 12/12 (100.0%), repair was 3/3 (100.0%), with 18 model requests and 47,020.5 ms median latency.
- **Evaluation Caveats**:
  - Playable@1 equals Run A (9/12).
  - `p06`, `s01`, and `s02` failed first in Runs A, A2, and D and were also the cases used to tune the QA check and repair prompt, so Run D is a development-set result, not a held-out estimate.
  - One run per prompt, results can vary between runs.
  - Run D prompts are the same 12 as Run A and do not measure the new enemy types and layouts.
  - The engine, QA runner, and repair prompt differ from Run A, so the comparison is not single-variable. No claims of superiority between models can be supported given this sample size constraint.
