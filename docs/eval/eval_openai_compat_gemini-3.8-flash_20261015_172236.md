# AETHER Full-Pipeline Evaluation Report: openai_compat (gemini-3.8-flash)



- **Benchmark Date:** 2026-10-15 17:22:36 UTC
- **Provider:** `openai_compat`
- **Model ID:** `gemini-3.8-flash`
- **QA Execution Mode:** `real`
- **Run Status:** `incomplete`
- **Request Timeout:** 60.0 s
- **Sample Size:** 12 prompt(s)
- **Total Model Requests:** 3

## Summary Metrics

| Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Spec Validation** | **0/0 (0.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **0/0 (0.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **0/0 (0.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **N/A (0/0)** | Repairs that transitioned failing game to READY |
| **Theme Match Rate** | **N/A** | Faithful to specified theme |
| **Objective Match Rate** | **N/A** | Faithful to specified objective |
| **Limitation Honesty Rate** | **N/A (no limitation prompts)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **0 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **0.0 ms** | Model response prompts only |
| **Min Latency** | **0.0 ms** | Model response prompts only |
| **Max Latency** | **0.0 ms** | Model response prompts only |

## Per-Prompt Evaluation Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category | Theme | Obj | Limit | Adherence (1-5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p08` | make something fun and fast-paced | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` | — | — | — | |

## Check Definitions & Failure Taxonomy
- **schema**: GameIR failed validation rules or schema constraints.
- **rendering**: Game canvas failed to mount or Phaser QA hook not ready.
- **interaction**: Player movement, velocity consistency, attack response, or controls failed.
- **objective**: Win condition unreachable, score progress halted, or playability thresholds failed.
- **restart**: Scene restart failed to restore fresh initial playing state.
- **timeout**: Planner, QA execution, or repair timed out.
- **provider_error**: Model HTTP error, quota 429, or network disconnect.
- **not_run**: Prompt omitted due to request budget or quota fast-fail.
