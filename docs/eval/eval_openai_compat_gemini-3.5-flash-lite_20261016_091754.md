# AETHER Full-Pipeline Evaluation Report: openai_compat (gemini-3.5-flash-lite)


> **Run D: upgraded engine (GameIR with new enemy types, layouts and defeat_enemies); same 12 prompts as Run A, so engine and repair prompt differ from Run A**


- **Benchmark Date:** 2026-10-16 09:17:54 UTC
- **Provider:** `openai_compat`
- **Model ID:** `gemini-3.5-flash-lite`
- **QA Execution Mode:** `real`
- **Run Status:** `complete`
- **Request Timeout:** 60.0 s
- **Sample Size:** 12 prompt(s)
- **Total Model Requests:** 18

## Summary Metrics

| Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Spec Validation** | **12/12 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **9/12 (75.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **12/12 (100.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **3/3 (100.0%)** | Repairs that transitioned failing game to READY |
| **Theme Match Rate** | **5/5 (100.0%)** | Faithful to specified theme |
| **Objective Match Rate** | **6/7 (85.7%)** | Faithful to specified objective |
| **Limitation Honesty Rate** | **1/1 (100.0%)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **11 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **47020.5 ms** | Model response prompts only |
| **Min Latency** | **43960.9 ms** | Model response prompts only |
| **Max Latency** | **81609.3 ms** | Model response prompts only |

## Per-Prompt Evaluation Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category | Theme | Obj | Limit | Adherence (1-5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 62223ms | `none` | ✅ | ✅ | — | |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `READY` | ✅ | ✅ | ✅ | No | 1 | 45399ms | `none` | ✅ | ❌ | — | |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `READY` | ✅ | ✅ | ✅ | No | 1 | 46627ms | `none` | ✅ | ✅ | — | |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `READY` | ✅ | ✅ | ✅ | No | 1 | 48402ms | `none` | ✅ | ✅ | — | |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 44688ms | `none` | ✅ | ✅ | — | |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 81609ms | `none` | — | — | — | |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `READY` | ✅ | ✅ | ✅ | No | 1 | 45866ms | `none` | — | — | — | |
| `p08` | make something fun and fast-paced | `READY` | ✅ | ✅ | ✅ | No | 1 | 45856ms | `none` | — | — | — | |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `READY` | ✅ | ✅ | ✅ | No | 1 | 43961ms | `none` | — | — | ✅ | |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `READY` | ✅ | ✅ | ✅ | No | 1 | 47414ms | `none` | — | — | — | |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 74493ms | `none` | — | ✅ | — | |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 77991ms | `none` | — | ✅ | — | |

## Check Definitions & Failure Taxonomy
- **schema**: GameIR failed validation rules or schema constraints.
- **rendering**: Game canvas failed to mount or Phaser QA hook not ready.
- **interaction**: Player movement, velocity consistency, attack response, or controls failed.
- **objective**: Win condition unreachable, score progress halted, or playability thresholds failed.
- **restart**: Scene restart failed to restore fresh initial playing state.
- **timeout**: Planner, QA execution, or repair timed out.
- **provider_error**: Model HTTP error, quota 429, or network disconnect.
- **not_run**: Prompt omitted due to request budget or quota fast-fail.
