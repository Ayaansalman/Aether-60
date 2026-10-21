# What Aether can create today

Current as of Iteration 6, October 21, 2026.

Aether turns a natural-language prompt into a small playable **2D platformer** or **top-down adventure**. Gemini plans a game using supported components; Aether validates the design, builds a deterministic world, selects licensed artwork, runs it in Phaser and checks gameplay in Chromium. It composes an existing engine's mechanics rather than inventing arbitrary new engine code for each prompt.

## Games you can make

| Game type | Good fits | What changes with the prompt |
| --- | --- | --- |
| Side-scrolling platformer | Forest crystal hunt, industrial switch puzzle, icy hazard course, tower ascent, short combat campaign | Theme, level count, route shape, difficulty, abilities, enemy families, hazards, objectives and interaction combinations |
| Peaceful top-down adventure | Woodland healer quest, village exploration, gathering and returning items, discovering a sanctuary | Settlement/forest setting, NPC names and dialogue, item types and quantities, landmarks, quest sequence and scenery |
| Combat top-down adventure | Crypt exploration, guarded key hunt, sealed chamber, relic recovery, small ruins expedition | Rooms/areas, enemy selection, combat requirements, key/switch prerequisites, sealed destination and final reward |

These are short games built from bounded reusable layouts and components. Prompt differences affect gameplay and layout, not just colors or seeds. Explicit platformer wording selects the platformer adapter; explicit top-down/adventure/RPG wording selects the adventure adapter. “RPG” here means the supported adventure features below, not a full statistical RPG system.

## Platformer engine

**Movement and world construction**

- Responsive horizontal movement, jumping, jump buffering and coyote time.
- Optional double jump and dash.
- Forest, industrial, twilight and ice themes, including slippery movement where selected.
- Journey, ascent, terraces and cavern layouts composed from reusable traversal, precision, combat, hazard, exploration and moving-platform sections.
- One to three levels, with individual themes, difficulty, briefings and mechanic settings.
- Horizontal/vertical moving platforms using bounded sine or ping-pong motion; riding and jumping from lifts.
- Tile collision, camera following, health, checkpoints, local respawns, loss, victory and whole-game restart.

**Combat, hazards and interactions**

- Patrol, chase, shooter, stationary turret and ambusher enemy behavior.
- Stomp combat and optional player projectiles.
- Configurable enemy health, detection radius, attack telegraph and cooldown within contract limits.
- Spikes, timed hazards and falling icicles triggered by proximity or a timer.
- Nearby interaction switches, touch/proximity switches, pressure plates and projectile switches.
- Linked security doors with real blocking collision. All/any switch conditions can open a door.
- Pressure plates latch after activation; they are not continuous weight puzzles.

**Objectives and campaigns**

- Reach the exit, collect crystals/relics, defeat specified enemies, activate switches or unlock doors.
- Survival-duration and finish-before-deadline conditions.
- Multiple required conditions per level, plus campaign objectives retained across level transitions.
- Checkpoint respawn retains local collected, defeated, activated and unlocked progress. Restart clears the run.

## Top-down adventure engine

**Movement, world and artwork**

- Normalized eight-direction movement with zero gravity, foot-sized collision bodies and camera following.
- Village, forest, ruins, dungeon and cave environment specifications.
- Settlement squares, complete house modules, connected paths, entrances, foraging clearings and framed woodland vegetation.
- Connected dungeon room layouts, early alternate routes, guarded exploration areas and sealed final sections.
- Seeded room sizes/positions, house arrangements, actor/pickup placement and decorations.
- Authored directional character animations in the primary asset families, foot-based depth sorting, roof/canopy walk-behind behavior and NPC collision.
- Ninja Adventure is the default visual family. Ansimuz Tiny RPG Forest supports a narrower forest exploration/combat subset. Legacy Kenney adventure art remains compatible. A game uses one supported family consistently.

**Characters, inventory and quests**

- Named NPCs with authored greeting, active-quest and completion dialogue supplied by the generated design.
- Sequential objectives: talk, collect, deliver, explore a landmark, defeat an enemy, activate a switch and unlock a door.
- Item pickups, quantities, inventory and atomic delivery of multiple different items.
- Quest progression retains earlier pickups and other irreversible events, so exploring before speaking to an NPC need not lose progress.
- Obtainable keys, retained key inventory, switch prerequisites and physically blocking locked passages.
- Up to three areas, sixteen sequential objective stages, thirty-two actor definitions and one sealed passage per area. These are schema ceilings, not recommended game sizes: one or two small areas and a short coherent quest work best.
- Forward area transitions with persistent inventory/quest state. Outdoor gather-and-return quests share one connected village/forest map, because area portals do not support backtracking.
- Objective markers, a direction/distance compass, interaction hints, pickup feedback, collection counters, readable dialogue, completion and restart.

**Optional combat**

- Patrol and local chase enemies, player projectiles, enemy health, contact damage and visible hit/defeat feedback.
- Player health, temporary damage protection, loss and restart.
- Peaceful prompts can omit enemies and attack controls entirely.
- Combat is simple action-adventure combat; adventure enemies do not inherit every platformer enemy behavior.

## Creator and generation workflow

- A prompt-driven Studio with playable preview, built-in examples, restart and expanded preview.
- Live Gemini planning through the configured provider, or explicitly labeled deterministic offline fixtures without a model call.
- Keyboard controls and existing touch controls; an adjacent mobile panel exposes adventure objectives, inventory and dialogue.
- Typed genre-specific GameIR, reference/resource checks, deterministic seeds and route/destination validation.
- Persisted generation jobs, stages and events, plus an Engineering Inspector showing intent, raw design, recorded corrections, final specifications, selected assets and QA evidence.
- Browser checks of supported runtime behavior and an explicit re-verification endpoint.
- Bounded platformer layout repair and recorded adventure design normalization. Arbitrary code repair or universal prompt fulfillment is not provided.
- JSON export of engineering evidence. This is **not** a standalone downloadable game/source bundle or hosted publication service.
- Bundled asset licensing, checksum/frame validation and a selected-resource redistribution allowlist. Credentials, databases, raw downloaded archives and runtime artifacts stay out of Git.

## Current limits

- Only the two generated genres above; no 3D, multiplayer, open-world simulation or arbitrary genre conversion.
- No full RPG statistics, leveling/skill trees, equipment system, crafting, economy/shops, procedural boss system or branching dialogue engine.
- No generated custom music/soundtrack or new AI-created artwork in the current pipeline.
- Adventure NPCs are stationary and dialogue is planned ahead, not a live conversation with an LLM.
- Adventure enemies use local pursuit, not global pathfinding. Quests are sequential, not a branching quest graph. Portals move forward.
- World construction uses a small set of reusable spatial grammars, not unlimited authored buildings, interiors or bespoke puzzle mechanics.
- No generated-game save/resume service. Persisted generation jobs retain the design and evidence, not a player's live run.
- Supporting an asset visually does not automatically implement its gameplay: owning boss, weapon or furniture sprites does not add those systems.
- Functional QA is bounded. Some checks use controlled positions and real keyboard/physics; passing them does not prove an unassisted playthrough, enjoyment or perfect interpretation of every prompt.

## Example prompts

**Peaceful woodland quest**

> Create a cozy top-down fantasy adventure in a woodland village. A healer needs three magical herbs from the nearby forest. Let me talk to the healer, explore the forest, collect the herbs and return them. Include houses, paths, trees and friendly villagers. No combat.

**Crypt adventure**

> Create a dark top-down dungeon adventure in an ancient crypt. Fight skeleton guards, discover a key, unlock a sealed chamber and claim a magical relic. Include connected rooms, treasure and a clear final objective.

**Industrial platformer**

> Create a two-level industrial platformer with moving lifts, patrolling robots and switches that open security doors. Start with a simple introductory level, then add turret enemies and a final escape objective.

**Icy precision platformer**

> Create a challenging ice platformer with slippery movement, double jump, falling icicles, checkpoints and collectible relics. Use an ascending route and a flashing beacon at the exit.

For predictable results, specify the genre, setting, a few supported mechanics and a clear objective. Use “no combat” when requesting peaceful exploration. Large unsupported feature lists do not expand the engine.

## Controls and testing

| Mode | Controls |
| --- | --- |
| Platformer | Arrows/A/D to move; Space to jump; Shift to dash when equipped; E to use supported switches; F/X to fire when equipped; R to restart |
| Adventure | WASD/arrows to move; E to talk/use/continue dialogue; F/X to attack in combat games; R to restart |

Click the game canvas to focus keyboard input. Touch buttons appear where supported.

The latest Iteration 6 verification passed 87 targeted backend tests, 17 frontend tests, 77 asset checks, production build and ESLint. Final Chromium results: healer fixture 16/16, crypt fixture 24/24, live Gemini healer 21/21, live Gemini crypt 24/24 and platformer regression 18/18. Geometry invariants passed forty seeds for each adventure acceptance prompt. Rendered screenshots were inspected; mobile creator QA was not rerun in Iteration 6.

See [setup](../README.md#run), [Iteration 6 evidence and reproduction](ITERATION6_RESULTS.md), [platformer systems](ITERATION4_RESULTS.md) and [asset provenance](ASSET_LIBRARY_EXPANSION.md).

## Iteration 9 - composed top-down behaviors

The existing adventure controller also accepts non-quest top-down games via optional typed `gameplay`: safe periodic spawning, uniform enemy-role choice, pursuit/patrol, counted projectile attacks with windup/interval and despawn/repeat, health/invulnerability, endless or finite survival and time scoring. It uses the modern AdventureScene and existing CC0 sprites. No inventory/NPC/quest/exit is implied by top-down movement. Inventory and quest dependency validation remains mandatory when those mechanics are used. New scheduler configurations are limited to one connected map, 64 live enemies and a conservative 240-projectile concurrency budget; unsafe spawns defer.

Platformer interactions may share a `gate` ID; every linked source must activate before that one door opens. Typed capability descriptors and semantic requirements are exposed in the existing Inspector. Shared event feedback covers warnings, impacts, defeats and interactions. See [Iteration 9](ITERATION9_RESULTS.md) for verified examples, field contracts and limits; this does not provide arbitrary executable game logic or new controllers.
