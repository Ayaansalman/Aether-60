# Iteration 2 audit and defect backlog

Baseline: `dc6b507`, continuing `codex/platformer-overhaul`. The active React/Vite product and v2 backend are retained. Earlier milestone claims describe earlier evidence, not this iteration's verification.

## Actual prompt traces before changes

`docs/evidence/iteration2/before/{fixture,live}/{forest,factory,ice}.json` preserves the three exact requested prompts, raw provider designs, guarded designs, GameIR and route checks. Live traces call the configured provider; fixtures remain separately labeled.

The contract only allowed forest/industrial/twilight, five section kinds, enemy/hazard booleans, and one exit. Every section advances x; terrain fills to the world bottom. Seed variation changes lengths by one tile. Crystals are placed every two tiles, enemies near the right edge, spikes in the center. Every enemy runs the same patrol loop. Optional moving platforms sit above the same mandatory route. Asset selection dispatches between grassy terrain and industrial terrain; twilight reuses forest tiles. No icicle, ice friction, exit animation, enemy behavior, campaign or trigger fields exist.

The fixture ice prompt becomes a forest with crystals and patrols; no ice features are marked unsupported. Both route and objective checks pass. Live planning can mention unavailable mechanics in `unsupported`, but cannot encode them for construction. The capability guard recognizes abilities, exclusions, moving platforms and a small future-feature list. `game_intent.json` records abilities as requested mechanics, losing other concrete requests. Thus even correctly understood requests cannot cross the schema/runtime boundary. See raw traces for actual provider limitations rather than assuming complete model understanding.

QA checks movement, jumps, route edges, controlled collection/checkpoint/damage/exit overlaps, restart and exceptions. It does not compare the prompt with implemented capabilities or exercise enemy behavior, moving platforms, environmental semantics or transitions. Repair only reduces gaps/elevation, at most twice. It cannot invent mechanics or fix runtime code. Initial static repair evidence omits the failed validation; this needs preservation.

## Priorities and root causes

| Severity | Defect | Root cause / action |
|---|---|---|
| Critical | Concrete mechanics silently disappear | Restrictive design/IR contracts and incomplete requirement extraction; add capability witnesses and verification status |
| High | Different prompts produce the same journey | One layout algorithm and encounter boolean; add topology, encounters and stages |
| High | Ice becomes grassy forest | Missing theme; controlled procedural ice terrain/background/decor instead of recolored grass |
| High | QA passes missing mechanics | Add requirement checks and real browser behavior observations |
| High | Existing game on empty creator | Automatic fixture fetch; use empty state and explicit samples |
| High | Stale game remains during generation/failure | Clear previous spec and gate generated preview by build/status |
| Medium | Keyboard works outside game focus | Runtime suppresses form input only; require preview focus |
| Medium | Collectible bobbing does not update static overlap body | Animate visual presentation separately or synchronize body |
| Medium | HUD total confused with required count | Label collected, required and available; include current stage |
| Medium | Gate warning persists after walking away | Dismiss temporary messages; report objective clearly |
| Medium | Generation evidence grows into every poll | Whole-artifact polling; retain for local iteration, future summary/artifact endpoints |
| Medium | Production lifecycle remains limited | No production authentication/durable queue; outside local gameplay iteration |

Extraction is intentionally bounded; unfamiliar natural language still requires review. Unsupported model statements must remain visible. Static construction evidence must never be presented as browser verification. Controlled QA positioning must remain disclosed; it does not certify full autonomous completion or fun.

## Resolution at the iteration checkpoint

The registered-feature contract, environment/encounter/stage composition, ice environment, feature QA, empty/stale preview states, keyboard focus, collectible collision body, HUD objective counts and temporary gate messaging are implemented and verified. Mobile review additionally found inherited one-screen body scrolling; studio pages now use normal document scrolling and the creator suite checks it. Visual review additionally found the old exit was a keyhole block; shrine/gate/beacon visuals now have explicit specifications.

The complete results and evidence index are in [ITERATION2_RESULTS.md](ITERATION2_RESULTS.md). Whole-artifact polling, production hardening, arbitrary NLP completeness, full unassisted playthrough coverage, nonlinear world graphs, richer authored animation and audio remain actionable backlog items. These are retained as limitations rather than marked fixed by passing smoke tests.
