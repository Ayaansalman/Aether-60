# Iteration 6 — deliberate adventure worlds

Implemented October 21, 2026 in the existing FastAPI/Phaser adventure adapter. No new genre, agent, dependency, asset pack, deployment or push.

## Findings and implementation

Focused inspection covered the adventure planner/contracts/builder, asset importer/catalog, Phaser scene, quest state, previous milestone documentation and a fresh Chromium run of the existing village. The old builder scattered actors first, chained broad L-shaped roads between them, and squeezed houses into leftover ground. The opening screenshot showed roads dominating the environment and sparse vegetation. Directional authored animation and foot colliders already existed; fixed sprite depths, undersized trees, an incorrect dungeon floor cell and loose placement were the larger problems.

`services/adventure_world.py` now constructs the environment before placing actors:

- Settlements have a square, house fronts connected to its paths, an entrance trail, eastern foraging clearings and a deepwood grove. The first NPC has a sensible position by a house. Settlement landmarks remain in the settlement; forest items occupy the woodland. Tree lines frame protected trails and clearings. Houses use complete registered modules, with seeded variants and arrangements.
- Dungeons compose entrance, guard, archive, approach and sanctum rooms through a connected graph, including an alternate route around the early rooms. Room positions/sizes vary with the seed. Short final areas use a smaller threshold/gallery/relic arrangement. Enemies guard the exploration route; keys and switches precede the seal, later objectives occupy its far side, and the exit is beyond the gate. Urns and stone decorations frame room edges.
- Actor counts, kinds, item quantities, area environments and ordered quest relationships come from the validated design. Placement reserves approaches before decorating. Narrow trails use the registered terrain borders. A physical sealed wall has one doorway and cannot be bypassed around the map edges.
- Determinism and destination/resource validation remain in the pipeline. The validator no longer invents access to non-objective keys in later or inaccessible areas. New `world_plan.json` evidence explains the generated zones and actor/prerequisite relationships.

Rendering uses the existing CC0 Ninja Adventure family throughout. Trees now match the 2× pixel scale, houses render as complete modules over ground, player/actor depth follows feet, and roofs/canopies support walking behind them. Roof art is separate from the solid facade footprint. NPCs now have real collision. Authored directional animation and the existing attack/damage feedback are retained. Pickup messages, collection counters, compact HUD and a short player identification improve orientation and feedback. Camera follow, keyboard movement, interaction ranges, dialogue, inventory, combat and restarts remain compatible.

The catalog importer now reproducibly selects a seamless interior floor cell (342 of the source's **22-column** atlas), rather than repeating a terrain boundary. It also composites reviewed urn/stone/rune cells onto the same floor. Catalog 1.1 records the new sheet dimensions, checksum and interior detail frames. No new downloaded artwork or license terms were introduced; original licenses and redistribution allowlists remain bundled.

## Quest and prompt differences

The exact supplied acceptance prompts are reproducible fixtures in `public/fixtures/village.json` and `crypt.json`, and are the Studio's first two examples. The older switch-based `dungeon.json` remains compatible.

The peaceful fixture has a healer, friendly villager, three herbs and a talk → collect → return loop, without enemies or attack controls. Dialogue references the actual eastern woodland. The crypt fixture has skeleton guards, an obtainable key, a physically sealed chamber and a separate magical relic objective. A key no longer replaces the requested relic. Skeleton requests resolve to skeleton artwork. Live planning instructions favor small, coherent quest loops and distinguish keys from final rewards.

A real Gemini attempt exposed an existing contract limitation: it placed the herbs in area one and the return NPC in area zero, although area portals only advance. The planner now explicitly requests a single outdoor map for collection/return loops. A bounded normalization merges only outdoor areas in a non-monotonic delivery loop into connected village/forest zones. It preserves quest order, actors and resources; it does not merge dungeon/interior progression or reorder objectives. Raw model JSON is persisted before normalization/validation, and `design_normalization.json` records corrections. A regression test verifies raw-output preservation and the normalized quest's reachability.

## Verification and evidence

| Verification | Result |
| --- | --- |
| Targeted backend: adventure, assets, Iteration 6, platformer, API, gameplay and campaign | 87 passed |
| Frontend adventure state and platformer behavior tests | 17 passed |
| Catalog images, frame bounds, nonempty roles, hashes and licenses | 77 checks passed |
| TypeScript/Vite build and ESLint | Passed; existing Phaser chunk-size advisory remains |
| Geometry/resource/closed-gate invariants | 40 seeds per acceptance prompt passed |
| Peaceful acceptance fixture in Chromium | 16/16 |
| Crypt acceptance fixture in Chromium | 24/24 |
| Real Gemini healer adventure, final browser retest | 21/21, READY |
| Real Gemini crypt adventure, final browser retest | 24/24, READY |
| Existing forest platformer Chromium regression | 18/18 |

Exactly **three** live planning invocations used `gemini-3.5-flash-lite`: the initial invalid outdoor return design, a successful crypt design, and one additional healer request after the correction. The successful healer output exercised the normalization and contains six stages with three distinct named herbs; the crypt contains five stages across two areas. Saved-design developer rebuilds and browser retests made no additional provider calls. Their original IR and QA remain in `iteration6_developer_rebuild.json`. The initial failed API export is retained separately.

Successful live IDs:

- Healer: `131ecf5b-3241-4fc9-ac0f-ece84bbe14e0`
- Crypt: `99ee11eb-0116-44a9-8753-d3eeb97e03ad`

Reports/API exports and opening, dialogue, forest collection, crypt key and completion screenshots are in [evidence/iteration6](evidence/iteration6/summary.json). Actual rendered village, woodland, dungeon and live gameplay screenshots were inspected. Visual review caught the floor-atlas mistake; final screenshots show the corrected floor. Browser checks exercise actual keyboard movement, animation changes/facing, collision, NPC dialogue, pickups, complete delivery consumption, enemy pursuit/damage/loss/defeat, closed/open passage collision, area transitions, victory and restart. They use **controlled positioning**, not an unassisted navigation playthrough. Visual inspection is qualitative, not an aesthetic score.

## Reproduction

The isolated verification servers use backend port 8002, frontend 5175, `data/iteration6.db` and `artifacts/iteration6`; existing servers were left untouched. Restart the backend after Python changes.

```powershell
# Backend terminal, from aether-backend
$env:AETHER_DB_PATH='data/iteration6.db'
$env:AETHER_ARTIFACTS_DIR='artifacts/iteration6'
$env:AETHER_FRONTEND_URL='http://localhost:5175'
./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002

# Frontend terminal, from aether-frontend
$env:AETHER_BACKEND_URL='http://127.0.0.1:8002'
npm run dev -- --host 127.0.0.1 --port 5175

# Repository root: deterministic fixtures + rendered checks, no provider calls
aether-backend/venv/Scripts/python.exe scripts/verify_iteration6.py

# Targeted backend checks
aether-backend/venv/Scripts/python.exe -m pytest aether-backend/tests/test_iteration6.py aether-backend/tests/test_adventure.py aether-backend/tests/test_adventure_assets.py aether-backend/tests/test_platformer.py aether-backend/tests/test_platformer_api.py aether-backend/tests/test_gameplay_systems.py aether-backend/tests/test_campaign.py -q

# From aether-frontend
npm run build
npm run lint
node --experimental-strip-types --test tests/adventure-state.test.mjs tests/platformer-behaviors.test.mjs
```

Play `/studio?example=village` or `/studio?example=crypt`. Click the canvas; WASD/arrows move, E interacts/advances dialogue, F/X attacks in combat games, and R restarts. `verify_iteration6.py --live` deliberately makes two new provider calls; `--case village` or `--case crypt` restricts it to one. Routine verification needs neither. `rebuild_iteration6.py` is a one-time preserved-history developer rebuild for the saved jobs; it refuses to overwrite its original rebuild record.

## Boundaries and checkpoint

Worlds use reusable small spatial grammars, not arbitrary authored architecture. Progression remains sequential, portals forward-only and doors limited to one per area. NPCs are stationary; enemies use local pursuit rather than global pathfinding. There is no new hazard system, branching dialogue, equipment/crafting, music or save-game service. This iteration did not rerun mobile creator QA or a broad repository audit. Arbitrary natural-language fidelity and fully autonomous completion are not certified.

The repository began with the Iteration 5 adapter, asset library and evidence uncommitted. The local checkpoint preserves those existing dependencies alongside these Iteration 6 improvements; nothing was reset or discarded. Secrets, databases, raw downloads, local environments and runtime artifact directories remain ignored. No push or deployment was performed.
