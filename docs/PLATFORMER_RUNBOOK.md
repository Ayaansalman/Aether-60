# Platformer evaluation runbook

The active product is `aether-frontend` (React/Vite/Phaser). `aether-web` is an unused Next starter. Legacy arena routes and v1 APIs remain for regression checks.

## Start

From the repository root, in two terminals:

```powershell
cd aether-backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
cd aether-frontend
npm run dev -- --port 5173
```

Open http://127.0.0.1:5173/studio. Vite proxies `/api` to the backend. Start the frontend before generating: backend QA opens an actual browser against it. Set `AETHER_FRONTEND_URL` for another frontend origin. Production needs an equivalent `/api` reverse proxy; nothing has been deployed.

The ignored local `.env` is configured for Gemini. For a fresh checkout, copy `.env.example`, set `MODEL_PROVIDER=openai_compat` and supply your key locally. `gemini-3.5-flash-lite` was verified by completion on 2026-10-20. Model listing alone does not guarantee access: the provider listed 2.5 Flash Lite but rejected its completion requests for new users. The existing OpenAI-compatible provider remains in use with bounded retries.

Without a provider choose **Offline fixture Â· deterministic**. Example previews are labeled fixtures. Live requests never silently fall back to mocks.

## Demonstrate

1. Submit a forest, industrial, tower or peaceful prompt. Arrows/A/D move, Space/W/up jump, Shift dash if supported, R restart. Mobile has real touch controls. Click the game to focus; typing does not control the player.
2. Open **Inspector**. Model planning is separate from deterministic contract checking, level construction, asset validation, browser testing and repair.
3. Open **Design** for actual platform geometry, seed, abilities and objective.
4. Inspect `model_design.json`, `requirement_report.json`, `final_design.json`, `game_ir_v2.json`, `asset_manifest.json`, `validation.json`, `qa_report_initial.json`, `qa_report.json`, `repair_report.json` and `diagnosis.json`. Artifacts appear only when produced. Export evidence from Inspector.
5. Play. Collection gates require the HUD count. Damage gives invulnerability feedback. Falling consumes health and returns to the checkpoint. Restart resets progress.

SQLite jobs/events are under `aether-backend/data/`; generated artifacts under `aether-backend/artifacts/`. Both are ignored. Interrupted jobs are marked failed on restart. Explicit browser re-verification preserves prior evidence and permits at most three re-verifications per built game.

## Reproduce

```powershell
cd aether-backend
.\venv\Scripts\python.exe -m pytest tests -q
cd ..\aether-frontend
npm run build
npm run lint
cd ..
aether-backend\venv\Scripts\python.exe scripts\platformer_fixtures.py
aether-backend\venv\Scripts\python.exe scripts\evaluate_platformers.py --mode fixture
# Makes four actual provider requests:
aether-backend\venv\Scripts\python.exe scripts\evaluate_platformers.py --mode live
```

For fresh dependencies, create a Python venv, install `aether-backend/requirements.txt`, install Playwright Chromium in that venv, and run `npm ci` in the frontend. Pillow is used only for development asset inspection, not application startup or tests.

Real snapshots are in `docs/evidence/live/`; fixture validation is in `docs/platformer-fixture-results.json`. They are separate evidence sources. Saved local IDs are in `docs/evidence/live-job-ids.json`; those routes require the ignored local SQLite database. Exported JSON remains inspectable in a fresh checkout.

## Evidence scope

- Schema/asset checks validate contracts, dependencies and checksums.
- Route equations include launch/landing margins. Browser route checks perform actual keyboard jumps from isolated launch positions and verify destination landings, including registered moving alternates.
- Objective/checkpoint/loss tests disclose controlled overlap placement or damage injection. These are actual state/collision checks, not full autonomous playthroughs.
- Runtime exceptions, failed assets and functional failures prevent QA success. Browser unavailability produces an explicit unverified-runtime warning.
- Repair targets diagnosed route failures only: reduce gaps/elevation, persist before/after IR, rerun QA, maximum two repairs. Other runtime defects require developer fixes. Generated code is never executed.
- Screenshots are manually reviewed. Passing functional checks does not certify aesthetics, fun or full semantic fidelity.

## Boundaries

Only the v2 platformer genre is implemented. RPG, dialogue, multiplayer, bosses, crafting and custom code are unavailable. Genre-specific contracts/builders allow future runtimes without changing the old arena schema. Tower designs are ascending connected routes, not multi-room tower engines. Moving platforms are alternate routes. Construction/validation/repair services are labeled deterministic software, not invented agents.

The pack has two player animation frames and no dedicated damage sprites or soundtrack. Remaining Tailwind build-tool advisories are recorded in `docs/evidence/npm-audit-final.json`. Phaser loads separately but exceeds Vite's size advisory. This is a local evaluation milestone, not a public production deployment.

Creator UI checks: run `aether-backend/venv/Scripts/python.exe scripts/check_studio_ui.py --game-id <local-built-job-id>` while both servers run. Without `--game-id`, checks use the explicitly labeled offline preview. No provider calls are made.
