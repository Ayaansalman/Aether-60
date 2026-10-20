# Aether development progress

Branch: `codex/platformer-overhaul`. Started 2026-10-20.

Current status: platformer evaluation milestone implemented and verified; see the final verification section below.

## Baseline
- Clean main checkout; React/Vite/Phaser application and unused Next starter inspected.
- Original v1 schema, planner, runtime and browser QA assume arena survival.
- Backend environment absent; installing isolated dependencies before baseline tests.
- Frontend dependencies installed; npm reports 16 inherited vulnerabilities (12 high).

## Decision
Consolidate active product in React/Vite, preserving legacy routes and v1 backend. Add versioned v2 typed contracts, deterministic level construction, registered CC0 artwork, persisted stage evidence, Gemini design planning and platformer browser QA. No arbitrary generated code. Future genres dispatch through versioned genre contracts.

## Earlier stage (completed)
Implementing platformer vertical slice and asset registry.

## Remaining
Provider live probe; browser gameplay and visual verification; four prompt evidence; bounded repair; polished workspace; regression checks and verified local commit.

## Implemented milestone
- GameDesign and genre-specific GameIR v2 contracts; explicit capability guard and typed model output.
- Seeded section composition; ballistic validation with landing margins; bounded evidence-based layout repair.
- Phaser tilemap runtime, CC0 sprites, idle/run/jump/fall states, acceleration, coyote time, jump buffer, double jump, dash, patrol enemies/stomping, crystals, spikes, checkpoints, exit gate, health, loss/win and restart.
- Asset registry with verified texture dimensions, roles, animations, sources, licenses and SHA-256 checks. Only used atlases/backgrounds retained.
- React landing page and creator workspace consolidated as primary application. Next starter retained but not used. Legacy arena routes preserved.
- Persisted v2 API, events, intent/design/IR/assets/build/requirements/QA/repair/diagnosis artifacts and Inspector export.
- Lazy loading separates landing/studio, legacy app and Phaser runtime.
- Mobile layout and real touch movement/jump controls; keyboard typing does not affect game.

## Evidence and fixes
- Original baseline: 137 backend tests passed; original frontend build passed.
- Gemini model listing succeeded. Listed gemini-2.5-flash-lite rejects new users (404). Provider-recommended gemini-3.5-flash-lite completion succeeded; four real prompt designs persisted. No credentials in evidence.
- First QA exposed serializing a Phaser object from the restart hook; fixed void return.
- Fixed overlap contacts incorrectly resetting grounded state/jumps in midair.
- QA now waits on observed physics states and actual scene-generation changes rather than wall-clock guesses.
- Route evidence records actual static landings and settled landings on registered moving alternate routes; isolated launch positions are explicitly disclosed.
- Fixed repeated grass interior tiles and HUD overflow after visual review.
- API lifecycle/repair tests and 13 platformer unit tests pass. Full suite pending final run.
- UI checks: desktop/mobile prompt typing, design tab, honest empty Inspector, overflow and runtime exceptions, plus touch movement: 11/11 passed.

## Earlier stage (completed)
Final browser verification of four live designs; saving evaluation evidence and checking current pipeline end to end through the UI.

## Limits
- Platformer is the only implemented v2 genre; future genres have separate dispatch/contracts.
- Two authored player frames provide run/idle/jump/fall presentation; damage uses tint/blink, not a dedicated authored animation.
- Browser objective tests use controlled placement and damage injection, labeled per check. Route edges use real keyboard physics from isolated launch points, not full autonomous playthroughs.
- Aesthetic/game-quality judgments are manual screenshot review, not fabricated automated scores.
- 16 inherited npm dependency audit findings remain to assess; Phaser chunk exceeds Vite size advisory but loads separately.

## Final verification
- Four actual Gemini jobs: final browser QA passes (forest 14, industrial 13, tower 12, peaceful 12 checks); original model tower warning retained.
- Fifth live generation submitted from the actual UI completed with 12 passing browser checks after one real evidence-triggered layout repair. Before/after IR and initial failed report saved in docs/evidence/ui-live-result.json.
- Final runtime verification passes, including a measured 620 px/s dash.
- Full backend suite: 154 passed; production build and lint pass.
- 11/11 desktop/mobile UI checks passed; final screenshots manually reviewed. Mobile HUD readability improved after review.
- Semver-compatible dependency updates reduce inherited audit findings from 16 to 7 (5 high/2 moderate Tailwind build-tool advisories); no forced breaking major migration.
- Credential scan across source/assets/evidence passed. Credentials stay only in ignored local .env.
- Evaluation: docs/PLATFORMER_EVALUATION.md. Setup/demo/reproduction: docs/PLATFORMER_RUNBOOK.md.

## Remaining work after this milestone
Broader semantic fidelity metrics and full autonomous playthrough bots; richer authored animation/audio packs; multi-room level topology; RPG/adventure genre contracts/runtime; production authentication/queue hardening and build-tool dependency migration. These are not claimed complete.

Final creator control checks: 15/15 pass, including keyboard and toolbar restart, expanded preview with Escape, evidence export, desktop/mobile layout and real touch movement. Reproduce with `scripts/check_studio_ui.py --game-id <built-job-id>`.
