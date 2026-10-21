# Survival routing and emitter follow-up — 2026-10-21

The user's exact failed prompt is preserved in `evidence/survival-fix/prompt.txt`; original intent and design are saved alongside it. Original failed job: `0f0ce45f-fdcb-490b-bbfd-cefef6483eff`.

The error was a composition failure, not a missing inventory ID that should have been added to this game. The studio's semantic router offered platformer/adventure/runner, so it classified a top-down survival loop as a quest adventure. Its mandatory quest model invented an NPC, relic, door and defeat/collection objectives. The invented relic lacked an inventory ID and failed AdventureDesign validation. Separately, the existing older arena IR/runtime already supported chasers and shooters, but the studio did not dispatch to it; it also lacked continuous randomized spawning and the requested exact five-shot emitter lifecycle. A feature name in one IR was not sufficient to preserve those semantics through the current creator.

Implemented a strict v2.3 SurvivalDesign/SurvivalIR adapter over the **existing ArenaScene**, with a validated endless objective, random safe role/position spawning, bounded live population, warnings, configurable shot count/interval, aimed projectiles, expiry immediately after the final shot, projectile cleanup, three-health evasion, elapsed-time score, death/restart and keyboard/touch movement. Chasers have a configurable 30-second lifespan so a full chaser population cannot permanently block further spawning; the default live cap is 18. Shooter bullets remain active after the shooter expires, until impact or their configured lifetime. Spawn samples that cannot satisfy the safety radius are skipped rather than placed on the player. Stream telemetry stays bounded. All new behavior is opt-in, preserving the legacy arena path.

The configured live semantic interpreter now distinguishes top-down perspective from quest gameplay and can select `arena_survival`. Requirements include exact health, emitter count/interval and roles, with specific construction witnesses and runtime check bindings. The existing v2 API, lifecycle, Inspector, blueprint and re-verification dispatch support this adapter. The creator includes a saved Bulletfall Survival sample. Mobile health/time are displayed outside the scaled canvas. Pydantic failures are reduced to field/message diagnostics for users, with a separate artifact that excludes raw input and reference URLs.

Verification:

- **103 focused backend tests pass**: survival contracts and API/re-verification, semantic routing and exact count/interval checks, friendly validation errors, legacy GameIR/mechanic variety, iteration-7 and regional dungeon regressions.
- **20 frontend pure behavior/state tests pass**, including exact five-shot scheduling, no catch-up burst after lag and no unsafe fallback spawn. Production build and ESLint pass. Existing Phaser bundle advisory and two Python deprecations remain.
- Exact-prompt deterministic API job and **one real Gemini end-to-end job** pass **14 browser runtime checks** each. The live job uses semantic interpretation plus typed design (two logical completions; no repeated generation). Checks use real Phaser movement, two real timed shots, real projectile collisions reducing all health points, fifth-shot expiry, restart, bounded spawning and a controlled accelerated timer proving no finite win. Spawn/emitter clock control and projectile placement are disclosed; these are not autonomous prolonged survival checks.
- The existing legacy arena's browser QA passes. Screenshot retained; the CLI report is in the execution record.
- **6 creator checks pass**: sample button, live preview, blueprint, mobile movement, readable health and no browser exceptions.

The live model produced two warnings about unrequested player attacks and quests. Its raw response and original READY_WITH_WARNINGS result are preserved. A narrow recorded guard removes only these known unsolicited categories when absent from the prompt, retaining unknown or explicitly requested limitations. The current job is READY; normalization used no further model calls. See `api-live/warning-normalization.json`.

Current local game: `http://localhost:5173/studio/play/4d8ceb5c-1f91-424d-9f75-f052de60707b`.
Sample: `/studio?example=survival`.

Reproduce offline with `scripts/check_survival_generation.py fixture`, `scripts/check_survival_creator.py`, and `pytest tests/test_survival.py` from the relevant runtime locations. The explicit `live` argument invokes the configured provider and should be used sparingly. Evidence is in `docs/evidence/survival-fix/`.

Scope: initial survival adapter uses an open arena, chaser/shooter roles, original primitive visuals and evasion-only controls. Other legacy arena actions/layouts remain in their existing path; they are not automatically claimed for this adapter. Human difficulty, prolonged play and arbitrary natural-language fidelity remain unverified. No new dependency, asset pack, push or deployment.
