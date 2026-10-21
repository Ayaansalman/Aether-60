# Iteration 5 — multi-genre adventure generation

Follow-up: the [adventure asset-library expansion](ASSET_LIBRARY_EXPANSION.md) adds Ninja Adventure and Ansimuz families, semantic resource selection and authored directional animation. The original milestone evidence and Kenney-specific limitations below remain as historical records.

Implemented in the existing React/Vite + FastAPI application. The unused Next starter and legacy arena endpoints remain unchanged. No deployment or push was performed.

## Architecture and playable behavior

The v2 API still accepts natural-language prompts without an engine selector. `services/game_factory.py` routes explicit top-down/adventure/RPG/NPC requests to the adventure adapter; explicit platformer prompts retain their original path. `AdventureDesign` and `AdventureIR` are separate contracts from platformer sections, jump physics and campaign schemas. Existing provider configuration, persisted jobs/events, Inspector artifacts, build/QA lifecycle and re-verification endpoints are reused.

The separate Phaser `AdventureScene` uses zero gravity, normalized eight-direction WASD/arrow movement, foot-sized collision bodies, tilemaps, camera following, world bounds and persistent adventure state across areas. It includes keyboard/touch interaction, NPC names/roles, greeting/active/completed dialogue, quest HUD and target compass/markers, scattered item pickups, quantities, atomic multi-item deliveries, retained keys, switch prerequisites, solid locked passages, optional two-hit projectile combat, contact damage, defeat/loss, final victory and whole-game restart. Enemy patrols and proximity pursuit use Arcade collision; peaceful games contain no enemies or attack controls.

Quest state is `NOT_STARTED → ACTIVE → COMPLETED`. Talk, collect, deliver, explore, defeat, activate and unlock goals are driven by real gameplay events. Earlier exploratory pickups and other irreversible events are retained so accepting a later quest does not lose them. Doors create physical barriers; destinations after the door are placed beyond the barrier. Area exits require local goals to complete. Inventory and quest state persist through transitions.

Seeded worlds compose paths, rooms, terrain, solid obstacles, houses, decorations, NPCs, landmarks and pickups. Village/forest maps use outdoor composition; ruins/dungeon/cave use connected rooms and corridors. Prompt-selected actors, quest sequences, combat, area count and settings change composition rather than merely recoloring a fixed map. Static validation checks all destinations and individual pickups, sequential access through locked passages, target types, quantities and item/switch prerequisites.

Artwork uses Kenney Tiny Town and Tiny Dungeon CC0 atlases, with original license files, source metadata, role mapping, dimensions and SHA-256 verification. New assets are separate from the existing platformer registry. The runtime applies a dark dungeon palette and uses registered top-down people, buildings, foliage, keys, switches, monsters and treasure.

## Real generation evidence

Exactly two live planning invocations used the securely configured provider abstraction and `gemini-3.5-flash-lite`, one per supplied prompt family. No credentials are exported. Deterministic fixtures and saved-design rebuilds made no further provider calls.

| Case | Final job | Final browser checks |
| --- | --- | --- |
| Gemini peaceful village | `a6ed2959-515e-4b56-b601-30a9bce305ae` | 21/21 |
| Gemini dungeon | `1fdc15eb-df61-430f-9cc1-ce0e5c0c4ba4` | 23/23 |
| Offline village | `8f7f6ca4-b3e4-46c6-9ef1-dbc27d2115ea` | 14/14 |
| Offline dungeon | `220400e2-e278-4f2a-9e55-f030ef54824d` | 23/23 |

All four jobs reached `READY`. Final API exports are `docs/evidence/iteration5/{live,fixture}/*-final.json`. Each includes genuine Inspector events, intent, design, IR, assets, validation, original QA, retests and outcomes. The live village contains seven objectives, named NPCs and three distinct herbs; the dungeon contains two areas, monsters, a key, runic switch, locked vault and treasure. The offline village instead composes a three-step talk/three scattered pickups/deliver quest. These are distinct compositions within the supported mechanics.

Original model output remains in `model_design.json`. Reviewed guards remove known unrequested limitations, replace spatial clues unsupported by placed actors, and expand the healer's delivery to consume the complete collected set. `interpretation_guard.json` records each correction. Saved live designs were rebuilt once after developer improvements; `iteration5_developer_rebuild.json` preserves prior IR/QA and explicitly identifies this as developer work, not autonomous repair. Re-verification uses the original provider provenance without a new completion request.

Initial failing browser evidence is retained. Real checks found inactive touch inputs producing invalid velocities and a Phaser static/dynamic body-group mismatch allowing closed-door traversal. Both were fixed and rechecked. A Vite development reload also interrupted an intermediate run; final API retests are unaffected. Adventure repairs do not claim arbitrary code synthesis: invalid designs fail validation; deterministic construction creates connected paths; runtime defects require developer fixes.

## Targeted verification

- Baseline: 31 existing platformer/gameplay backend tests passed.
- Final targeted backend suite: 75 passed (adventure, platformer, v2 lifecycle, gameplay and campaign).
- Shared frontend behavior/state tests: 17 passed, including early pickups, delivery consumption, multi-item atomicity, gating and state retention.
- Frontend TypeScript/Vite production build and ESLint pass. Existing Phaser chunk-size advisory remains.
- Existing forest platformer Chromium regression: 18/18 checks pass, including real physics and restart.
- Adventure API Chromium cases above: 81/81 checks pass. Checks include real horizontal/vertical movement, zero gravity, collision, NPC dialogue, event-based quest progress, inventory delivery, optional combat movement/damage/defeat/loss, locked/open passage collision, area transitions, completion and restart, with no runtime exceptions.
- Creator verification passes 12/12, including actual fixture submission, blueprint/Inspector, typing isolation, toolbar restart, expanded preview, mobile touch movement, readable mobile objectives/dialogue and overflow checks. Report and desktop/mobile screenshots are in `docs/evidence/iteration5/creator/qa_report.json` and adjacent images. A stale test hook during canvas recreation was fixed and the prior creator submission resumed for the final checks, without generating another game.

Browser tests disclose controlled placement before keyboard/collision/interaction checks. They are not autonomous navigation, aesthetic scoring, or proof that every natural-language request has been fulfilled. Static connectivity and ordered prerequisite checks complement these runtime tests. Screenshots were manually inspected; source atlas contact sheets are preserved.

## Reproduction

Normal development uses backend port 8000 and Vite port 5173. Stop/restart any already-running backend to load the changed Python modules. Use the existing ignored `.env` for provider credentials; fixture mode requires no API key.

Verification here used isolated ports 8001/5174 and `data/iteration5.db`, leaving the pre-existing backend on port 8000 untouched:

```powershell
# Terminal 1, from aether-backend
$env:AETHER_DB_PATH='data/iteration5.db'
$env:AETHER_ARTIFACTS_DIR='artifacts/iteration5'
$env:AETHER_FRONTEND_URL='http://localhost:5174'
./venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001

# Terminal 2, from aether-frontend
$env:AETHER_BACKEND_URL='http://127.0.0.1:8001'
npm run dev -- --host 127.0.0.1 --port 5174

# From repository root: two fixture jobs, or add --live for two provider requests
aether-backend/venv/Scripts/python.exe scripts/verify_iteration5.py
aether-backend/venv/Scripts/python.exe scripts/check_iteration5_ui.py

# From aether-backend
./venv/Scripts/python.exe -m pytest tests/test_adventure.py tests/test_platformer.py tests/test_platformer_api.py tests/test_gameplay_systems.py tests/test_campaign.py -q
./venv/Scripts/python.exe -m services.adventure_qa 'http://localhost:5174/studio?example=dungeon' ../docs/evidence/iteration5/reproduction

# From aether-frontend
npm run build
npm run lint
node --experimental-strip-types --test tests/adventure-state.test.mjs tests/platformer-behaviors.test.mjs
```

Offline previews are `/studio?example=village` and `/studio?example=dungeon`. Saved jobs use `/studio/play/{id}`. Click the game to focus; WASD/arrows move, E talks/uses/advances dialogue, F/X casts when combat is equipped, R restarts. Gold indicators and the compass mark the active objective. Inspector exposes the actual generation artifacts.

## Limits

This is a small linear adventure adapter: up to three areas, sixteen sequential goals and one sealed passage per area. It has no branching dialogue, equipment/stat/crafting systems, shops, save-game service, multiplayer or boss AI. NPCs remain stationary; enemies use local pursuit rather than navigation-mesh pathfinding. Single-frame authored characters use stride/bob/mirroring animation rather than full authored directional walk cycles. Replacing the atlas with a different layout requires updating the adapter's frame mapping as well as registry metadata. The canvas scales on small screens; an adjacent HTML panel preserves readable objectives, inventory and dialogue, and expanded preview is available.

Fixtures use labeled keyword rules, while live designs use the existing model provider. Supported structural references and explicit guard cases are validated; arbitrary prose semantics and every unsupported request cannot be universally certified. The model's original output and each actual correction remain inspectable. No broad repository audit, unrelated redesign, dependency migration, deployment or additional model training was performed.
