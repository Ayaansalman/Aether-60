# Presentation readiness follow-up — 2026-10-22

Scope agreed with the user: generation progress inside the preview, release to play only after successful QA, actionable errors below the preview, and existing provider fallbacks. Likes, comments, publication, account integration and social database migration are deferred. No dependency or schema migration was introduced.

## Changes

- Studio now displays persisted backend events inside the game frame: interpretation, planning, asset selection, validation, construction, browser QA and repair. No fabricated percentages or simulated stages.
- A public generated game mounts only when its job is READY/READY_WITH_WARNINGS, QA is PASS, and core semantic/requirement reports do not fail. Missing/unavailable QA remains visibly unverified; warnings and presentation limitations remain available.
- Exact failure events, critical QA check names and failed mandatory requirements appear below the frame. Users can inspect diagnostics, regenerate, rerun QA, or reconnect to the same saved job after a connection error. Reconnect does not spend another model request.
- Browser QA uses `/studio/verify/<id>` to mount the same runtime before public release. Stored user URLs remain `/studio/play/<id>`. This QA route is a testing entry point, not an authorization/security boundary.
- Three browser adapters now resolve the same saved specification from both playback routes. Initial integration caught this: platformer QA mistakenly loaded the forest sample (wrong exit indicator/enemy assumptions), while adventure QA looked for a missing `example` parameter. The corrected platformer/adventure/composition adapters passed actual HTTP pipeline tests.
- The existing bounded provider fallback implementation is enabled/configured. Primary remains `gemini-3.5-flash-lite`; fallback order is `gemini-3.5-flash`, then `gemini-3.8-flash`. Job-scoped sanitized fallback events are persisted and displayed without changing the active generation stage. API failures have readable recovery messages without returning upstream response bodies.

## Verification

- 66 focused backend tests pass: generation presentation, provider transports, Iterations 7 and 10. After ordering the live-verified fallback first, the four presentation/config tests were rerun and passed.
- 43 frontend behavior/state tests pass; generation tests, ESLint, TypeScript and production build pass again after the final reconnect wording change. Existing Phaser bundle-size warning remains.
- 12 controlled-response Chromium UI checks pass: early IR stays hidden, TESTING/REPAIRING stay hidden, QA PASS unlocks runtime, failures are below the canvas, unavailable QA remains blocked, fallback disclosure, reconnect without POST, QA route, saved examples, mobile width, and no page exceptions. Actual React/Phaser rendering and browser input are used; backend responses in this suite are controlled fixtures.
- Five independent fixture HTTP generations on isolated backend/frontend ports pass actual browser QA and then become playable at public URLs. The observer saw TESTING for all five and no public canvas during that state:

| Family | Final status | Browser checks |
|---|---|---:|
| Runner | READY | 10 |
| Platformer | READY | 13 |
| Quest adventure | READY | 17 |
| Boss duel | READY | 11 |
| Compositional survival | READY | 11 |

These QA checks include real keyboard/collision/interaction probes with the existing disclosed controlled positioning/state where needed. They do not prove autonomous playthroughs, aesthetic quality or arbitrary live-prompt generation success.

The authenticated provider catalog listed both fallback model IDs. Four tiny live completion probes were used, with no full game generations: a 32-token probe timed out on 3.8 and yielded no visible content on 3.5; repeating the production payload without the token cap returned usable content on 3.5 in 1.88 seconds, while 3.8 again timed out. Thus **3.8 is configured but not verified usable**. A successful 3.5 response is not a guarantee against later quota/provider outages. No further probe retries were made. Deterministic transport/job tests exercise actual fallback switching and safe event delivery.

Evidence: `evidence/presentation-ready/pipeline.json`, `fallback-live.json`, `ui/report.json`, and screenshots. Initial adapter failure summaries are retained in `pipeline-initial-failures.json`. Existing Iteration 10 evidence and supported/unsupported mechanic limits are unchanged.

## Reproduction

Run the frontend on 5173 for the controlled UI suite:

```powershell
aether-backend/venv/Scripts/python.exe scripts/check_generation_presentation.py
```

For the full fixture pipeline, run backend 8001 with isolated `AETHER_DB_PATH`, `AETHER_ARTIFACTS_DIR` and `AETHER_FRONTEND_URL=http://127.0.0.1:5174`; run Vite 5174 with `AETHER_BACKEND_URL=http://127.0.0.1:8001`, then:

```powershell
aether-backend/venv/Scripts/python.exe scripts/verify_presentation_pipeline.py
```

Both scripts use zero fresh model completions. Live model probes are evidence only and are not part of routine test scripts. No push or deployment was performed for this follow-up.

The idle main backend was restarted with the final code/config on port 8000; the original frontend remains on 5173. Existing runner job `00650aae-0bfc-4aed-a5ba-1799bd7b1dd1` still opens as READY_WITH_WARNINGS / QA PASS, renders one canvas and responds to actual Space input without page exceptions. Isolated verification servers were stopped. Runtime databases/cache/build outputs were excluded from the source checkpoint.
