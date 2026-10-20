# Aether — from an idea to a playable world

Aether is a no-code game creation studio. This milestone generates sprite-based 2D platformers from natural-language prompts using Gemini, typed design contracts, deterministic level composition, Phaser, and real browser QA.

The active product is **`aether-frontend`**: an original landing page, creator workspace, playable preview, touch/keyboard controls, and Engineering Inspector backed by persisted events and artifacts. The separate `aether-web` Next starter is not required. Original arena routes and v1 APIs remain available.

```text
Prompt → Gemini GameDesign → capability checks → seeded GameIR v2
       → ballistic validation → CC0 assets → Phaser runtime
       → Chromium QA → bounded targeted layout repair → result
```

Supported: accelerating movement, buffered/coyote-time jumping, double jump, dash, tilemap terrain, ascending routes, moving platforms, animated sprites, patrol enemies, stomping, hazards, crystals, checkpoints, health, win/loss and restart. Unsupported mechanics are reported.

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

Artwork: Kenney Pixel Platformer and Industrial Expansion, CC0; original procedural ice, relic and exit components use project source terms. Licenses and asset registry are bundled. No code has been pushed or deployed.
