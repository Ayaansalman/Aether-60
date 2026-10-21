# Iteration 7 — semantic composition and arcade runners

Date: 2026-10-21. Continued the existing application and v2 lifecycle; no replacement project, external deployment, push, dependency installation or new asset pack.

## What blocked fidelity

Inspection of the current code and recent iteration-4/5/6 commits found that `game_factory.genre_for_prompt` used phrase routing with a platformer default; platformer construction always distributed crystals and rejected bosses; adventure environments were specified once per area; the platformer guard could override model topology/enemies using broad phrase rules. Existing Gemini designers, strict Pydantic contracts, asset selection, persisted jobs, browser QA and bounded repair were already functional. This iteration extends those boundaries rather than replacing the application.

## Implemented

- Live requests now start with a genuine configured-provider semantic interpretation. It chooses the family/control/central loop and records verbatim source phrases, capability IDs, dependencies, counts, biome types, same-level scope and verification intent. Deterministic phrase parsing remains explicitly labeled fixture behavior. Semantic interpretation is supplied to the existing validated genre designers; no model-authored code executes.
- `semantic_requirement_report.json` maps registered requirements to IR paths, construction witnesses and specific runtime checks. Root genre/control mismatches and missing represented requirements fail fidelity. Validated exclusions are distinguished from observed runtime behavior; sword melee and visual style can remain approximations. The creator and Engineering Inspector expose this report. Re-verification also recalculates it. This does not certify requests the interpreter omitted.
- A separate strict RunnerDesign/RunnerIR (v2.2) and runner adapter share the existing API, jobs, seed, creator preview, blueprint, Inspector and verification lifecycle. No platformer levels are added to endless games.
- The runner simulation uses fixed 120 Hz steps. Ground mode provides automatic motion, grounded-only jump, spikes, gaps, lasers and optional barriers. Flap mode provides gravity, repeated airborne impulses, scrolling paired barriers and once-per-gap scoring. Both support keyboard/pointer input, immediate restart, collision/bounds loss, finite finish, seeded continuing generation, speed curves, active obstacle cleanup and original procedural art. Spacing uses maximum speed and jump flight plus a landing/reaction margin; the schema rejects insufficient jump/barrier clearance. Themes have city/forest/sky/ice presentations.
- Typed boss encounters build one bounded arena, one knight boss, no collectible/exit objectives, a health bar, alternating telegraphed charge and three-projectile volley, cooldowns, faster second phase, hit feedback, player/boss damage and direct defeat victory. Receiving hits does not reset the boss attack clock. Sword melee is explicitly approximated by existing F/X projectile combat. A validated encounter invariant rejects extra arena entities and invalid victory targets. Ordinary platformer combat remains separate.
- Adventure areas now contain typed nested biome rectangles. Later regions take priority. Forest can surround a frozen lake and icy ruins within one traversable map. Actor region references place a villager in forest and a crystal in ruins. Existing connected paths and ordered quest/resource validation remain active. Incompatible trees are removed from frozen regions; local terrain/atmosphere/ruin decoration is rendered. Slippery acceleration/coasting applies only where `slippery=true`; snow visuals alone do not change movement.
- Model-invented unsupported warnings for instantiated, registered biome capabilities are removed by an explicit, recorded guard. Unknown limitations are retained. Original live responses and the guarded saved-design retest are preserved.

## Focused verification

| Scenario | Deterministic Chromium result | Verified scope |
| --- | --- | --- |
| A boss duel | 8/8 | One boss, health bar, charge, volley, real F projectile damage, real player collision damage, final-hit victory, R restart |
| B mixed biome | 19/19 | One map, real keyboard crossing into lake, slippery coasting, assets/movement/collision, NPC talk, crystal inventory, delivery, completion/restart |
| C auto-runner | 7/7 | Auto motion/jump, bounds and obstacle death, restart, distance score, continuing bounded obstacle stream, browser errors |
| D flap | 9/9 | Airborne repeat flap, pointer impulse, bounds/obstacle death, once-per-gap score, restart, continuing bounded stream, browser errors |
| Existing platformer | 18/18 | Original saved forest fixture and existing runtime QA |

The browser tests disclose controlled placements, attack clocks and final boss HP. Scoring/collision stream checks also use controlled state. They are functional runtime checks, not autonomous full playthroughs, an enjoyment score or proof every random course is easy. Screenshots were inspected for distinct presentation; full visual polish remains manual work.

Backend focused selection: **83 passed** (iteration 7, platformer API/fidelity, adventure, iteration 6 geometry and gameplay systems). Shared frontend state/behavior/runner/biome tests: **23 passed**. Production TypeScript/Vite build and ESLint pass. Two inherited Python deprecation warnings and the existing Phaser chunk-size advisory remain. No exhaustive whole-project audit was run.

Two actual Gemini end-to-end jobs were run for **D and B**, each with semantic interpretation plus typed design (four logical completions through configured `gemini-3.5-flash-lite`; provider transport retry behavior was not separately audited). Both passed browser checks. B's original job retained two invented unsupported warnings; the saved real-model design passed 19/19 after the recorded guard, with no additional model calls. A and C did not receive live Gemini checks. The updated API also generated C offline; actual creator submission, correct runner labels, semantic Inspector, mobile tap and browser error checks pass 5/5 and are recorded separately in `evidence/iteration7/creator/`.

Initial evidence includes a stale-server C submission and test-timing failures. Port 8000 was confirmed to be Aether's existing uvicorn process, then restarted with updated code after isolated-port testing. The obsolete result is labeled `stale_server_result.json`; it is not counted as a successful runner test. Restart QA allows a few rendered frames of new distance after the real key press; pure simulation tests verify the exact zeroed reset.

## Reproduce

From repository root, with the backend on 8000 and frontend on 5173:

```powershell
aether-backend/venv/Scripts/python.exe scripts/check_iteration7.py
aether-backend/venv/Scripts/python.exe scripts/check_iteration7_creator.py
aether-backend/venv/Scripts/python.exe scripts/retest_iteration7_live.py
aether-backend/venv/Scripts/python.exe -m pytest aether-backend/tests/test_iteration7.py aether-backend/tests/test_platformer_api.py aether-backend/tests/test_adventure.py aether-backend/tests/test_platformer_fidelity.py aether-backend/tests/test_gameplay_systems.py aether-backend/tests/test_iteration6.py -q
```

From `aether-frontend`, run `npm run build`, `npm run lint` and `node --experimental-strip-types --test tests/iteration7.test.mjs tests/platformer-behaviors.test.mjs tests/adventure-state.test.mjs`. `scripts/check_iteration7_api.py fixture C` checks the actual API without a provider call; its explicit `live` option invokes the configured provider and should be used sparingly.

## Limits and manual playtesting

- Semantic understanding is bounded by the registered contracts; omitted or incorrectly interpreted prose is still possible. The shared requirement registry intentionally does not cover every legacy mechanic. Unsupported families fail rather than silently becoming platformers. Model defaults and the older platformer guard still constrain some designs.
- Initial boss support is a single arena/knight presentation with two controlled attack patterns, not arbitrary authored bosses or a campaign boss placement system. Sword melee is not implemented. Platformer same-level regional biomes are not implemented; region support is in adventure maps.
- Adventure regions are rectangles with deliberate nested overrides and simple procedural atmosphere/ruin accents, not authored blended tile transitions. Existing linear quests, forward area progression and stationary NPC limitations remain.
- Runners have original simple art, no audio, four ground obstacle primitives and paired flap barriers. Finite finish and speed curves have simulation tests; prolonged human survival, mobile hardware performance and subjective difficulty remain unverified. The active-world tests accelerate generation rather than simulating hours of browser play.
- The frontend offers the existing sample catalog plus Neon Overdrive (ground auto-runner) and Cloudwing (tap-to-flap), with saved offline fixtures, sidebar buttons and landing-page cards. Direct links are `/studio?example=auto-runner` and `/studio?example=flap`. New systems are also reached by the real Generate workflow. Saved job URLs rely on the ignored local database; exported designs/reports remain portable.

Next manual checks: play A without state injection to assess boss telegraphs and projectile aiming; complete B by walking the whole collection/return path and compare stopping on forest versus ice; play C through speed increases and each obstacle kind; play D on keyboard and a physical touch device for several minutes. Adjust pacing only from those observations, retaining the physics constraints.

Evidence: `docs/evidence/iteration7/`. This report distinguishes live provider designs, deterministic fixtures and saved-design retests.
