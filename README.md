# Aether — from an idea to a playable world

Aether is a no-code game creation studio. It generates sprite-based 2D platformers and top-down adventures from natural-language prompts using Gemini, genre-specific design contracts, seeded world construction, Phaser, and real browser QA.

The active product is **`aether-frontend`**: an original landing page, creator workspace, playable preview, touch/keyboard controls, and Engineering Inspector backed by persisted events and artifacts. The separate `aether-web` Next starter is not required. Original arena routes and v1 APIs remain available.

**What can it create?** See the [current engine capabilities](docs/ENGINE_CAPABILITIES.md) for both genres, supported mechanics, example prompts, controls and current limits.

```text
Prompt → genre routing → Gemini design → validated genre-specific GameIR
       → route/connectivity checks → CC0 assets → Phaser genre adapter
       → Chromium QA → diagnosis / supported targeted repair → result
```

Supported: accelerating movement, buffered/coyote-time jumping, double jump, dash, tilemap terrain, ascending routes, moving platforms, animated sprites, patrol enemies, stomping, hazards, crystals, checkpoints, health, win/loss and restart. Unsupported mechanics are reported.

Top-down adventures add explorable villages/forests/ruins/dungeons, NPC dialogue, sequential event-based quests, inventory and multi-item deliveries, keys, switches, solid locked passages, area transitions and optional projectile combat. Natural-language prompts select the runtime automatically. Try the Village and Dungeon samples in the creator. See [Iteration 5 results, limits and reproduction](docs/ITERATION5_RESULTS.md).

Adventure artwork now defaults to a semantic Ninja Adventure catalog with authored directional animations. Ansimuz Tiny RPG Forest is a separate selectable forest family; legacy Kenney artwork remains compatible. Original CC0 licenses, frame/hash validation and resource-export allowlists are included. See [asset library expansion and verification](docs/ASSET_LIBRARY_EXPANSION.md).

## Run

Use Python 3.11+, Node.js 20.19+/22.12+, and Playwright Chromium.

```powershell
# First-time setup, from the repository root
python -m venv aether-backend/venv
aether-backend\venv\Scripts\python.exe -m pip install -r aether-backend/requirements.txt
aether-backend\venv\Scripts\python.exe -m playwright install chromium
cd aether-frontend
npm ci
```

Start in separate terminals:

```powershell
cd aether-backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
cd aether-frontend
npm run dev -- --port 5173
```

Open [Aether Studio](http://127.0.0.1:5173/studio). Configure `aether-backend/.env` from `.env.example` for live Gemini generation; the verified model is `gemini-3.5-flash-lite`. Keep credentials local. Choose **Offline fixture · deterministic** to work without a provider. Live jobs never silently fall back to mocks.

## Verify

```powershell
cd aether-backend
.\venv\Scripts\python.exe -m pytest tests -q
cd ..\aether-frontend
npm run build
npm run lint
```

Iteration 2 has 164 passing backend tests, five shared runtime behavior tests, and 20 passing creator checks. The three required real Gemini jobs and three separate fixtures pass expanded browser QA. See [Iteration 2 results and limits](docs/ITERATION2_RESULTS.md). The previous milestone's four real Gemini results, earlier failures, re-verifications and provenance are exported separately from fixtures in `docs/evidence/live/`. Browser tests use actual keyboard movement/jumping/landings and explicitly labeled controlled state transitions. They do not establish full autonomous playthroughs, aesthetic excellence, or fun.

- [Iteration 2 audit and results](docs/ITERATION2_RESULTS.md)
- [Previous milestone evaluation](docs/PLATFORMER_EVALUATION.md)
- [Evaluation and startup runbook](docs/PLATFORMER_RUNBOOK.md)
- [Development progress and boundaries](docs/DEVELOPMENT_PROGRESS.md)
- [Four live prompt results](docs/evidence/live/summary.json)
- [Asset sources and dimensions](aether-frontend/public/assets/README.md)

Artwork: Kenney Pixel Platformer and Industrial Expansion, CC0; original procedural ice, relic and exit components use project source terms. Adventure assets and their original CC0 licenses are also bundled. See the asset-library documentation for provenance. Pushing source to a testing repository does not deploy or host the application.


Adventure world design and the playable healer/crypt acceptance cases: [Iteration 6 results, verification and reproduction](docs/ITERATION6_RESULTS.md).

Arcade difficulty, structured procedural challenges, physics checks and theme-specific presentation: [Iteration 8 results and reproduction](docs/ITERATION8_RESULTS.md).
