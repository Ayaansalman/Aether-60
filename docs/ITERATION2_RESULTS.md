# Iteration 2: generation fidelity, gameplay and creator UX

Continues the existing `codex/platformer-overhaul` branch from `dc6b507`. No deployment or push. The React/Vite/Phaser application and the original arena routes remain in place.

## Root causes and implementation

The [audit and backlog](ITERATION2_AUDIT.md) describes the original schema/runtime limitations. Three exact prompt traces were saved with fixtures and with real Gemini before changes. The ice fixture became grass; Gemini instead reported the ice mechanics unavailable. The factory silently lost its multiple stages. The old QA could pass either outcome because it checked playability rather than requirements.

Requirements now retain original phrases, model-enumerated requests, capability IDs, construction witnesses, verification check IDs, and explicit status. Construction failures, verification failures, unverified implementations and unsupported requests are different states. The pipeline stops when a requested supported feature has no construction witness. A passing browser run cannot upgrade an untested feature to verified. Repeated checks across stages must all pass. Inspector artifacts and the creator's requested-feature list expose this evidence. Model source phrases must actually occur in the submitted prompt.

The library now includes patrol, proximity chase with edge restraint, stationary ranged attacks with projectile collisions, proximity/timer icicles with warning/fall/impact/reset states, periodic machinery, one-way alternate shelves, moving platforms, checkpoints, collection, animated shrine/gate/beacon exits, slippery acceleration/braking, damage/knockback/invulnerability, and real level transitions. `behaviors.ts` contains decisions shared by Phaser and Node regression tests. No model-generated executable code is run.

Designs can choose journey, ascent, terraces or cavern composition. Section geometry, suspended bridges, optional upper shelves, collectible arcs, encounter choices, per-stage camera settings and 1–3 connected stages replace the former single composition. Seeds are deterministic. Every mandatory route is checked analytically and through actual browser jumps. Platforms duplicated by a moving route and an optional shelf are excluded during construction. Some routes still advance primarily from left to right; this is an expressive library, not arbitrary world synthesis.

Forest retains Kenney terrain, vegetation and ruins. Factory uses the industrial atlas, moving machinery and mechanical enemies. Ice uses original procedural ice blocks, cave silhouettes, crystals, icicles, relic medallions and a beacon. Requested shrines now have an actual shrine silhouette instead of the former yellow keyhole block. Sources and replacement boundaries are documented in the asset README and registry; original procedural components are not falsely attributed to Kenney's CC0 license.

The creator starts empty. Samples require explicit selection and are labeled. Generation clears the previous preview and displays persisted backend stages. Ready and failed games show their actual status. Instructions, objective counts, icon tooltips, game focus, mobile touch input and mobile page scrolling were improved. Inspector includes an explicit browser recheck that retains previous evidence and does not call the model.

## Real generation and browser verification

All three exact prompts ran through the real Gemini path using `gemini-3.5-flash-lite`. Final developer fixes were applied by rebuilding those saved typed designs with the original seeds; `DEVELOPER_REBUILD` events and before/after IR distinguish this from AI planning or automatic repair. No live job silently switched to a fixture.

| Prompt | Live stages | Final browser checks | Registered requested features |
|---|---:|---:|---|
| Forest | 1 | 16/16 | Forest composition, crystals, patrol creatures, glowing shrine verified |
| Factory | 3 | 31/31 | Industrial composition, robots, moving platforms, timed machinery, checkpoints, transitions verified |
| Ice cavern | 2 | 34/34 | Ice composition, slippery movement, icicles, relics, flashing exit beacon verified |

The separate fixture runs pass 16/16, 29/29 and 21/21 checks respectively. Fixture campaigns have 1, 3 and 1 stages. All tracked requested supported capabilities are verified in all six final reports. The three prompts have distinct geometry signatures in both modes; geometry profiles, object counts, enemy behaviors, objectives, cameras and provenance are in [quality-comparison.json](evidence/iteration2/quality-comparison.json). This comparison excludes titles and theme colors from geometry hashes.

The backend suite passes **164 tests**. The five Node behavior tests pass, frontend production build passes, and ESLint passes. The creator suite passes **20 checks**, including desktop/mobile empty states, typing, Inspector honesty, layout, seeded 503 error/recovery, normal mobile document scrolling, touch movement, restart, expanded preview and export. The 503 response is explicitly labeled test injection, not a real provider outage.

The additional actual creator submission configures icicles to fall every **1.5 seconds**; its final browser recheck passes **19/19** checks. It clears a previously loaded sample, follows real backend progress, and saves the resulting timer specifications and browser evidence in `evidence/iteration2/timer-flow/`. Model calls are not used for this explicitly selected offline fixture. The engine supports configurable intervals of 0.8–10 seconds; out-of-range explicit requests are reported as unsupported rather than silently clamped.

## Failures, diagnosis and repair evidence

- Initial browser runs exposed a destroyed collectible body being refreshed by its tween and an incorrectly registered procedural ice texture. These were developer fixes; original failed reports remain in `initial-failures/`.
- An intermediate factory run produced a real failed route check. The existing bounded repair reduced only gaps/elevation, rebuilt with the same seed, retested and passed. `intermediate-verified/factory-job.json` retains the initial QA, permitted before/after changes, diagnosis and retest. This is evidence for a narrow layout repair, not a claim that the system can repair arbitrary mechanics or generate new runtime code.
- Enlarging the exit visual exposed a QA assumption: a successful exit collision can occur before landing on the last platform. QA now records an actual destination exit collision separately from a settled landing. The failed intermediate fixture report remains in its job's original artifacts; its final re-verification passes. The harness does not hide this by claiming an airborne landing.
- Re-verification preserves original reports. Developer rebuilds are recorded separately from automatic repairs. Inspector export contains actual persisted job activity.

## Evidence and reproduction

`docs/evidence/iteration2/` contains before/after traces, live and fixture exported jobs, original failures, intermediate repair evidence, screenshots, comparison metrics, backend/build/lint/behavior logs, UI checks, and the configured-timer creator flow. Jobs still require the ignored local SQLite database to reopen by ID; exported JSON and screenshots are independent artifacts.

With backend and Vite running:

```powershell
aether-backend\venv\Scripts\python.exe scripts/trace_iteration2.py --phase audit --mode fixture
aether-backend\venv\Scripts\python.exe scripts/evaluate_iteration2.py --mode fixture
# Makes three live planning requests through the real generation API:
aether-backend\venv\Scripts\python.exe scripts/evaluate_iteration2.py --mode live
aether-backend\venv\Scripts\python.exe scripts/check_studio_ui.py --game-id <saved-id>
aether-backend\venv\Scripts\python.exe scripts/check_iteration2_generation_flow.py
cd aether-frontend
npm run test:behaviors
```

## Remaining boundaries

- Requirement extraction combines bounded explicit rules with model enumeration. It is not proof that every possible natural-language request is understood. Subjective style and fun require human review; unknown mechanics should be reported through the model's unsupported contract.
- Browser QA uses real controls, physics and collisions, but isolates route launches and uses controlled positioning for collection, traps, enemies, checkpoints and exits. It establishes functional objective completion, not a full unassisted autonomous playthrough. A manual keyboard play review also exercised forest movement and a gap jump.
- Nonlinear/backtracking worlds, switches/doors, authored boss encounters, arbitrary new mechanics, richer authored animations and audio remain future work. Only platformers are expanded here.
- Automatic repair remains confined to diagnosed layout parameters and at most two attempts. Runtime implementation defects require developer changes.
- Existing authentication, durable worker recovery and production hardening remain outside this local iteration. The inherited dependency advisories and Phaser bundle-size advisory remain; no dependency migration or external deployment was performed.
