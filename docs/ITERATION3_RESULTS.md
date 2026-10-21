# Iteration 3 — level design and campaign progression

Completed locally on 2026-10-20, continuing from `1faa7a6`. No push or deployment.

## Implemented

- `GameDesign.levels` now accepts up to three typed `LevelDesign` specifications. A populated list must match `level_count`. Each level controls its title, theme, topology, difficulty, sections, objectives, slippery terrain, icicles, machinery, moving platforms, checkpoints, exit presentation, collectible type and briefing. Omitted settings inherit campaign defaults; explicit `false` disables a mechanic for that level.
- The planning schema and model instructions expose these controls. Persisted GameIntent includes the interpreted count and level progression, followed by model design, guarded design and runtime IR as before. Campaign-wide exclusions do not overwrite later encounters when an exclusion belongs to an introductory level.
- The deterministic compatibility planner expands older multi-stage designs into introductory horizontal routes, ascending sections and a final combination. Fixture interpretation recognizes two/three, digits, hyphenated counts and explicit first/second/final mechanic introductions, including reversed introduction orders. Explicit model specifications bypass this fallback.
- Reusable section challenges alter construction: precision sections narrow the landing, combat sections reserve wider encounter space, exploration adds elevated collectible shelves, and moving sequences reuse the existing moving platform system. Existing section elevation requests are honored. Introductory sections, lengths, gaps, encounters and checkpoint placement differ across the fallback progression.
- Optional collectibles retain their actual supporting-platform references. Collection gates can be satisfied entirely on the main route. Checkpoints precede demanding sections. Slippery routes use shorter gaps; enemy placement reserves departure space, and precision sections with enemies allow extra room.
- Runtime level resolution applies the current theme, physics modifier, objective, camera and exit settings. Older saved levels with missing/null settings still inherit defaults. Transitions freeze physics, fade to the next scene and display a completion message. Level-start briefings wrap within the canvas; the HUD shows `Level n/total` and that level's collection objective.
- Transitions restore campaign health and reset level-local collectibles, checkpoint and trap/enemy state. Falling respawns within the current level and preserves its collected items. Exhausting health ends the journey. R and the restart toolbar restart the campaign at level one, including after victory/loss. Physics explicitly resumes when rebuilding a scene.
- Layout repair now updates explicit level sections as well as campaign defaults. Validation checks every level's ballistic edges, main-route objective supply, entry/exit and entity support references. Capability evidence searches all levels for environmental and slippery mechanics.

## Verification

| Check | Result |
| --- | --- |
| Full backend pytest suite | 190 passed; two dependency deprecation warnings |
| Frontend production build | Pass; existing Phaser chunk-size advisory remains |
| ESLint | Pass |
| Shared runtime decision tests | 6 passed |
| Three-level ice fixture | 26 Chromium checks passed |
| Saved Gemini three-level ice design | 40 Chromium checks passed |
| Two-level industrial fixture | 30 Chromium checks passed |

The acceptance prompt was:

> Create a three-level ice platformer. The first level introduces slippery terrain, the second introduces falling icicles, and the final level combines both mechanics with difficult platforming.

Both ice designs produce slippery/no-icicle introductions, icicle development levels, and final levels combining both. Their per-level geometry differs. The fixture and Gemini layouts are also different from each other. Chromium verified keyboard movement/jumps, route landings, later-level icicle warning/fall/collision/damage, checkpoint respawn, objective overlaps, both scene transitions, full-game victory, final-level loss and keyboard restart after both victory and loss. The factory case also covers existing dash, robots, moving platforms, collectibles and later-level machinery.

Two live planning invocations were made against the configured Gemini `gemini-3.5-flash-lite`: the first returned HTTP 503/high demand; the second returned the saved typed design. Subsequent verification rebuilt that saved design locally and made no further model calls. The original model design remains in `evidence/iteration3/live/model_design.json`; `generation.json` explicitly identifies saved-design rebuilds. No new artwork or asset downloads were needed.

Initial browser failures are retained in `qa_initial.json`, `qa_second.json` and `qa_third.json` where applicable. They exposed departure-edge encounters, insufficient ice braking in the QA driver, a shooter probe over a gap, and a locked-exit probe that could incidentally pick up a collectible before the fresh-level assertion. These were corrected through construction changes and accurately positioned/controlled browser checks. No successful checks were fabricated from validation equations.

Screenshots were visually inspected, including the ice introduction, later levels and wrapped final briefing (`live/qa/stage-3-wrapped.png`). The browser fixture transport leaves the existing creator sample label/prompt visible; it is a test injection of the saved JSON into the actual preview/runtime, not a claim that the screenshot shows a new creator submission.

## Reproduce

Start the existing frontend on port 5173, then run from the repository root:

```powershell
aether-backend\venv\Scripts\python.exe scripts\verify_iteration3.py
aether-backend\venv\Scripts\python.exe scripts\verify_iteration3.py --case factory
# Reuse the saved real design without a provider request:
aether-backend\venv\Scripts\python.exe scripts\verify_iteration3.py --live --saved-design
# Optional: explicitly make a new live planning request:
aether-backend\venv\Scripts\python.exe scripts\verify_iteration3.py --live
```

Tests: run `.\venv\Scripts\python.exe -m pytest tests -q` from `aether-backend`. Frontend commands remain `npm run build`, `npm run lint`, and `npm run test:behaviors` in `aether-frontend`.

## Scope

Chromium uses controlled launch positions for individual route edges and controlled overlaps for objectives/checkpoints. These are real physics and state transitions, not full autonomous unassisted playthroughs. Ice route tests actively countersteer to brake. API lifecycle tests validate persistence and repair with explicitly stubbed browser reports; the separate browser runs accept the actual generated IR at the preview's JSON boundary.

Levels remain connected side-scrolling routes with ascending segments and optional elevated routes. Arbitrary room graphs, mandatory moving-platform-only routes, other genres and full natural-language semantic coverage remain outside this iteration. Fixture interpretation is bounded and labeled offline; the live model can specify the individual level designs. The existing licensed asset registry, creator UI, backend services and v1 runtime remain in place.
