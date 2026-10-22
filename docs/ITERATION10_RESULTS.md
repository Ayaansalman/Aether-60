# Iteration 10 — generation reliability and targeted gameplay repair

Date: 2026-10-21 (America/Denver). Baseline: `b8eba0b6`, after Iterations 8–9. Existing SQLite records, artifacts, recent commits, family planners, validators, construction, orchestration, QA and runtimes were inspected before changes. No new genre, agent fanout, dependency, asset download, deployment or legacy survival renderer was introduced.

## Production failure evidence

The actual playtest jobs were present. Original jobs remain unchanged; relevant JSON snapshots are committed in `evidence/iteration10/source-*.json`.

| Scenario / job | First incorrect representation and exact failure | Correction |
|---|---|---|
| Factory `cada5d84-b3f3-443e-9bca-1960dc02a335` | GameDesign contained sources at sections 2/6 and a shared door at 5, in both defaults and its explicit level. One model correction fixed `unlock.count`, but the design schema checked counts/shared gate identity without checking section precedence. Construction threw before the route-repair loop existed. | Recorded local dependency repair moves the second source to section 4, retains both sources/shared gate, validates the design before construction, then checks route geometry, references and runtime progression. Invalid unprepared designs now fail at the schema boundary. |
| Garden `8f4b3d57-c1af-412b-80fa-ab5253b23d3e` | Semantic intent copied all six biome enum values (including dark/garden/lake), despite requesting forest and frozen ruins. The design correctly had forest/icy ruins, two flowers and an atomic return. Fidelity required all six invented biomes and rejected construction. | Source-ground biome metadata; snowy ruins satisfy the snow terrain family. Core biome/physics/quest/no-combat requirements stay mandatory. The environmental-animation limitation was **not the original hard blocker** and remains visible. |
| Boss `751b349e-9abc-4261-99c8-87957c97ba86` | Explicit-phrase audit treated a boss's ranged attack as an ordinary shooter; it reported missing supported requirements before semantic auditing. The intent also attached dark biome metadata to a single-level constraint. Other attempts (`7755721b…`, `54a0d383…`) invented top-down spawn Gameplay for platform controls or invalid attack components. | Boss volley witnesses satisfy ranged attacks. Biome checks apply to biome requirements. Nonempty incompatible behavior configurations receive the bounded semantic correction; they are not silently erased. Three configured attacks are now represented and audited. |
| Runner `78fc55b5-a02f-4817-bdd8-f80cf1e6b880` | Browser QA passed, but forest biome metadata on `endless_obstacles` and `visual_theme` was audited against nonexistent adventure regions. The job was FAILED despite working arcade behavior. | Capability-specific biome auditing. Existing runner restart is no longer accepted as an unsupported feature. Explicit model tuning remains intact. |
| Guardian `ffaaa295-1fd1-49b6-8aa3-fce2da7a064f` | Failed before design: platform ice used top-down-only `slippery_region`; icicles were mislabeled patrol enemies. Independently, the actual engine cannot construct switch-controlled boss immunity or a traversal route followed by its dedicated boss arena. | Source-ground platform ice/icicle bindings. Explicit `boss_shield` and arena-composition diagnostics now identify the actual unsupported relationships before paying for a design. No switches, shield or traversal requirements are silently removed. |

Additional earlier interpretation failures included null verification descriptions and abbreviated source quotes. Verification descriptions now allow null because the capability registry owns executable check IDs. Abbreviated quotes are expanded only through ordered original words into an exact original substring; invented synonyms still fail. Raw successful candidates and undecodable response text are retained for future diagnosis. The original Garden malformed response text was unavailable in its old artifact; its parser diagnostic and second candidate are retained, without guessing the formatting defect.

## Repair, severity and traceability

- Deterministic dependency correction runs inside the existing design boundary, before GameIR construction. It clamps invalid indices, handles shared gates together and retains every source. Changes include field paths, before/after values and failed invariants; the original prompt and raw candidate remain available. No additional model call is needed for these local corrections.
- Adventure prerequisites use a stable topological quest ordering for existing same-area keys, switches, unlocks and deliveries. Same-area return visits remain possible. Missing resources, cyclic dependencies, invalid references and unsupported cross-area return structures still fail honestly. Existing flood-fill and ordered inventory validation remain active.
- One semantic/design model correction per boundary and the existing bounded route-repair budget remain. No additional AI agents or whole-design regeneration loop was added.
- Exclusions are mandatory. Supported mechanics cannot become presentation-only or optional without an explicit optional clause. Source-grounded quantities avoid invented counts. Mandatory unsupported gameplay fails fidelity; presentation limitations remain warnings. Named failed runtime checks remain failures.
- Stable semantic requirement IDs are stored before browser construction and survive final reports and explicit re-verification. Legacy phrase-extractor evidence remains separate so it cannot reinterpret semantic IDs as unknown features.
- Inspector rows distinguish presentation, construction failure, runtime failure, approximation and unverified implementation. READY_WITH_WARNINGS continues to expose actual limitations.

## Spatial and runtime changes

Survival had been routed into the same fixed woodland hub/clearing grammar used for quests. Seeds mostly changed scatter decoration, rather than its topology. The modern adventure builder now resolves `AreaDesign.layout`: seeded open fields, distributed cover, connected chambers/passages and woodland obstacles. Explicit layout selections win; otherwise general spatial prompt terms select the grammar. Chamber rendering uses the existing coherent indoor tiles instead of hedge walls. Starts reserve clearance; geometry and valid spawn availability are validated across 12 seeds per layout. Numeric health, volley timing, spawn lifecycle and scoring remain unchanged. No Laboratory-specific authored map was added.

Two-switch links now optionally enable existing moving platforms and disable timed machinery. The actual runtime starts controlled platforms still and keeps disabled hazards off after activation. **Factory remains an approximation:** moving platforms are alternate routes, with a traversable static main route; timed machinery represents the requested laser barrier. This is disclosed in the job's limitations and semantic report. It does not prove an exclusive switch-dependent pit crossing or a literal laser security wall.

Boss encounters support charge, volley and an optional telegraphed ground slam with two low shockwaves. Configured patterns determine the real state machine; a requested count of three is checked. Procedural lean/windup poses, named dodge/jump warnings, half-health aggression, hit/defeat feedback, a smaller HUD and brief title banner improve readability. Seeded arena width, supported floor geometry and coherent pavement improve the encounter without inventing sprite frames. The boss remains a simple existing procedural knight texture; this is not an authored animation/art overhaul or true melee implementation.

Runner toolbar restart previously rebuilt the canvas while focus remained on the toolbar button, pausing simulation and rejecting game keys. Restart now restores canvas focus; an engaged game can recover from body focus while input fields remain isolated. Phaser adapters also queue a short R keydown so it cannot disappear entirely between update frames. Ground obstacle separation now uses a conservative speed bound at the course position rather than eventual maximum speed from the first obstacle. Profiles, model tuning, motifs, exclusions, ballistic bounds, flap search and cleanup are preserved.

## Verification and its limits

| Case | Final observed evidence |
|---|---|
| Laboratory A | 12/12 Chromium checks: four health, three shots 500 ms apart, natural scheduler/AI/projectiles and actual damage/restart. Separate real-time 60-second run reaches victory at 60.000 s, stops score and restarts. Player teleports evade threats; health and attack clocks are unchanged. |
| Alternate survival layout | Open field 12/12 Chromium. Same mechanics/seed produce different chamber/open geometry. 48 seeded layout configurations pass connectivity/start/spawn checks. Chasers retain local pursuit; global enemy pathfinding through chambers is not claimed. |
| Factory B | Captured original invalid design through persisted HTTP lifecycle: READY_WITH_WARNINGS, 17/17 runtime, semantic WARN. Both switches, first-source motion, second-source hazard shutdown, still-locked partial gate, collision/progression and completion/restart are observed. |
| Garden C | Captured original design: READY_WITH_WARNINGS, 22/22 runtime, semantic PASS. Same-world biome crossing, local slippery movement, two flowers, atomic delivery, no enemies/combat and completion/restart pass. Visual transition/environment animation remains limited. |
| Boss D | Captured exact prompt through persisted HTTP: READY_WITH_WARNINGS, 12/12 runtime, semantic PASS. One boss, three attacks, half-health acceleration, real player/projectile damage, defeat-only victory and restart. Boss clock, positions and final HP are controlled in isolated probes. Fresh boss-model reliability was not statistically tested. |
| Runner E | Easy and saved extreme each 10/10 browser checks. Actual toolbar, Space retry, body-focus recovery and editable isolation pass. Separate real-keyboard 12-second runs survive with five/six jumps and no state overrides. Easy starts at 210 px/s; saved extreme at 340 px/s (its custom values are preserved). Generated geometry/reaction-time tests independently distinguish the easy/extreme profiles. No prolonged human difficulty/enjoyment claim. |
| Guardian F | Correctly BLOCKED before design, including through HTTP. Switch-controlled boss immunity and traversal-plus-boss composition remain unsupported. Platform ice, moving platforms, icicles, ordinary switch/door dependencies and dedicated boss attacks are independently supported. |
| Existing platformer | 18/18 Chromium regression checks pass. |

142 distinct focused backend tests pass (141 selected-suite checks, followed by 49 affected checks including the new identity/re-verification regression). 38 frontend state/behavior tests, TypeScript/Vite production build and ESLint pass. The unrelated full legacy backend suite was not run. Existing Python deprecations and Phaser bundle-size advisory remain.

Initial failed probes are recorded in `initial-observations.json`: a two-endpoint sine-motion measurement missed real motion; it now samples a range. A quick Phaser restart was missed and fixed. API typing isolation initially tried to focus the disabled creator prompt; the probe now uses a real temporary textarea only while that field is disabled. These corrections retain real input/physics assertions. The initial API failure report is archived separately.

Screenshots for Garden, factory, boss, chambers and arcade were visually inspected. They are functional evidence, not an aesthetic certification or an autonomous full playthrough.

## Live Gemini budget and persisted results

Six fresh logical provider completions total, using configured `gemini-3.5-flash-lite`, with fallback disabled: Garden interpretation/correction (2), Factory interpretation/design/correction (3), then one Garden design after recovering its saved interpretation (1). Transport retries were not independently counted.

**Both initial fresh jobs failed.** Garden exposed an abbreviated cross-sentence quote; Factory labeled “No collectible requirements” unsupported. Their original results remain in `live-garden/` and `live-factory/`. After targeted corrections, saved-decision recovery through the actual HTTP/background-job/browser pipeline produced:

- Garden `89d9b78e-15eb-4000-bfe4-fe69eb64a1e1`: READY_WITH_WARNINGS, 22 browser checks, semantic PASS; one fresh designer completion during recovery.
- Factory `66483172-ae69-41c6-b8e5-509985a7a738`: READY_WITH_WARNINGS, 17 browser checks, semantic WARN; zero fresh recovery calls.

These recovered successes are not counted as two clean fresh-from-scratch generations. Subsequent historical decision replays use zero fresh provider calls. The sample is too small to estimate a production success rate.

Playable local replay IDs: factory `0e5fe401-0241-4d3c-96b9-db2bd14b7d71`, Garden `1d14eb4b-d7a4-4d0f-8084-0050569a14db`, boss `233e0260-9f49-4b98-a811-19caea4bf08c`, runner `00650aae-0bfc-4aed-a5ba-1799bd7b1dd1`. Open `/studio/play/<id>` on the local frontend. SQLite jobs remain local; exported JSON evidence is committed.

## Reproduction

With the frontend on 5173 and backend on 8000, from repository root:

```powershell
aether-backend/venv/Scripts/python.exe scripts/check_iteration10.py
aether-backend/venv/Scripts/python.exe scripts/play_iteration10.py
aether-backend/venv/Scripts/python.exe scripts/live_iteration10.py --replay factory garden boss
aether-backend/venv/Scripts/python.exe scripts/live_iteration10.py --replay runner guardian
```

The browser and play scripts use fixtures/captured decisions and no provider calls. Replay is also free of fresh inference; its local per-invocation completion limit permits up to three cases, so split the five cases across invocations. `live_iteration10.py` without `--replay` costs provider usage and should not be part of routine verification. `resume_iteration10.py` can consume one fresh design completion; its captured live evidence is retained for inspection instead of routine reruns.

Remaining limits: Guardian composition; exclusive factory pit gating/literal laser barrier; elaborate environmental transition animation; global chaser navigation; true sword melee; broader authored boss art/animation; arbitrary omitted/misclassified prose. None is hidden by lowering core validation.
