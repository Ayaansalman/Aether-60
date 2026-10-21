# Iteration 4 — composable gameplay systems

Continued locally from `41c93ac` on 2026-10-20. Implementation focused on the platformer planner, typed contracts, compiler, runtime components and their targeted verification. No new framework, genre, external artwork, push or deployment.

## Gameplay changes

The existing patrol/chase decisions and icicle state machine remain in use. New pure TypeScript components in `aether-frontend/src/game/platformer/gameplay.ts` provide registered trigger predicates, idempotent gameplay events, all/any activation links, objective conditions, bounded platform trajectories and a shared enemy state machine. The model configures these components through validated data; no generated code, arbitrary action names or expression interpreter is executed.

Enemy families now include patrol, chase, shooter, stationary turret and ambusher. Shooters reposition before firing when crowded; turrets remain anchored; ambushers telegraph a committed short lunge and deal contact damage during the attack. Ranged enemies flash during windup before firing. Configuration bounds health, detection radius, telegraph duration and recovery cooldown. Multi-hit enemies enter a visible hurt/stun state; actual defeat events satisfy only matching objective targets. Optional overhead routes are kept clear of stomp-only encounters so they do not make a stationary guard impossible to defeat.

Environment components support key-operated switches, contact/proximity switches, grounded pressure plates and projectile switches. All use stable IDs and typed links to open doors. Plates latch: they do not require a second actor to keep standing on them. Closed doors have actual collision bodies; activation removes collision and animates opening. Door unlock conditions also guard the exit against an alternate route bypass. Player projectiles are enabled only by the selected attack configuration or the needs of projectile-switch composition. Friendly shots hit enemies and projectile switches; terrain and closed doors stop shots.

Moving platforms now follow bounded horizontal/vertical sine or ping-pong paths. They advance on fixed Arcade physics steps rather than render-frame feedback. Rider contacts account for relative vertical velocity, allowing the player to ride and jump from a lift. Restart removes the old physics listener safely.

## Objectives and progression

`GoalDesign` configures `defeat`, `activate`, `unlock`, `collect`, `survive` and `time_limit` conditions. Compilation resolves explicit entity IDs. `count=0` means all matching targets; an optional `enemy_behavior` selects a specific enemy family. Impossible counts, incorrect target kinds, dangling IDs, invalid links and conflicting timer budgets are rejected. Deadlines also receive a necessary straight-line traversal budget check; this does not certify the difficulty of every encounter.

Local goals must all be satisfied before the exit completes a level. A deadline is an active constraint: reaching the exit before expiry wins; expiry loses. Survival means staying alive for the configured level duration. Campaign goals are evaluated only at the final exit, using unique event IDs retained across transitions. Per-level objective lists, interaction lists, attack modes and platform motion can override defaults, including an empty introductory list.

Checkpoint respawns keep the current level's collected/defeated/activated/unlocked state. Level transitions rebuild local actors and timers while preserving campaign events. Whole-game restart clears all event progress. HUD counts, exit tint, switch feedback, attack windup, projectile impacts and timeout messages expose the current state. Terminal states refresh the HUD immediately; an obsolete locked-exit message changes to “Exit unlocked!” when its requirements become satisfied.

Controls remain arrows/A/D and Space, with existing dash where selected. **E** uses nearby interaction switches; **F/X** fires when equipped. Matching touch buttons appear for campaigns using these controls. The creator layout remains intact; its capability text now lists the new systems.

## Planning and generation

GameDesign and per-level specifications expose interactions, objective conjunctions, campaign objectives, player attack selection, enemy tuning and platform trajectories. Persisted GameIntent includes the gameplay choices. The model prompt explains supported combinations, target supply and zero-based section indices.

The deterministic fixture/requirement guard selects systems from explicit prompt language. Combat requests create defeat conditions and guard encounters. Factory switch requests create linked doors and activation/unlock conditions without inserting unrelated enemies. Ice/ranged requests combine slippery terrain, falling icicles and shooters. Requested enemy families are distributed rather than overwriting each other. Registered unsupported mechanics remain outside the action enum.

One live Gemini planning invocation produced a two-level factory design. Its first level used an out-of-range one-based door index. The bounded guard converted those indices to existing zero-based sections and recorded before/after values in `live-factory/generation.json`. The original model design is preserved. Subsequent browser runs rebuilt the saved design without another model call.

## Targeted verification

| Check | Result |
| --- | --- |
| Relevant backend contracts, compiler, fidelity, campaign and API tests | 72 passed |
| Python compilation of changed backend modules | Pass |
| Frontend production build and ESLint | Pass |
| Shared runtime component tests | 12 passed |
| Forest defeat-creatures example | 11 Chromium checks passed |
| Factory switches/security doors example | 13 Chromium checks passed |
| Difficult ice/falling hazards/ranged enemies example | 21 Chromium checks passed |
| Two-level pressure/projectile-switch, armored turret, ambusher and campaign-goal integration | 29 Chromium checks passed |
| Survival plus deadline fixture | 11 Chromium checks passed |
| Short achievable deadline: expiry, restart and early completion | 11 Chromium checks passed |
| Saved real Gemini factory design, two levels | 30 Chromium checks passed |

The backend suite was deliberately limited to the affected systems; the unrelated project-wide suites were not rerun. Existing dependency deprecation and Phaser chunk-size advisories remain.

All seven browser cases pass, totaling 126 checks. Their final requirement reports also pass; `evidence/iteration4/summary.json` records per-case component profiles and results.

Browser checks use controlled positions with real keyboard interaction, pressure contacts, projectile collisions, stomps, door blocking/passage, objective gates and scene transitions. They verify multi-hit damage reactions, attack telegraphs, lift riding/jumping, persistent campaign defeats, victory, deadline loss and restart. They are not autonomous playthroughs and do not establish enjoyment or overall visual quality.

Initial reports retained under the relevant case folders distinguish real fixes from test-driver fixes: render-time platform velocity amplification, shutdown listener cleanup, stale HUD feedback, a projectile probe initially positioned over a gap, and fixed-delay probes that could miss a jump near its apex or sample a lift across its turnaround. The final probes wait for observed collision/airborne states and sample the ride trajectory. Screenshots of level states, turret windup, open doors and deadline failure were visually inspected. Test screenshots load saved JSON through the real preview's fixture boundary; the surrounding sample label/prompt is not a claim of a new creator submission.

## Reproduce

With the frontend running on port 5173, from the repository root:

```powershell
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case combat
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case factory
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case ice
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case mixed
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case timers
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case deadline
# Reuses the saved Gemini design; no live call:
aether-backend\venv\Scripts\python.exe scripts\verify_iteration4.py --case factory --live --saved-design
```

From `aether-backend`: `.\venv\Scripts\python.exe -m pytest tests/test_gameplay_systems.py tests/test_platformer.py tests/test_platformer_fidelity.py tests/test_campaign.py tests/test_platformer_api.py -q`.

From `aether-frontend`: `npm run build`, `npm run lint`, `npm run test:behaviors`.

Evidence lives in `docs/evidence/iteration4/`. Fixture and live-derived artifacts are labeled separately. A new `--live --case factory` invocation explicitly makes another provider request.

## Deliberate limits

Objectives are conjunctions plus the exit; links support all/any sources and the registered `open_door` action. Pressure plates latch rather than closing doors on release. Survival is a duration while alive, not a wave-spawning system. Campaign collection/combat conditions are supported, not an inventory or quest scripting language. Moving routes remain optional. No audio files were found in the current asset pack, so this iteration uses visual feedback without downloading sounds. Other genres, arbitrary actions, comprehensive natural-language fidelity and production hardening remain outside this milestone.
