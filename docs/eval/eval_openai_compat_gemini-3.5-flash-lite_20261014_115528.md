# AETHER Full-Pipeline Evaluation Report: openai_compat (gemini-3.5-flash-lite)


- **Benchmark Date:** 2026-10-14 11:55:28 UTC
- **Provider:** `openai_compat`
- **Model ID:** `gemini-3.5-flash-lite`
- **QA Execution Mode:** `real`
- **Run Status:** `complete`
- **Sample Size:** 12 prompt(s)
- **Total Model Requests:** 14

## Summary Metrics

| Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Spec Validation** | **11/12 (91.7%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **9/12 (75.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **9/12 (75.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **0/2 (0.0%)** | Repairs that transitioned failing game to READY |
| **Theme Match Rate** | **5/5 (100.0%)** | Faithful to specified theme |
| **Objective Match Rate** | **6/6 (100.0%)** | Faithful to specified objective |
| **Limitation Honesty Rate** | **1/1 (100.0%)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **7 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **45807.6 ms** | Model response prompts only |
| **Min Latency** | **3762.6 ms** | Model response prompts only |
| **Max Latency** | **68085.9 ms** | Model response prompts only |

## Per-Prompt Evaluation Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category | Theme | Obj | Limit | Adherence (1-5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 68086ms | `none` | ✅ | ✅ | — | |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `READY` | ✅ | ✅ | ✅ | No | 1 | 50825ms | `none` | ✅ | ✅ | — | |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `READY` | ✅ | ✅ | ✅ | No | 1 | 50224ms | `none` | ✅ | ✅ | — | |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `READY` | ✅ | ✅ | ✅ | No | 1 | 49768ms | `none` | ✅ | ✅ | — | |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 46945ms | `none` | ✅ | ✅ | — | |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `FAILED` | ✅ | ❌ | ❌ | Att | 1 | 32177ms | `interaction` | — | — | — | |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `READY` | ✅ | ✅ | ✅ | No | 1 | 53163ms | `none` | — | — | — | |
| `p08` | make something fun and fast-paced | `READY` | ✅ | ✅ | ✅ | No | 1 | 43328ms | `none` | — | — | — | |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `READY` | ✅ | ✅ | ✅ | No | 1 | 43949ms | `none` | — | — | ✅ | |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `READY` | ✅ | ✅ | ✅ | No | 1 | 44670ms | `none` | — | — | — | |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `FAILED` | ✅ | ❌ | ❌ | Att | 1 | 22010ms | `interaction` | — | ✅ | — | |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `FAILED` | ❌ | ❌ | ❌ | No | 1 | 3763ms | `schema` | — | — | — | |

## Check Definitions & Failure Taxonomy
- **schema**: GameIR failed validation rules or schema constraints.
- **rendering**: Game canvas failed to mount or Phaser QA hook not ready.
- **interaction**: Player movement, velocity consistency, attack response, or controls failed.
- **objective**: Win condition unreachable, score progress halted, or playability thresholds failed.
- **restart**: Scene restart failed to restore fresh initial playing state.
- **timeout**: Planner, QA execution, or repair timed out.
- **provider_error**: Model HTTP error, quota 429, or network disconnect.
- **not_run**: Prompt omitted due to request budget or quota fast-fail.
