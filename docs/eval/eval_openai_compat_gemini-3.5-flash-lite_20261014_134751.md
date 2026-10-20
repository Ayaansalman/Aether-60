# AETHER Full-Pipeline Evaluation Report: openai_compat (gemini-3.5-flash-lite)


> **Run A2: after repair-prompt fix, same prompts; these were dev cases, not an unbiased estimate**


- **Benchmark Date:** 2026-10-14 13:47:51 UTC
- **Provider:** `openai_compat`
- **Model ID:** `gemini-3.5-flash-lite`
- **QA Execution Mode:** `real`
- **Run Status:** `complete`
- **Request Timeout:** 60.0 s
- **Sample Size:** 3 prompt(s)
- **Total Model Requests:** 7

## Summary Metrics

| Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Spec Validation** | **3/3 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **0/3 (0.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **2/3 (66.7%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **2/2 (100.0%)** | Repairs that transitioned failing game to READY |
| **Theme Match Rate** | **N/A** | Faithful to specified theme |
| **Objective Match Rate** | **2/2 (100.0%)** | Faithful to specified objective |
| **Limitation Honesty Rate** | **N/A (no limitation prompts)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **3 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **75266.5 ms** | Model response prompts only |
| **Min Latency** | **28490.8 ms** | Model response prompts only |
| **Max Latency** | **76690.1 ms** | Model response prompts only |

## Per-Prompt Evaluation Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category | Theme | Obj | Limit | Adherence (1-5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `FAILED` | ✅ | ❌ | ❌ | No | 1 | 28491ms | `interaction` | — | — | — | |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 76690ms | `none` | — | ✅ | — | |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 75266ms | `none` | — | ✅ | — | |

## Check Definitions & Failure Taxonomy
- **schema**: GameIR failed validation rules or schema constraints.
- **rendering**: Game canvas failed to mount or Phaser QA hook not ready.
- **interaction**: Player movement, velocity consistency, attack response, or controls failed.
- **objective**: Win condition unreachable, score progress halted, or playability thresholds failed.
- **restart**: Scene restart failed to restore fresh initial playing state.
- **timeout**: Planner, QA execution, or repair timed out.
- **provider_error**: Model HTTP error, quota 429, or network disconnect.
- **not_run**: Prompt omitted due to request budget or quota fast-fail.
