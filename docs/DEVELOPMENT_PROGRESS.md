# Aether development progress

Branch: `codex/platformer-overhaul`. Started 2026-10-20.

Current status: Iteration 2 implemented and verified locally on the existing branch. Detailed results: docs/ITERATION2_RESULTS.md. The earlier milestone history below is preserved.

Implementation baseline: commit `8658bb94a4e0193d7740e91f96c082342b7a828e`. This checkpoint updates documentation while preserving that completed implementation and its evidence. No push or deployment is authorized by this checkpoint request.

## Baseline
- Clean main checkout; React/Vite/Phaser application and unused Next starter inspected.
- Original v1 schema, planner, runtime and browser QA assume arena survival.
- The backend environment was initially absent; dependencies were installed in an isolated local virtual environment.
- The initial frontend dependency audit reported 16 inherited findings (12 high); subsequent compatible updates reduced these to 7.

## Decision
The active product is the React/Vite application in `aether-frontend`; `aether-web` remains an unused Next starter. Existing arena routes and the v1 backend are preserved.

- FastAPI exposes the v2 generation, inspection, specification and bounded re-verification routes in `aether-backend/routes/platformer.py`.
- Gemini planning uses the existing OpenAI-compatible provider abstraction and validated `GameDesign` contracts. Explicit capability guards run before deterministic, seeded `PlatformerIR` construction and ballistic route validation in `services/platformer.py`.
- The Phaser Arcade runtime consumes the specification and registered CC0 artwork; it does not execute model-generated code.
- Jobs/events persist through the existing SQLite stores. JSON artifacts record intent, raw/final design, requirements, assets, build, validation, QA, diagnosis and repairs. Interrupted unfinished jobs are marked failed on startup.
- Browser QA runs in a bounded subprocess. Automatic repair changes only diagnosed level-layout parameters, retains evidence and reruns checks, at most twice. Other runtime failures require developer fixes.
- React exposes actual persisted evidence through the Engineering Inspector. Offline fixtures are explicitly labeled and remain separate from live Gemini evidence.

Only platformers have a v2 builder/runtime today. Future genres should add their own contracts, construction, validation and runtime dispatch rather than expand an arena-only global schema.

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
- API lifecycle/repair tests and 13 platformer unit tests pass as part of the final 154-test backend suite.
- Final creator checks pass 15/15, including desktop/mobile typing, design/Inspector controls, overflow, exceptions, touch movement, keyboard/toolbar restart, expanded preview with Escape, and evidence export.

## Limits
- Platformer is the only implemented v2 genre. RPG/adventure and other genre runtimes are not implemented.
- Two authored player frames provide run/idle/jump/fall presentation; damage uses tint/blink, not a dedicated authored animation.
- Browser objective tests use controlled placement and damage injection, labeled per check. Route edges use real keyboard physics from isolated launch points, not full autonomous playthroughs.
- Aesthetic/game-quality judgments are manual screenshot review, not fabricated automated scores.
- 7 dependency audit findings remain (5 high, 2 moderate) in the Tailwind build-tool chain. Phaser exceeds Vite's chunk-size advisory but loads separately.
- Some model outputs reported unrequested or contradictory limitations. Original evidence is preserved; registered-capability contradictions are corrected by the current guard, and the planning prompt now prohibits invented limitations. Complete semantic fidelity is not established.
- Saved job URLs require the local ignored SQLite database. Exported JSON evidence remains inspectable without it. Production authentication, durable queue recovery and deployment hardening remain future work.

## Final verification
- Four actual Gemini jobs: final browser QA passes (forest 14, industrial 13, tower 12, peaceful 12 checks); original model tower warning retained.
- Fifth live generation submitted from the actual UI completed with 12 passing browser checks after one real evidence-triggered layout repair. Before/after IR and initial failed report saved in docs/evidence/ui-live-result.json.
- Final runtime verification passes, including a measured 620 px/s dash.
- Full backend suite: 154 passed; production build and lint pass.
- 15/15 final creator UI checks passed; final screenshots manually reviewed. Mobile HUD readability improved after review.
- Semver-compatible dependency updates reduce inherited audit findings from 16 to 7 (5 high/2 moderate Tailwind build-tool advisories); no forced breaking major migration.
- Credential scan across source/assets/evidence passed. Credentials stay only in ignored local .env.
- Evaluation: docs/PLATFORMER_EVALUATION.md. Setup/demo/reproduction: docs/PLATFORMER_RUNBOOK.md.

These are results from the completed implementation verification, not newly rerun tests during this documentation-only checkpoint. The checkpoint rechecked saved evidence, Git state and the tracked progress document.

## Earlier checkpoint recommendations (see Iteration 2 results for subsequent work)
1. Strengthen semantic requirement-fidelity checks and add full autonomous playthrough coverage while retaining the disclosed scope of existing controlled tests.
2. Integrate richer authored character animations and audio; extend scene/level topology beyond connected side-scrolling sections.
3. Address the remaining build-tool advisories through a separately tested dependency migration.
4. Harden authentication, queue recovery and artifact persistence before any production deployment.
5. Add adventure/RPG through a separate genre contract, builder, validator and runtime when the platformer foundation is ready.

Reproduce creator checks with `scripts/check_studio_ui.py --game-id <built-job-id>`. See `docs/PLATFORMER_RUNBOOK.md` for backend, build, lint, browser and live-generation commands.

## Preservation
All completed source, assets, tests and exported evaluation evidence remain in Git. Local credentials, SQLite databases, runtime artifacts, dependencies and build output remain on disk under their existing ignore rules; credentials are not committed. This checkpoint does not delete files, push to GitHub, or begin another development iteration.


## Iteration 2 — 2026-10-20

Continued from dc6b507 on the same branch. Inspected Git history, prior progress/evaluation/runbook, planner, schema, builder, assets, runtime, orchestration, QA and repair before changing implementation. Preserved three exact prompt traces in both fixture and real Gemini modes before changes. Root causes and independent defect backlog: docs/ITERATION2_AUDIT.md.

Implemented requirements with original/model source phrases and capability IDs, construction witnesses, runtime verification linkage, failed/unverified/unsupported statuses and Inspector evidence. Expanded typed design/IR and shared runtime decisions for patrol/chase/ranged attacks, icicle warning/fall/collision/reset with proximity or configurable timers, periodic machinery, slippery movement, shrine/gate/beacon animation, one-way optional shelves and campaign transitions. Added distinct level compositions, collectible arcs, per-stage camera modes and seeded connected stages. Ice has original procedural art and relics; existing CC0 artwork remains registered and replaceable.

Creator now starts empty, explicitly labels samples, clears stale previews, shows backend stages, handles errors, surfaces requirement coverage, supports Inspector rechecks, labels controls and HUD counts, and uses proper game focus and mobile page scrolling. Screenshots prompted additional fixes to the keyhole-block exit representation and mobile body scrolling.

Verification:
- Three actual Gemini generation jobs using gemini-3.5-flash-lite; final saved-design rebuilds are explicitly labeled developer changes with prior IR preserved. Forest 16/16, factory 31/31, ice 34/34 browser checks pass; every tracked requested supported capability verified.
- Separate fixture results: forest 16/16, factory 29/29, ice 21/21. Live stage counts 1/3/2; fixture counts 1/3/1. Distinct geometry hashes and detailed encounter/hazard/objective profiles saved.
- Backend 164 tests pass; frontend production build and ESLint pass; five shared-behavior regression tests pass; creator suite 20/20, including intentionally seeded 503 recovery, keyboard/touch/restart/export and mobile scrolling.
- Additional actual creator submission configures timer icicles at 1500 ms, clears the previous sample and completes real backend/browser QA. Evidence in docs/evidence/iteration2/timer-flow/.
- Initial runtime failures and a genuine intermediate bounded layout repair are retained. A QA false failure caused by successful midair exit collision was corrected with explicit exit-collision evidence, not an invented landing.

Full report and reproduction: docs/ITERATION2_RESULTS.md. Evidence: docs/evidence/iteration2/. No push, external deployment, new genre, credential disclosure or destructive cleanup. Full autonomous unassisted completion, arbitrary natural-language coverage, nonlinear worlds, authored animation/audio, and production hardening remain limitations; parameter repair does not invent new runtime mechanics.
