# Iteration 8 — arcade design, difficulty and presentation

Date: 2026-10-21. Existing repository, existing runner family and v2 lifecycle. No new genre, agents, dependencies, asset downloads, provider calls, push or deployment.

## Root causes and representative trace

The previous `RunnerDesign` had speed/physics but no difficulty, motif, recovery, transition or pacing contract. The offline planner only changed speed for “fast” and acceleration for broad phrases. Factory and cyberpunk both became neon. `RunnerWorld.populate` chose one isolated primitive and used `max_speed * (full_jump_flight + .72 + random*.35)` spacing regardless of requested intensity. Flying always used 1.65 seconds plus jitter, a fixed gap height and a ±50px center random walk clamped to 180–330. `RunnerCanvas` ignored the existing CC0 catalog: four simple backgrounds, one generic obstacle color, and a square/ellipse player. The model was not the sole bottleneck.

Trace B now: original prompt → `semantic_intent.interpret` → explicit `arcade` difficulty/extreme, factory, gradual, endless constraints → `runner.plan` → typed `RunnerDesign` → `construct` → persisted `RunnerIR` → `RunnerWorld` → `ChallengeStream` and `ArcadePainter`. Original prose still reaches the live designer. Explicit semantic constraints bind omitted/contradictory designer fields, with `provider.json.intent_bindings` recording changes; custom numeric/motif decisions survive validation. `semantic_requirement_report.json.arcade_constraints` compares requested and actual values and fails mismatches. The actual local HTTP B job is READY with extreme/factory/390px/s, a .10s recovery setting, .82 precision fraction, six-element phrases and seven passing Chromium checks (`http-api.json`). Fixtures A–D exercise the complete API in tests; model-stub testing exercises preservation of custom live-designer values. No Gemini generation was performed this iteration.

## Design contract and procedural behavior

`RunnerDesign`/`RunnerIR` retain schema version 2.2 with additive fields. New designs always serialize resolved values. Difficulty selects easy/medium/hard/extreme defaults; supplied values override only the fields actually supplied, including partial challenge objects. Stable progression stops acceleration and geometric escalation; gradual raises speed continuously and ramps geometry over course distance; surge raises speed in 12-second steps while geometry ramps. The HUD exposes difficulty and actual speed.

`challenge` fields: `patterns` (mode-validated allowlist), `recovery` (.10–1.8 grounded seconds), `spacing` (.8–2.8 flying transit seconds at maximum speed), `precision` (.2–.85 fraction of safe jump travel), `transition` (10–170px maximum desired center change), `sequence_length` (2–8), `rest_every` (2–8 phrases). Ground families and exclusions remain typed. Contradictory flap passage exclusions fail validation. Unavailable special mechanics remain in `unsupported`; pixel is the implemented visual style.

Ground motifs: single precision jump, rhythmic repeated jumps with alternating recovery, escalating widths, mixed family phrases and recovery sections. Flying motifs: single, alternating high/low, ascending, descending, nearly level precision corridor and recovery. Seeded shuffled motif bags ensure coverage without immediate repeated motifs; phrase lengths, dimensions, family combinations and recovery intervals vary. Scheduled rests honor the configured motif list. This extends reusable parameterized archetypes rather than generating executable code.

Both modes retain finite distance finish and endless continuation. Pending phrases have at most eight obstacles; the active horizon is 1250px and old objects are removed. Restart restores seed, sequence, score and physics, while retaining best score for the mounted game session. Existing public runner/flap examples now serialize challenge settings too. Legacy frontend specs without `challenge` retain their old stream for compatibility; backend-parsed old specs receive resolved defaults.

## Fairness and controls

Ground validation uses apex `I²/(2g)`, flight `2I/g`, and the clearance interval above each actual obstacle height. Widths use minimum speed, the 28px collision diameter and a 4px vertical reserve; independent jump separation uses maximum speed, full flight time and configured landing/reaction recovery. Gap widths use the zero-height envelope. Testing performs actual fixed-step grounded jumps across generated sequences at both speed endpoints, for 12 seeds per ground scenario and 24 obstacles per run.

Flying first validates that the gap fits a complete repeatable ballistic flap cycle plus collider/margin. Each planned gate then runs a bounded beam search: flap/no-flap choices at 30Hz, four semi-implicit substeps per choice (at most 1/120s), the actual impulse/gravity, screen bounds, collider and the whole gate slab. Up to 64 position/velocity states survive. Exit states carry forward, without resetting velocity or teleporting to the next center. Searches run at configured minimum and maximum speed. Failed searches add transit time and reduce height change, for at most seven attempts; remaining failure is explicit rather than emitting a known impossible gate. Fifteen seeds per flying scenario retain witnesses through at least 35 gates. The supplied comparison fixtures needed no repairs.

These are practical checks, not a general solver or proof for every intermediate/time-varying speed. Beam pruning can reject feasible layouts. Human reaction/learning is not modeled. Recovery is intentionally tight on extreme. Ground input now buffers jumps for 100ms before landing; airborne flap remains immediate. Death rotates the player, briefly shakes/flashes the border and shows a compact retry panel. R/Space/tap restart, once-per-passage scoring, distance, session best, action trails, motes and player animation are implemented. Audio was not added.

## Art selection and actual comparison

`presentation.ts` selects the existing Kenney CC0 terrain/industrial atlases and forest/industrial/twilight backgrounds, with nearest-neighbor pixel scaling. Forest uses grassy/dirt terrain, trees and woodland fox animation; factory uses metal/hazard surfaces, girders, pipes/fan shapes and a two-frame character; neon has lit architecture; sky has cloud layers and bird flap/tilt; ice has cavern silhouettes, frost geometry and distinct pale gate edges. Bird/fox/ice/accent drawings are original project-source primitives. The selected theme controls composition, ground, obstacle surfaces, decoration and palette, not only clear color. No new license or asset pack is claimed. Some geometry remains deliberately simple pixel artwork.

Seed 7, first 40 obstacles, unweighted means (spacing excludes obstacle width):

| Fixture | Initial → cap speed px/s | Base flap gap px | Mean width px | Mean spacing px | Pattern types |
| --- | --- | --- | --- | --- | --- |
| A easy forest ground | 210 → 280 | — | 22.9 | 583.1 | 5 |
| B extreme factory ground | 390 → 500 | — | 145.2 | 523.5 | 5 |
| C beginner sky flight | 210 → 280 | 240 | 48.1 | 722.4 | 6 |
| D extreme ice flight | 390 → 500 | 112 | 47.0 | 558.5 | 6 |

Flying gaps initially include up to 19.5px of introductory margin, removed with progression, plus 25px in recovery sections. These are deterministic fixture measurements, not live Gemini output. Seed 23 also changes actual geometry and motif order for each scenario, not just metadata. Detailed measurements: `evidence/iteration8/comparison.json`.

## Verified results and limits

- 93 focused backend tests pass: iteration 8/7, platformer API/fidelity, adventure, iteration 6 and gameplay systems. The final 10 iteration-8 tests also pass after the last schema/binding changes.
- 29 frontend tests pass across arcade, platformer behaviors and adventure state. Final arcade-only rerun: 6/6. Tests cover deterministic continuation/cleanup, finite termination, physics, contrasting geometry, once-only scoring, collision, restart, best score, stable progression and distinct art roles.
- TypeScript/Vite production build, ESLint and Python `compileall` pass. Existing Phaser chunk advisory and two Python dependency deprecation warnings remain. The backend has no separate distributable build step.
- Actual Chromium functional checks: A 7/7, B 7/7, C 9/9, D 9/9. These include real input and explicitly controlled state for bounds/collision/scoring, plus accelerated spawning. A finite ground fixture additionally passes 7/7, including stopped generation rather than an erroneous endless requirement.
- Separate approximately 12-second real-keyboard runs used read-only telemetry to decide Space presses, with no position/velocity/collision overrides. All four survived; A/B traveled about 2597/4897px, C/D passed 3/7 gates. This is scripted controller evidence, not human playtesting or full-course completion. Screenshots of all four presentations were inspected.
- Mobile-sized Chromium pointer checks pass for A/D; screenshots were inspected. Physical touch hardware, audio, long sessions, broader custom physics combinations and subjective fun remain unverified.
- The local backend process was identified as this checkout's uvicorn, confirmed idle, and restarted. One actual HTTP offline B generation completed READY with 7/7 subprocess browser QA. No live provider usage/cost, push or deployment.

## Reproduce

From repository root, with the frontend on 5173:

```powershell
aether-backend/venv/Scripts/python.exe scripts/prepare_iteration8.py
aether-backend/venv/Scripts/python.exe scripts/check_iteration8.py
aether-backend/venv/Scripts/python.exe -m pytest aether-backend/tests/test_iteration8.py aether-backend/tests/test_iteration7.py aether-backend/tests/test_platformer_api.py aether-backend/tests/test_platformer_fidelity.py aether-backend/tests/test_adventure.py aether-backend/tests/test_iteration6.py aether-backend/tests/test_gameplay_systems.py -q
```

From `aether-frontend`: `npm run build`, `npm run lint`, and `node --experimental-strip-types --test tests/iteration8.test.mjs tests/iteration7.test.mjs tests/platformer-behaviors.test.mjs tests/adventure-state.test.mjs`. Prepare the deterministic specs before the iteration-8 frontend tests. Evidence is portable in `docs/evidence/iteration8`; the local HTTP job link depends on the ignored local database.
