# Aether development progress

Branch: `codex/platformer-overhaul`. Started 2026-10-20.

Current status: Iteration 5 and its adventure asset-library expansion are implemented and verified locally: platformer and top-down adventure generation. Detailed results: docs/ITERATION5_RESULTS.md and docs/ASSET_LIBRARY_EXPANSION.md. Earlier milestone history is preserved below; older limitations describe those checkpoints.

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

## Iteration 3 — 2026-10-20

Implemented explicit per-level design specifications and model planning instructions, persisted count/progression intent, backward-compatible per-level IR/runtime settings, progressive deterministic fallback designs and reusable precision/combat/exploration/moving section components. Fixed optional collectible support references, kept collection objectives achievable on the mandatory route, reserved enemy departure space and placed checkpoints before challenges. Level transitions, local respawn, health/collection/checkpoint resets, final victory and whole-campaign keyboard restart are verified. Briefings wrap and the HUD shows level progress. Bounded layout repair now updates all level specifications.

Verification: backend 190 tests pass; frontend build, lint and six shared runtime tests pass. Real Chromium checks pass for the three-level ice fixture (26), saved Gemini design (40) and two-level industrial fixture (30). Evidence includes actual keyboard jumps with active ice braking, later-level hazards/checkpoints, objectives, transitions, final-level loss and keyboard restart after victory/loss. Two live planning invocations: HTTP 503 followed by a successful Gemini design; subsequent rebuilds made no further provider calls. Initial failures and screenshots are retained. Tests use isolated launch positions/controlled overlaps, not full autonomous playthroughs.

Full report and reproduction: docs/ITERATION3_RESULTS.md. Evidence: docs/evidence/iteration3/. Creator UI and asset library preserved; no push, deployment, new genre or asset download.

## Iteration 4 — 2026-10-20

Extended the platformer with typed, reusable event/trigger/link/objective components and a shared enemy state machine. Existing patrol, chase and icicle decisions are reused. Shooters reposition, turrets anchor, ambushers telegraph a lunge, and configurable multi-hit enemies react to damage. Added key/contact/proximity switches, latched pressure plates, projectile switches, real security-door collision/opening, optional player projectiles and bounded horizontal/vertical platform trajectories. Fixed lift motion on physics steps and relative rider grounding. New local/campaign objectives cover defeat, activation, unlocking, collection, survival and deadlines, with validated targets and explicit progress reset/retention rules. Planner, GameIntent, requirements evidence and creator capability/control text expose the new components.

Targeted verification: 72 backend tests and changed-module compilation pass; frontend build/lint and 12 shared component tests pass. Seven Chromium cases pass 126 checks: the three requested prompt families, a two-level mixed campaign with persistent defeat goals, survival/deadline constraints, timeout/restart and a saved two-level Gemini factory design. Final requirement reports pass for all cases. One live planning invocation; a recorded one-based index correction preserves the original design, and rebuilds use no further calls. Initial failures, final reports and screenshots are retained. Tests use controlled positions and real collisions/inputs, not autonomous completion or enjoyment certification. The unrelated project-wide suites were not rerun.

Full report, precise counts, supported semantics and reproduction: docs/ITERATION4_RESULTS.md. Evidence: docs/evidence/iteration4/. No new dependencies, genre, asset downloads, push or deployment.

## Iteration 5 — multi-genre adventures

Added separate AdventureDesign/AdventureIR contracts, v2 genre factory dispatch, provider-independent adventure planning, seeded connected-world construction and validation, and an independent zero-gravity Phaser adventure scene. Existing jobs/events, generation stages, Inspector, QA subprocess lifecycle and re-verification are reused; platformer generation and its runtime remain operational.

Playable adventures include eight-direction movement, tilemap collision, camera/bounds, buildings and scenery, named NPCs with contextual structured dialogue, seven event-driven goal types, explicit quest states, scattered pickups, quantities, atomic multi-item delivery, retained keys, switches, physically sealed passages, area transitions, optional patrol/chase projectile combat, health/loss, victory and restart. Gold objective markers and a compass guide exploration. Mobile controls have an adjacent readable objective, inventory and dialogue panel. Added matching Kenney Tiny Town/Tiny Dungeon CC0 atlases with original licenses, sources, dimensions and SHA-256 checks.

Verification: baseline 31 existing backend tests passed; final targeted backend suite 75 passed; shared frontend behavior/state suite 17 passed; production build and ESLint pass. Existing platformer Chromium regression passes 18/18. Two real Gemini planning calls produced distinct village/dungeon designs; reviewed saved-design rebuilds made no additional model calls. Final live browser checks pass 21/21 and 23/23, offline API cases pass 14/14 and 23/23, and creator checks pass 12/12 including actual submission, blueprint/Inspector, typing isolation, toolbar restart, expanded preview, touch movement and readable mobile objectives/dialogue.

Original model output, developer corrections/rebuilds, initial failures and all retests are preserved. Tests found and corrected invalid inactive-touch velocity, a Phaser body-group collision mismatch, and stale test hooks during canvas recreation. Browser checks use disclosed controlled positioning with real inputs/collisions, not autonomous navigation or aesthetic scoring. Specs validate references, resources and ordered access through locked passages. Unknown prose semantics are not universally certified; guards and fixture scope are explicit.

Limits: linear quest/area progression, one sealed passage per area, stationary NPCs, local enemy pursuit, no equipment/crafting/save-game service or branching dialogue. Characters have authored single frames animated through stride/bob/mirroring, rather than authored directional walk cycles. Asset replacement with a different atlas layout requires frame mapping updates. Detailed reproduction and evidence: docs/ITERATION5_RESULTS.md and docs/evidence/iteration5/. No deployment, push, unrelated redesign or dependency migration.

## Adventure asset-library expansion — 2026-10-21

Downloaded the official free Ninja Adventure and Tiny RPG Forest archives and independently verified their included CC0 licenses. Curated 52 resources into a semantic, versioned catalog with original license documents, source/archive hashes, image/frame geometry, authored directional animation sequences, collision-body alignment and category/style metadata. Ninja Adventure is the default family; Ansimuz is a separate forest-only family. The old Kenney renderer and platformer assets remain compatible. Remaining raw resources, paid expansions and downloaded demo code are not public/export dependencies; no CraftPix resource was used.

Added deterministic specification-driven asset selection to GameIR and real generation stages/Inspector evidence, plus a CC0 resource-export allowlist that rejects restricted or mixed-family bundles. Phaser uses registered terrain edge rules, actor resources, authored directional player/enemy animation, pickups, door/switch states, props, projectiles and defeat VFX. The two existing Gemini games received preserved-history, art-only upgrades with every non-art IR field asserted unchanged. No additional provider request or fixed authored demo map was used.

Verification: 77 catalog checks, 38 targeted backend tests, 17 frontend behavior/state tests, 83 API-browser checks and 12 actual creator UI checks pass; production build and ESLint pass. Fresh Ninja and Ansimuz fixture jobs and both upgraded Gemini jobs are READY. Corrected short-sheet animation bounds, empty animation sequences, transparent terrain selection, a six-frame VFX slice width and padded-frame pickup alignment during integration. Initial evidence is retained. Actual authored directional animation replaces the earlier single-frame limitation for the new families; Kenney compatibility retains its previous animation behavior.

Details, provenance, constraints, screenshots and reproduction: docs/ASSET_LIBRARY_EXPANSION.md and docs/evidence/asset-expansion/. The library does not add boss AI, shops, equipment, crafting, music behavior or a full game-source export feature. No deployment, push, unrelated refactor or dependency migration.


## Iteration 6 — adventure world quality, 2026-10-21

Replaced scatter-first maps with seeded settlement/woodland zones and connected dungeon room graphs. Added reserved approaches, purposeful house fronts and forest clearings, guarded key routes, physically sealed sanctums, smaller final chambers and settlement-aware landmark placement. Fixed tree proportions, roof/canopy depth ordering, NPC collision, dungeon floor atlas mapping and coherent interior decoration. Added pickup messages, collection counters and a compact opening HUD. The exact healer and crypt prompts are the first two Studio examples; peaceful delivery and key/unlock/relic adventures retain distinct mechanics.

Live testing exposed a model-generated cross-area return loop incompatible with forward-only portals. Added explicit planner instructions and a bounded, recorded outdoor-area normalization while preserving raw model JSON. Also stopped symbolic validation from granting inaccessible/later-area keys. Three Gemini calls total: one preserved invalid design and two successful live adventures. Saved-design rebuilds and final retests made no further calls.

Verification: 87 targeted backend tests, 17 frontend tests, 77 catalog checks, production build and ESLint pass. Geometry invariants pass across 40 seeds per acceptance prompt. Chromium fixture checks pass 16/16 (healer) and 24/24 (crypt), live checks 21/21 and 24/24, and platformer regression 18/18. Final rendered village, woodland, dialogue, crypt and completion screenshots were inspected. Browser tests use controlled placement with real input/physics, not autonomous navigation; mobile QA was not rerun.

Full implementation, reproduction, provenance and limitations: docs/ITERATION6_RESULTS.md. Evidence: docs/evidence/iteration6/. Local Git checkpoint includes the existing uncommitted Iteration 5 dependencies. No push, deployment, new asset pack, genre or agent.

## Iteration 7 — 2026-10-21

Extended the existing v2 pipeline with configured-LLM semantic family/control/requirements interpretation, source-grounded capability-to-IR/runtime evidence and creator Inspector fidelity reporting. Added strict runner design/IR and a shared fixed-step endless stream with distinct ground auto-jump and airborne flap controls, deterministic seeds, physics-derived spacing, bounded cleanup, score/death/restart, finite finish and speed curves. Added validated one-boss arenas with health bar, alternating telegraphed charge/volley, phase acceleration, real damage and defeat victory; sword requests use the disclosed existing projectile approximation. Adventures now support same-area nested biome regions, region-scoped actors and local explicitly requested slippery movement, retaining connected paths and real NPC/crystal/delivery flow.

Focused results: 83 backend tests, 23 shared frontend tests, production build and lint pass. Deterministic Chromium A/B/C/D pass 8/19/7/9 checks; existing platformer regression passes 18. Actual Gemini D and B jobs exercise semantic interpretation plus design; both pass runtime checks. B's original invented unsupported warnings and a zero-call saved-design correction/retest are preserved. Actual creator/mobile/Inspector evidence is recorded separately. Checks use disclosed controlled placement/state, not autonomous full playthroughs. Detailed architecture, reproduction, evidence and remaining limits: [ITERATION7_RESULTS.md](ITERATION7_RESULTS.md).

No push, deployment, new dependencies or asset packs. The identified stale local Aether backend was restarted with current code after isolated-port integration checks. Arbitrary prose coverage, authored biome blending, sword melee, arbitrary boss systems and prolonged human runner difficulty remain unverified or unsupported as specified in the report.

Iteration 7 follow-up: added playable Neon Overdrive and Cloudwing examples to the sample catalog, backed by saved deterministic runner fixtures and direct example URLs. Both sample buttons load their distinct control modes. Browser evidence: `docs/evidence/iteration7/runner-samples/`.


## Regional dungeon follow-up — 2026-10-21

Fixed the reported dark/garden dungeon failure using the user's saved Gemini job `ebf92a09-24b3-46a8-8519-587b9e6cc00b`, without new provider calls. Region bounds had replaced gate-access bounds, stranding the key and early enemies behind a locked whole-map divider. Maps with regions now reserve a local sealed final room, place prerequisites outside it and post-unlock targets inside, and carve connected corridors around its footprint. Indoor biome decoration preserves dungeon walls. Added actual dark/garden biome types with local dungeon/grass terrain and flower accents instead of using ice as a dark-theme proxy.

Expanded semantic bindings for adventure combat, item collection, switches, doors, exploration and treasure completion; saved narrower capability IDs retain their original IDs alongside explicit effective bindings. Ordered validation no longer credits unreachable goals and records targets, reachability and missing resources. Failures identify the blocked objectives instead of only asking users to inspect a JSON file.

Verification: 53 focused backend tests pass, including 40 generated region/door configurations with both theme orientations, the saved prompt regression and existing adventure/iteration-6/7 checks; 11 frontend state/behavior tests, build and lint pass. The rebuilt saved design passes 31 real browser checks covering combat, inventory, switch, closed/open door collision, treasure completion and restart. These checks use disclosed controlled placement, not an autonomous playthrough. Original failure evidence and corrected output: `docs/evidence/dual-dungeon-fix/`. Rebuild command: `aether-backend/venv/Scripts/python.exe scripts/rebuild_adventure_job.py <source-job-id>`. Current rebuilt local game: `4fd02ed9-1c32-4943-b17e-f84269aa7f24`; historical failure remains preserved. Backend restarted with current code. Semantic visual/combat approximation warnings from the original interpretation remain explicit; no new Gemini generation was claimed.
