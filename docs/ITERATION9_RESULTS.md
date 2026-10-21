# Iteration 9 - compositional behavior contracts and reliable handoffs

Date: 2026-10-21. Existing application and three runtime families preserved. No new genre, legacy arena activation, dependency/asset download, parallel model agents, push or deployment.

## Diagnosis and actual pipeline

The persisted creator path is `POST /api/v2/games` in `routes/platformer.py`, not the older v1 orchestrator/arena path. Live mode runs configured-provider semantic interpretation, then one family designer. These are the two real model-backed responsibilities; they are sequential calls, not independent autonomous agents. Feasibility, intent binding, Pydantic validation, asset selection, seeded construction, ballistic/connectivity checks, Phaser/Canvas assembly, Playwright probes, fidelity reporting and local job/event/artifact persistence are deterministic services. Fixture mode is explicitly labeled keyword-based demo planning and is not equivalent to live semantic interpretation. No claim of general semantic coverage is made for fixtures.

Routing chooses a controller adapter. Previously, adventure planning then required nonempty actors/quests and an objective in every area. Its instructions steered every top-down game toward sequential quest loops. The original failed job `0f0ce45f-fdcb-490b-bbfd-cefef6483eff` is still present locally. Its saved model design inserted `survival_relic`, kind `item`, name `Survival Emblem`, without an inventory ID. It also inserted a guide, a collection quest and a sanctuary door into the user's bullet-survival game. The object was an unsolicited objective pickup, **not** an actual projectile. Inventory validation correctly rejected it. Adding an invented ID would have preserved the wrong game. See `evidence/iteration9/original-failure.json` for the original request and offending objects.

Other observed bottlenecks: no top-down runtime spawn/shot-count lifecycle contract; designers independently relabeled semantic requirements; the platformer compiler exposed only one-switch/one-door designs although its IR/runtime already supported all-source links; unlock counts were not checked against distinct doors until construction; adventure/runner design errors had no bounded model correction; raw Pydantic text could reach creator events. Existing biome, boss, arcade and licensed sprite systems were functional and were extended rather than replaced.

## Contracts and ownership

`Intent` now independently represents perspective, control, core loops, structure, source-grounded requirements, mandatory flags and optional typed `Gameplay`. Perspective/control contradictions and top-down survival without a non-quest outcome fail at the interpretation boundary. Existing biome/count/exclusion and arcade contracts remain. The interpreter receives the actual capability catalog.

`schemas/gameplay.py` defines health, invulnerability, player weapon availability, outcome (`quests`, `endless`, finite `survive`), optional deadline, time scoring, enemy archetypes, spawn rules and attack sequences. Relations are controlled data: spawn timer -> uniformly selected archetype; shooter -> counted projectile sequence; final shot -> despawn/repeat; health zero -> loss; finite survival clock -> victory. Numeric values bind the designer and survive IR construction. This is not an unrestricted scripting language.

Adventure actors/quests may be empty only with an explicit non-quest outcome. Real items still require inventory IDs, real quests still validate actor kinds/supply/order/area coverage, and combat components require combat enabled. Imported adventure IR revalidates the same design boundary. Archetype references, unique IDs, windup/interval compatibility, finite/endless deadlines, one connected area and enemy/projectile budgets are checked. No inventory IDs are synthesized.

The existing semantic capability map now exposes typed descriptors: IR paths, controls, dependencies, configuration, behavior types, conflicts, runtime implementations, limitations and verification IDs. It feeds interpretation, pre-designer compatibility, Inspector artifacts and final fidelity. It documents that the new spawn scheduler currently runs only in the top-down adapter. This is a bounded catalog, not a universal mechanic graph.

Platformer designers no longer act as a second authoritative requirement classifier when semantic intent is supplied. Their `requested_features` are retained in provider provenance as advisory data; the source-grounded semantic contract owns fidelity. This fixes an observed real-model gate requirement mislabeled `combat_objective`, which had rejected an otherwise constructed game. Legacy callers without semantic intent retain the older requirement path. The older explicit platformer phrase guards remain and are a continuing architectural limitation.

## Validation, repair and Inspector

All three live designers and the interpreter use the common `validated_response` boundary: one initial response, at most one correction, original prompt retained, exact error locations/messages and failed candidates retained, then revalidation. There is no family substitution. Exclusions in adventure are checked before construction and enter this same bounded correction path. Typed gameplay and existing arcade constraints bind deterministic fields with recorded before/after changes.

Source quotes must exist in the original prompt. A deterministic grounding step may expand an ordered token subsequence to its complete original sentence (for shortened list clauses); it never inserts synonyms or changed numbers. Expansions are recorded. Unmatched/hallucinated sources enter bounded correction. Provider transport retries/fallbacks remain an independent pre-existing layer.

`capability_compatibility.json`, `semantic_intent.json`, `provider.json`, `design_validation.json`, final design, IR, QA and semantic fidelity are visible in the existing Inspector artifact selector. Model decisions, deterministic bindings, construction witnesses and named runtime checks are distinguished. Failed designs get a concise creator message and detailed field diagnostics in artifacts. Platformer route repair remains bounded and preserves the prompt/seed. Nonrepairable runtime defects are reported, not disguised as balance changes.

## Runtime construction and presentation

`BehaviorWorld` is a pure deterministic scheduler used by **AdventureScene**, the existing sprite-based Phaser scene. It uses a fixed 120 Hz logical step, seeded uniform role selection, per-rule live caps and deferred unsafe spawns without debt bursts. Candidate tiles need reachable 3x3 clearance and avoid actors/doors; current player distance and enemy spacing are rechecked at spawn time. There is a combined 64-enemy and conservative 240-projectile configuration budget. Hostile projectiles use real physics collisions, impacts and bounded lifetime. Shooter disappearance leaves already-fired bullets alive. Attack counters, recent event history and active entities stay bounded. Chasers pursue; patrols and stationary shooters retain separate behavior. Gameplay/scoring stops at loss and resets with R. Unfocused play freezes simulation.

`InteractionDesign.gate` allows several switches to share one actual door with `condition=all`. Existing single-switch behavior is compatible. Distinct gate counts, activation counts and shared gate section consistency are validated before compilation. Physical door collision and the exit objective both depend on the full source set. No collectible objective replaces the puzzle.

The existing CC0 asset catalog now resolves spawned archetypes as entity roles, not inventory actors. No new packs or fabricated sprite frames were added. Directional walk/idle and available attack states are used from manifests; procedural windup cues cover assets without attack frames. A shared lightweight feedback component handles real attack warnings, impacts, defeats, pickups and switch/door activation across top-down and platformer scenes. Top-down damage feedback aligns blinking to invulnerability. Survival has compact health/time UI and no inventory/quest/exit controls. Boss victory clears the stale health bar and names the defeated boss. Existing runner presentation and physics remain intact.

## Acceptance evidence

| Scenario | Source and result | Verified scope |
| --- | --- | --- |
| A top-down survival | Fresh Gemini semantic/design capture: 12/12 Chromium. Captured decisions replayed through actual persisted HTTP lifecycle: READY, 12/12 runtime, semantic PASS | Three health; safe random spawns; both roles; five shots at 1000 ms intervals and despawn; actual projectile damage; health-zero loss; time score stops; restart; no quest/inventory/NPC/pickup/exit. Modern AdventureScene |
| B boss duel | Deterministic existing boss fixture: 10/10 Chromium | Exactly one boss, alternating warning/charge/volley, real projectile hits, direct defeat victory, restart, natural warning effects and hit/defeat effects |
| C mixed biome quest | Deterministic existing fixture: 20/20 Chromium | One connected map, keyboard forest/lake crossing, localized slippery coasting, directional licensed animation, item collection/delivery, no enemies, completion/restart |
| D shared factory gate | Fresh Gemini design required one live correction for unlock count. Direct browser: 14/14. Final captured decisions through HTTP lifecycle: READY_WITH_WARNINGS, 15/15 runtime | Two switches, one door, partial activation keeps physical collision and exit locked; final source opens door; actual patrol/machinery and objective completion. Visual interpretation and unobserved route/restart requirement hooks remain warnings |
| E arcade contrast | Offline easy forest creature and extreme factory robot: each 7/7 Chromium | Theme/player and difficulty survive construction. 210->280 versus 390->500 px/s; recovery .90 versus .10 sec; precision .30 versus .82; sequence length 3 versus 6. Existing seeded geometry/ballistic/flying tests remain passing |
| F presentation | Survival and boss browser probes plus biome directional animation | Actual events emit warning/impact/defeat/pickup/activation cues; available manifests animate. Screenshots inspected. No subjective enjoyment certification |

Chromium probes disclose controlled player placements, boss clock/final-health isolation and scripted interactions. Survival attack clocks/counters/health were not changed during sequence observation; player teleportation evaded threats, and controlled overlap with an actual projectile verified damage. These are functional tests, not autonomous full playthroughs. Schema/unit/runtime evidence is separately labeled.

110 focused backend tests pass, including 17 iteration-9 tests; 36 frontend tests pass, including seven new behavior tests. They cover paraphrased source handoffs using deterministic model stubs, exact behavior propagation, no-combat semantics without literal keywords, source/dependency failures, preserved inventory validation, bounded repairs, multiple shot counts/intervals, mixed random roles, caps and shared gate latching. Stub paraphrases verify plumbing, not real model paraphrase accuracy. Production TypeScript/Vite build and ESLint pass. Two inherited Python deprecations and the existing Phaser chunk advisory remain.

Real Gemini checks used `gemini-3.5-flash-lite`. There were ten logical provider completions across development: three initial A attempts consumed 2/1/2 completions and failed schema/source grounding, the final A used two, and D used two initial calls plus one resumed correction. Initial failures are disclosed, not counted as successes. Transport-level retries were not independently counted. `live-D --resume` used the saved real semantic/design response and one fresh bounded designer correction. HTTP verification explicitly replays captured model decisions with zero additional provider calls. Its provenance/model ID says `captured-gemini`; it is not presented as fresh inference.

Local playable captures with Inspector artifacts:
- Survival: `http://localhost:5173/studio/play/5c220870-0d7c-465f-94b6-f4cc4b57ca61`
- Factory: `http://localhost:5173/studio/play/584b2fc0-95b3-4fac-addb-93d9271a2cdc`

Evidence summary: `evidence/iteration9/summary.json`. Initial semantic failures, the factory's raw invalid design, the secondary-label API failure, corrected designs, runtime reports and representative screenshots are retained. Earlier iteration evidence is preserved. Local DB jobs are not part of the source checkpoint. The idle Aether backend was restarted with current code; both saved game endpoints still load. A fresh actual HTTP offline runner job reached READY with compatibility PASS and 7/7 Chromium checks (`local-http-smoke.json`), without a provider call.

## Limits and next architectural step

Aether still cannot generate arbitrary games. The controlled vocabulary omits melee swords, arbitrary AI scripts, multiplayer, complex inventories/crafting, arbitrary boss patterns and new controllers. New behavior composition currently uses one top-down connected area; it is not a universal scheduler across all controllers. Existing boss and biome boundaries remain. Safe spawn deferral can reduce density when space is exhausted; shooter aim is direct, not path-planned. Bounds are supported configuration limits, not claims of unlimited enemies/projectiles.

The most valuable next step is consolidating the remaining legacy per-family requirement vocabularies/guards into the canonical semantic capability contract. The real D interpreter even labeled an exit dependency as `restart`; actual gate behavior is separately verified, but a source quote alone cannot prove a model assigned the correct meaning. Omitted or misclassified intent and unsupported relationships still need explicit coverage. This iteration makes supported combinations constructible and inspectable; it does not solve general game understanding. New runtime mechanics still require engine development.

## Reproduce

From repository root with the frontend on 5173:

```powershell
aether-backend/venv/Scripts/python.exe scripts/check_iteration9.py
aether-backend/venv/Scripts/python.exe scripts/verify_iteration9_examples.py
aether-backend/venv/Scripts/python.exe scripts/replay_iteration9_api.py A
aether-backend/venv/Scripts/python.exe scripts/replay_iteration9_api.py D
```

Replay requires the local backend on 8000 for the browser to fetch persisted specs; no live provider calls occur. `scripts/live_iteration9.py A` or `D` explicitly uses the configured provider (and can cost usage). Routine checks should use captured evidence/fixtures. Backend selection and frontend commands are listed in `evidence/iteration9/verification.json`.
