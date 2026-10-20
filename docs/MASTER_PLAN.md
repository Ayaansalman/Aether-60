# MASTER PLAN: autonomous execution for the 60% milestone
Save as `docs/MASTER_PLAN.md` in the repo (`AETHER_V3`). Hard deadline: portal submission Sun Oct 18, 2026; evaluation Mon Oct 19. Feature freeze Thu Oct 16. Today is about Oct 12 (evening).

## 0. How the agent must work
1. Before starting, read this file, `docs/QA_HOOK.md`, `docs/DECISIONS.md`, `docs/CODEBASE_MAP.md` and `docs/blueprint.pdf` (sections 4, 5, 6, 7, 9, 13, 15). The blueprint is the product spec; this file is the work order.
2. Create `docs/PROGRESS.md` if it does not exist: one row per phase with status (todo / doing / done / blocked), date and time, commit hash, key results (real numbers), and open problems. Update it after every phase. If your context gets long or you restart, resume from PROGRESS.md.
3. Work phase by phase, in order. After each phase: run that phase's acceptance checks, fix failures in the code (never weaken or delete a test), update `PROGRESS.md`, make a local git commit with the given message, then continue to the next phase without asking me.
4. Stop and report only if: (a) a phase still fails after 3 genuinely different fix attempts (say what you tried), (b) a manual step by me is truly required (say exactly what), or (c) all phases are done.
5. If a file or module from a phase already exists (the teammate may have added some), read it and extend it. Do not duplicate or overwrite it.
6. Do not gold-plate. If something is not in this plan, do not build it.

### Standing rules (never break)
- Never run `git push`, `git reset`, `git checkout`, `git pull` or `git fetch`. Local commits only, after tests pass.
- Never print, log or commit secrets. `aether-backend/.env` stays untracked. Do not edit `.env` except where a phase says so. Only update `.env.example`.
- Never edit `providers/mock.py` or any test just to make results look better. Mock results must always be labeled ("MOCK PROVIDER: not a real model, results are not evidence" and `provider="mock"` in outputs).
- Don't change gameplay behavior unless a phase says so. Don't touch Nexus, Vault, Auth or the old `/api/games`, `/api/auth`, `/api/users`, `/api/generate` routes.
- Windows PowerShell: no `&&` chaining. Backend python is `aether-backend\venv\Scripts\python.exe`. Run commands to completion with a timeout. Start dev servers in the background once and don't poll them repeatedly. Stop servers you started when you are done.
- Every phase ends with a results table: what you ran, pass/fail, real numbers.
- If you add a dependency, justify it in `docs/DECISIONS.md`.

### Out of scope (do NOT build)
Second game genre, new enemy types (schema allows `chaser` only), LangChain/LangGraph, vector DB, accounts/login changes, fine-tuning, Unity, 3D, multiplayer, executing model-written code, queues like Redis/Celery.

## 1. Fixed facts
- Repo: `AETHER_V3` (React 19 + Vite + TS frontend `aether-frontend`, FastAPI + Pydantic v2 backend `aether-backend`, flat layout with `main.py` and `routes/` at the backend root; `aether-web` is unused).
- Frontend: `http://localhost:5173`. Backend: `http://localhost:8000` (CORS already allows 5173). Phaser 3.90.
- Game URLs: `/play/demo`, `/play/demo-survive`, `/play/demo-melee`, `/play/demo-avoid`, and `/play/:game_id` for generated games. QA hook only when the URL has `?test=1`; known-broken fixtures only with `?test=1&bug=restart_keeps_hp|no_win`.
- GameIR v1 (`aether-backend/schemas/game_ir.py`): `arena_survival`, themes fantasy/sci_fi/pirate/spooky/cozy, attack modes projectile/melee/avoid_only, enemy type chaser only, objectives survive_seconds (5-120) / collect_count (1-20). `GameIRPatch` + `apply_patch` exist. `services/validator.validate_game_ir` exists.
- LLM: `providers/` (mock, OpenAI-compatible adapter with 429/503 backoff), `services/planner.plan_game(prompt, provider)`; `.env` is configured for Gemini free tier (`MODEL_PROVIDER=openai_compat`, `MODEL_NAME=gemini-3.8-flash`). Free-tier rate limits apply: keep `BENCH_DELAY_SECONDS` (default 4).
- QA: `services/qa_runner.py` (`run_qa(url, out_dir)`, 15 checks, sync Playwright, call it as a subprocess: `python -m services.qa_runner <url>`), scripts `run_qa_all.py`, `run_qa_fixtures.py`, `check_movement.py`, `ui_smoke.py`, `run_planner_bench.py`, `try_planner.py`.
- Frontend API layer: `src/lib/apiClient.ts` + `mockApi.ts` (`VITE_USE_MOCK_API`), Forge page with timeline and trace drawer, `PlayGame.tsx` loads `getSpec(id)` for non-demo ids.
- Current tests: 23 pytest tests passing; QA 15/15 on the four demo modes; both fixtures detected.
- Job states: `QUEUED` -> `PLANNING` -> `VALIDATING_SPEC` -> `BUILDING` -> `TESTING` -> `READY` | `READY_WITH_WARNINGS`; critical failure -> `REPAIRING` -> `VALIDATING_SPEC` -> `BUILDING` -> `TESTING`; `FAILED` after 2 repairs. Max 3 test runs. Never leave a job stuck.

---

## Phase 0: verify the real-model planner results
1. Read the newest `artifacts/bench/planner_*.json|md`. Confirm it says provider `openai_compat`, shows the model id and date, and has realistic latencies (hundreds of ms or more, not ~1 ms). If it is a mock run, re-run the benchmark with the real provider (do not change the mock).
2. Write `docs/EVAL_PLANNER.md`: provider, model, date, sample size, per-prompt table, first-response validation rate, final success rate, theme/objective match rate, limitation-honesty rate, median and max latency. For every prompt whose first response failed validation, include the raw first response and the root cause. Copy numbers only from the artifact.
3. Confirm `aether-backend/.env` is ignored (`git check-ignore -v aether-backend/.env`) and not in `git ls-files`.
4. Run the full pytest suite.
5. Commit: `docs: record real-model planner results`.

## Phase 1: jobs pipeline (backend)
Build per blueprint sections 4.4, 4.5, 6, 9.1 (extend whatever already exists).
- `schemas/api.py`: Pydantic request/response models. `services/job_store.py` and `services/event_store.py` on SQLite at `data/app.db` (tables `games`, `events`; the job is persisted before processing starts). Fields: `game_id` (server UUID), prompt, status, stage, attempt, `max_attempts=3`, model id, prompt version, timestamps, error_code, artifact paths, limitations.
- `services/orchestrator.py`: explicit state machine from section 1, driven by FastAPI background tasks. Flow: `plan_game(prompt, get_provider())` -> `validate_game_ir` -> save artifacts -> QA -> (repair, see Phase 4) -> terminal state. Artifacts in `artifacts/<game_id>/`: `game_ir_v1.json` (v2, v3 if repaired), `qa_report_attempt_N.json`, `agent_trace.jsonl`, `screenshots/`. QA runs via subprocess `python -m services.qa_runner http://localhost:5173/play/<game_id>` with a 120 s timeout, killing it on timeout (error `QA_CRASHED`), and parses its JSON. Env `QA_MODE=fake` returns a canned PASS report (tests only; `real` is the default).
- Concurrency limit 1: extra jobs wait in `QUEUED`. On startup, mark any non-terminal job as `FAILED` (`INTERNAL_ERROR`, "interrupted by restart"). Provider timeout, invalid output, unsupported spec and QA crash must each end in a terminal state with a friendly message and error_code (`PROMPT_INVALID`, `MODEL_TIMEOUT`, `MODEL_HTTP_ERROR`, `QA_FAILED`, `MODEL_OUTPUT_INVALID`, `SPEC_UNSUPPORTED`, `QA_CRASHED`, `REPAIR_LIMIT_REACHED`, `GAME_NOT_FOUND`, `INTERNAL_ERROR`).
- `routes/games_v1.py`, registered in `main.py` without touching existing routes, public (no auth): `POST /api/v1/games` (202; reject empty and >1200 chars), `GET /api/v1/games/{id}` (status, stage, attempt, max_attempts, created_at, updated_at, game_url, qa_summary `{passed, failed, critical_failed ids}`, error_code, limitations), `/spec` (validated GameIR), `/qa` (latest QA report), `/events` (ordered events: ts, stage, result, detail, attempt; repair events carry rationale and before/after diff), `GET /api/v1/health` (status, provider name, model id, whether a key is configured: boolean only). Optional safe artifact download `GET /api/v1/games/{id}/artifacts/{name}` (UUID dir, whitelist file names).
- Tests (`tests/test_jobs.py`, `tests/test_orchestrator.py`) with the mock provider and a fake QA: happy path, invalid prompt, unknown id, provider timeout -> `FAILED/MODEL_TIMEOUT`, QA crash, restart recovery, concurrency queueing, no stuck jobs.
- `scripts/api_walk.py`: start the API in the background (mock provider, `QA_MODE=fake`), walk one job to READY with httpx, test the error paths, shut the server down.
- Acceptance: pytest passes, `api_walk.py` prints a PASS table. Commit: `feat(api): jobs pipeline, SQLite store, /api/v1 endpoints`.

## Phase 2: wire the frontend to the real API
- Set `VITE_USE_MOCK_API=false` in `aether-frontend/.env.local`; keep true in `.env.example`; mock stays available via env.
- Make `mockApi.ts` match the real backend's response shapes (not the reverse). Update `apiClient.ts`, `Forge.tsx` and `PlayGame.tsx` so they work with real statuses, real events, real QA reports, error codes and `READY_WITH_WARNINGS`.
- `/play/:game_id` loads the spec from the backend and must work with `?test=1` (the hook must exist for generated games, because the QA runner opens that URL).
- Forge shows: the real stages including REPAIRING with rationale and before/after diff, the QA checks list (critical pass/fail), limitations from the planner ("what we adapted"), friendly FAILED state, Retry on network failure. Keep the existing look.
- Acceptance: `tsc --noEmit` clean; `ui_smoke.py` still passes in mock mode. Commit: `feat(ui): Forge and Play wired to the real API`.

## Phase 3: end-to-end smoke (real pipeline, mock model)
- `scripts/e2e_smoke.py`: start backend (mock provider, real QA) and the Vite dev server in the background; POST a prompt; poll to a terminal state; assert READY and that every critical QA check passed; fetch `/spec`; open `/play/<id>` with Playwright and confirm the canvas renders; save a screenshot to `artifacts/e2e/`; stop both servers. Add `--live` to run one job with the real provider from `.env`, and report honestly (time, model, result).
- Run it in mock mode and with `--live`. Acceptance: both end READY or you diagnose and fix real bugs.
- Commit: `test: end-to-end smoke for prompt to playable game`.

## Phase 4: spec-level QA checks and the repair loop
A parameter patch cannot fix a runtime bug (restart, boot), so the repair loop needs failures that parameters can fix.
New critical QA checks (in `services/qa_runner.py`, using the hook and real keyboard input; mark each failed check `patchable: true`; mark the existing runtime checks `patchable: false`):
- `idle_survival_min_seconds`: with enemies active and no input, the player survives at least 4 s (wait up to 15 s; measure from `getState()`).
- `flee_bot_survives`: a simple bot steers away from the nearest enemy (use `getEnemyPositions()` and `getState().player`, steer toward the arena center near walls) and must stay alive for min(12 s, objective target seconds).
- Tune thresholds so all four demo samples pass. Add `sample-too-hard.json` (valid GameIR: about 12 enemies at speed 240, max_health 1, difficulty 5) registered at `/play/demo-too-hard`; it must fail these checks. Extend `run_qa_all.py` and `run_qa_fixtures.py` to cover them.
Repair (`services/repair.py`): `propose_repair(spec, qa_report, provider) -> RepairResult(patch, rationale, errors)`. The system prompt lists the allowed patch fields and ranges, requires JSON only, forbids changing theme, title, objective type or genre, and says the goal is to fix the failed checks with minimal parameter changes. Validate the patch (`extra=forbid`), `apply_patch`, `validate_game_ir`, reject no-op patches (one retry).
Orchestrator: when critical QA fails and all failed critical checks are patchable -> `REPAIRING` -> `VALIDATING_SPEC` -> `BUILDING` -> `TESTING`, re-running the same QA, max 2 repairs; if a non-patchable check failed, do not repair: log "needs developer" and end FAILED. Record rationale and before/after diff in events and artifacts (`game_ir_v2.json`).
- Mock provider: add a deterministic repair responder (only for `MODEL_PROVIDER=mock`, clearly labeled) so tests and the offline demo work.
- Tests: patch validation, bounds, state machine (fail, fail, pass -> READY; fail x3 -> FAILED; non-patchable -> no repair).
- `scripts/repair_demo.py`: with mock: a "repair demo" prompt produces the too-hard spec, QA fails the playability checks, REPAIRING, READY; print before/after. With `--live`: submit "an extremely brutal survival game with 40 fast enemies and only 1 health" to the real model and report honestly whether the planner produced a failing spec and whether repair fixed it (never force the outcome). The `?bug=` fixtures remain QA self-tests only; docs must say seeded faults are seeded.
- Commit: `feat(repair): spec-level QA checks and bounded repair loop`.

## Phase 5: full-pipeline evaluation
- Keep `bench/prompts.json` (10 prompts). Add `bench/stress_prompts.json` (2 prompts that should produce unplayable specs).
- `scripts/run_eval.py`: for each prompt run the orchestrator in-process (real provider from `.env`, real QA, `BENCH_DELAY_SECONDS` between prompts). Record per prompt: spec validated on first response, Playable@1 (all critical checks pass after the first build), Playable@3 (pass within 2 repairs), repair attempted/succeeded, total latency, token usage and a cost estimate if usage is present (else null with a note), failure categories (schema, rendering, interaction, objective, restart, timeout), theme/objective match, limitation honesty, and a blank `prompt_adherence_1to5` column for a human. Outputs: `artifacts/eval/<provider>_<model>_<timestamp>.json` + `.md`, and `docs/EVAL_RESULTS.md` (generated; header with date, provider, model, sample size, repair limit, check definitions; no invented numbers).
- Run it with the real provider, and a labeled dry run with the mock. Document in `docs/EVAL_RESULTS.md` how to re-run with another provider (change `.env`; filenames keep providers separate).
- Commit: `feat(eval): full-pipeline evaluation harness and first real results`.

## Phase 6: demo resilience
- `scripts/start_all.ps1` (start backend and frontend in separate windows, wait for `/api/v1/health`, open the browser to `/forge`), `scripts/stop_all.ps1`, `scripts/demo_check.py` (health, key configured without printing it, a model ping, QA on a fallback game).
- `scripts/make_fallback.py`: generate 3 saved results into `aether-frontend/public/fallback/<name>/` (`spec.json`, `events.json`, `qa.json`, `screenshot.png`): a spooky collect game, a pirate survive game, and a repaired too-hard game. Forge gets a "Load saved demo" row that replays them instantly with no API call, clearly labeled "Saved result (offline demo)".
- `docs/DEMO_RUNBOOK.md` per blueprint 15.3 (exact commands, the rehearsed prompt, what to do if the live call fails).
- Commit: `feat(demo): launch scripts, saved offline demos, runbook`.

## Phase 7: documentation
Generate from real outputs only; never invent numbers.
- `README.md` (exact Windows setup and run commands per blueprint 15.1, `.env.example` explained, key handling), `docs/architecture.md`, `docs/api-contract.md`, `docs/GameIR-v1.md`, `docs/QA_CHECKS.md` (table: id, what it checks, critical, patchable), `docs/REPAIR_LOOP.md`, `docs/LIMITATIONS.md` (one archetype, chaser only, parameter-only repair, instrumented smoke tests are not proof of fun or of solvability, free-tier rate limits, small sample), `docs/TEST_REPORT.md` (pytest, QA suites, e2e, repair demo, eval results from the artifacts).
- `docs/DOCUMENT4_OUTLINE.md`: section headings, and which doc or artifact feeds each. Use the safe claim from blueprint section 17.
- `docs/MODULE_OWNERSHIP.md`: a table of every module with its purpose, blank owner columns, and 3 "explain in your own words" viva questions per module group.
- Commit: `docs: README, architecture, API, GameIR, QA, repair, limitations, test report`.

## Phase 8: final verification
- Commit everything first. Then extract the committed tree with `git archive HEAD` into a temp folder, create a venv, `pip install -r requirements.txt`, `python -m playwright install chromium`, `pytest`; in the frontend `npm ci`, `tsc --noEmit`, `npm run build`; run `e2e_smoke.py` against the fresh copy (use different ports or stop the dev servers first).
- Run the whole suite on the working copy: `pytest`, `check_movement.py`, `run_qa_all.py`, `run_qa_fixtures.py`, `ui_smoke.py`, `api_walk.py`, `e2e_smoke.py`, `repair_demo.py`.
- Scan tracked files for secrets (`git grep -nE "AIza[0-9A-Za-z_-]{35}"`, and check `.env` is not tracked).
- Write `docs/FINAL_CHECKLIST.md` from blueprint section 19 with V/X and evidence for each line. Update `PROGRESS.md`.
- Commit: `chore: final verification and checklist`.

---

## Final report (when everything is done)
One table: phase, status, commit, key numbers (tests passed, QA results, Playable@1, Playable@3, repair success, first-response validation rate, median latency), then the list of things that still need a human (visual check of the UI, recording the backup video, writing Document 4 prose, pushing to GitHub, rehearsal).
