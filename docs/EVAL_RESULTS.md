# AETHER Pipeline Evaluation Results

This document records empirical evaluation results of the AETHER Game Synthesis and Self-Repair pipeline across models and runs.

---

## Multi-Model Evaluation Comparison

| Run | Model | Provider | Date (UTC) | Status | Playable@1 | Playable@3 | Repair Rate | Median Latency | Requests |
|---|---|---|---|---|---|---|---|---|---|
| `Run D` | `gemini-3.5-flash-lite` | `openai_compat` | 2026-10-16 09:17:54 | `complete` | 9/12 (75.0%) | 12/12 (100.0%) | 3/3 (100.0%) | 47020ms | 18 |
| `gemini-3.8-flash` | `gemini-3.8-flash` | `openai_compat` | 2026-10-15 17:22:36 | `incomplete` | 0/0 (0.0%) | 0/0 (0.0%) | N/A (0/0) | N/A | 3 |
| `mock-planner-v1` | `mock-planner-v1` | `mock` | 2026-10-14 14:22:13 | `complete` | 10/11 (90.9%) | 11/11 (100.0%) | 1/1 (100.0%) | 44111ms | 12 |
| `Run A2` | `gemini-3.5-flash-lite` | `openai_compat` | 2026-10-14 13:47:51 | `complete` | 0/3 (0.0%) | 2/3 (66.7%) | 2/2 (100.0%) | 75266ms | 7 |
| `gemini-3.8-flash` | `gemini-3.8-flash` | `openai_compat` | 2026-10-14 12:05:23 | `incomplete` | 1/1 (100.0%) | 1/1 (100.0%) | N/A (0/0) | 66639ms | 5 |
| `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` | `openai_compat` | 2026-10-14 11:55:28 | `complete` | 9/12 (75.0%) | 9/12 (75.0%) | 0/2 (0.0%) | 45808ms | 14 |
| `mock` | `mock` | `mock` | 2026-10-14 09:41:33 | `complete` | 2/4 (50.0%) | 4/4 (100.0%) | 2/2 (100.0%) | 59973ms | 6 |
| `mock` | `mock` | `mock` | 2026-10-14 09:15:44 | `complete` | 12/12 (100.0%) | 12/12 (100.0%) | N/A (0/0) | 187ms | 12 |

---

## Run D: upgraded engine (GameIR with new enemy types, layouts and defeat_enemies); same 12 prompts as Run A, so engine and repair prompt differ from Run A


> **Date:** 2026-10-16 09:17:54 UTC  
> **Provider:** `openai_compat`  
> **Model:** `gemini-3.5-flash-lite`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`  
> **Total Model Requests:** 18

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **12/12 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **9/12 (75.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **12/12 (100.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **3/3 (100.0%)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **5/5 (100.0%)** | Faithful to target prompt theme |
| **Objective Fidelity** | **6/7 (85.7%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **1/1 (100.0%)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **11 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **47020.5 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 62223 ms | `none` |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `READY` | ✅ | ✅ | ✅ | No | 1 | 45399 ms | `none` |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `READY` | ✅ | ✅ | ✅ | No | 1 | 46627 ms | `none` |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `READY` | ✅ | ✅ | ✅ | No | 1 | 48402 ms | `none` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 44688 ms | `none` |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 81609 ms | `none` |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `READY` | ✅ | ✅ | ✅ | No | 1 | 45866 ms | `none` |
| `p08` | make something fun and fast-paced | `READY` | ✅ | ✅ | ✅ | No | 1 | 45856 ms | `none` |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `READY` | ✅ | ✅ | ✅ | No | 1 | 43961 ms | `none` |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `READY` | ✅ | ✅ | ✅ | No | 1 | 47414 ms | `none` |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 74493 ms | `none` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 77991 ms | `none` |

---

## Evaluation Run: gemini-3.8-flash (2026-10-15 17:22:36 UTC)


> **Date:** 2026-10-15 17:22:36 UTC  
> **Provider:** `openai_compat`  
> **Model:** `gemini-3.8-flash`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`  
> **Total Model Requests:** 3

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **0/0 (0.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **0/0 (0.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **0/0 (0.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **N/A (0/0)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **N/A** | Faithful to target prompt theme |
| **Objective Fidelity** | **N/A** | Faithful to target objective criteria |
| **Limitation Honesty** | **N/A (no limitation prompts)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **0 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **0.0 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p08` | make something fun and fast-paced | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `NOT_RUN` | — | — | — | No | 0 | — | `provider_error` |

---

## Evaluation Run: mock-planner-v1 (2026-10-14 14:22:13 UTC)

> **MOCK PROVIDER: not a real model, results are not evidence**  

> **Date:** 2026-10-14 14:22:13 UTC  
> **Provider:** `mock`  
> **Model:** `mock-planner-v1`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_mock_mock_20261014_142213.json`  
> **Total Model Requests:** 12

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **11/11 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **10/11 (90.9%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **11/11 (100.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **1/1 (100.0%)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **5/5 (100.0%)** | Faithful to target prompt theme |
| **Objective Fidelity** | **5/6 (83.3%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **1/1 (100.0%)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **0 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **44110.6 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 46743 ms | `none` |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `READY` | ✅ | ✅ | ✅ | No | 1 | 44378 ms | `none` |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `READY` | ✅ | ✅ | ✅ | No | 1 | 43844 ms | `none` |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `READY` | ✅ | ✅ | ✅ | No | 1 | 44660 ms | `none` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 42480 ms | `none` |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 87055 ms | `none` |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `READY` | ✅ | ✅ | ✅ | No | 1 | 43895 ms | `none` |
| `p08` | make something fun and fast-paced | `READY` | ✅ | ✅ | ✅ | No | 1 | 44963 ms | `none` |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `READY` | ✅ | ✅ | ✅ | No | 1 | 44111 ms | `none` |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `READY` | ✅ | ✅ | ✅ | No | 1 | 42364 ms | `none` |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `READY` | ✅ | ✅ | ✅ | No | 1 | 42092 ms | `none` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |

---

## Run A2: after repair-prompt fix, same prompts; these were dev cases, not an unbiased estimate


> **Date:** 2026-10-14 13:47:51 UTC  
> **Provider:** `openai_compat`  
> **Model:** `gemini-3.5-flash-lite`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`  
> **Total Model Requests:** 7

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **3/3 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **0/3 (0.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **2/3 (66.7%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **2/2 (100.0%)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **N/A** | Faithful to target prompt theme |
| **Objective Fidelity** | **2/2 (100.0%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **N/A (no limitation prompts)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **3 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **75266.5 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `FAILED` | ✅ | ❌ | ❌ | No | 1 | 28491 ms | `interaction` |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 76690 ms | `none` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 75266 ms | `none` |

---

## Evaluation Run: gemini-3.8-flash (2026-10-14 12:05:23 UTC)


> **Date:** 2026-10-14 12:05:23 UTC  
> **Provider:** `openai_compat`  
> **Model:** `gemini-3.8-flash`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json`  
> **Total Model Requests:** 5

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **1/1 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **1/1 (100.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **1/1 (100.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **N/A (0/0)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **1/1 (100.0%)** | Faithful to target prompt theme |
| **Objective Fidelity** | **1/1 (100.0%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **N/A (no limitation prompts)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **1 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **66639.2 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 66639 ms | `none` |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `FAILED` | — | ❌ | ❌ | No | 1 | 121924 ms | `timeout` |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p08` | make something fun and fast-paced | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `NOT_RUN` | — | — | — | No | 0 | — | `not_run` |

---

## Evaluation Run: gemini-3.5-flash-lite (2026-10-14 11:55:28 UTC)


> **Date:** 2026-10-14 11:55:28 UTC  
> **Provider:** `openai_compat`  
> **Model:** `gemini-3.5-flash-lite`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`  
> **Total Model Requests:** 14

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **11/12 (91.7%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **9/12 (75.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **9/12 (75.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **0/2 (0.0%)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **5/5 (100.0%)** | Faithful to target prompt theme |
| **Objective Fidelity** | **6/6 (100.0%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **1/1 (100.0%)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **7 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **45807.6 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 68086 ms | `none` |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `READY` | ✅ | ✅ | ✅ | No | 1 | 50825 ms | `none` |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `READY` | ✅ | ✅ | ✅ | No | 1 | 50224 ms | `none` |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `READY` | ✅ | ✅ | ✅ | No | 1 | 49768 ms | `none` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 46945 ms | `none` |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `FAILED` | ✅ | ❌ | ❌ | Att | 1 | 32177 ms | `interaction` |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `READY` | ✅ | ✅ | ✅ | No | 1 | 53163 ms | `none` |
| `p08` | make something fun and fast-paced | `READY` | ✅ | ✅ | ✅ | No | 1 | 43328 ms | `none` |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `READY` | ✅ | ✅ | ✅ | No | 1 | 43949 ms | `none` |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `READY` | ✅ | ✅ | ✅ | No | 1 | 44670 ms | `none` |
| `s01` | an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point | `FAILED` | ✅ | ❌ | ❌ | Att | 1 | 22010 ms | `interaction` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `FAILED` | ❌ | ❌ | ❌ | No | 1 | 3763 ms | `schema` |

---

## Evaluation Run: mock (2026-10-14 09:41:33 UTC)

> **MOCK PROVIDER: not a real model, results are not evidence**  

> **Date:** 2026-10-14 09:41:33 UTC  
> **Provider:** `mock`  
> **Model:** `mock`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `real`  
> **Artifacts:** `docs/eval/eval_mock_mock_20261014_094133.json`  
> **Total Model Requests:** 6

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **4/4 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **2/4 (50.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **4/4 (100.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **2/2 (100.0%)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **2/2 (100.0%)** | Faithful to target prompt theme |
| **Objective Fidelity** | **4/4 (100.0%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **N/A (no limitation prompts)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **2 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **59973.3 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 47675 ms | `none` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 42399 ms | `none` |
| `repair_demo` | repair demo: impossible arena challenge with 12 fast enemies | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 72272 ms | `none` |
| `s01` | a repair demo stress challenge: an impossible claustrophobic bullet-hell arena with 50 relentless pursuers moving twice player speed, zero recovery, and 1 hit point | `READY` | ✅ | ❌ | ✅ | Succ | 2 | 73036 ms | `none` |

---

## Evaluation Run: mock (2026-10-14 09:15:44 UTC)

> **MOCK PROVIDER: not a real model, results are not evidence**  

> **Date:** 2026-10-14 09:15:44 UTC  
> **Provider:** `mock`  
> **Model:** `mock`  
> **Fallback Status:** disabled (`MODEL_FALLBACKS=""`, `AETHER_ALLOW_FALLBACK=0`)  
> **QA Mode:** `fake`  
> **Artifacts:** `docs/eval/eval_mock_mock_20261014_091544.json`  
> **Total Model Requests:** 12

### Summary Metrics

| Evaluation Metric | Rate / Value | Note |
|---|---|---|
| **First-Response Validation Rate** | **12/12 (100.0%)** | Evaluated over prompts with model response |
| **Playable @ Attempt 1** | **12/12 (100.0%)** | Initial build passed all critical QA |
| **Playable @ Attempt 3** | **12/12 (100.0%)** | Pass after up to 2 repair iterations |
| **Repair Success Rate** | **N/A (0/0)** | Successful repairs over repair attempts |
| **Theme Fidelity** | **5/5 (100.0%)** | Faithful to target prompt theme |
| **Objective Fidelity** | **7/7 (100.0%)** | Faithful to target objective criteria |
| **Limitation Honesty** | **12/12 (100.0%)** | Prompts with expect_limitation=True |
| **Non-Limitation Disclosed** | **0 prompt(s)** | Disclosed limitations on standard prompts |
| **Median Latency** | **187.3 ms** | Model response prompts only |

### Per-Prompt Results

| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |
|---|---|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | `READY` | ✅ | ✅ | ✅ | No | 1 | 237 ms | `none` |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | `READY` | ✅ | ✅ | ✅ | No | 1 | 178 ms | `none` |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | `READY` | ✅ | ✅ | ✅ | No | 1 | 177 ms | `none` |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | `READY` | ✅ | ✅ | ✅ | No | 1 | 184 ms | `none` |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | `READY` | ✅ | ✅ | ✅ | No | 1 | 210 ms | `none` |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | `READY` | ✅ | ✅ | ✅ | No | 1 | 193 ms | `none` |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | `READY` | ✅ | ✅ | ✅ | No | 1 | 183 ms | `none` |
| `p08` | make something fun and fast-paced | `READY` | ✅ | ✅ | ✅ | No | 1 | 188 ms | `none` |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | `READY` | ✅ | ✅ | ✅ | No | 1 | 193 ms | `none` |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | `READY` | ✅ | ✅ | ✅ | No | 1 | 200 ms | `none` |
| `s01` | a repair demo stress challenge: an impossible claustrophobic bullet-hell arena with 50 relentless pursuers moving twice player speed, zero recovery, and 1 hit point | `READY` | ✅ | ✅ | ✅ | No | 1 | 185 ms | `none` |
| `s02` | an extremely brutal survival nightmare with 45 lethal chaser monsters moving at maximum speed in a tiny arena with only 1 health | `READY` | ✅ | ✅ | ✅ | No | 1 | 187 ms | `none` |

---

## Comparative Analysis: Run C (gemini-3.8-flash) vs Run A (gemini-3.5-flash-lite)

Empirical head-to-head comparison between Run A (`gemini-3.5-flash-lite`, 12 prompts complete) and Run C (`gemini-3.8-flash`, standalone real-model evaluation with fallback disabled).

| Evaluation Dimension | Run A: `gemini-3.5-flash-lite` | Run C Rerun (2026-10-15): `gemini-3.8-flash` | Run C Attempt 1 (2026-10-14): `gemini-3.8-flash` | Primary Artifact Citation |
|---|---|---|---|---|
| **Artifact File** | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` | `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json` | `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` | JSON benchmark artifacts |
| **Execution Date** | `2026-10-14 11:55:28 UTC` | `2026-10-15 17:22:36 UTC` | `2026-10-14 12:05:23 UTC` | UTC timestamp |
| **Provider / Fallback** | `openai_compat` / Disabled | `openai_compat` / Disabled | `openai_compat` / Disabled | Fallback strictly disabled |
| **Prompts Attempted** | 12 / 12 | 12 / 12 | 2 / 12 | Canonical prompt benchmark |
| **Prompts Completed** | **12 / 12 (100.0%)** | **0 / 12 (0.0%)** | **1 / 12 (8.3%)** | Completed model responses |
| **Run Status** | `complete` | `incomplete` (preflight timeout) | `incomplete` (p02 timeout) | Upstream provider status |
| **First-Response Validation Rate** | **11/12 (91.7%)** | **0/0 (0.0%)** | **1/1 (100.0%)** | `spec_validated_first_rate` |
| **Playable @ Attempt 1** | **9/12 (75.0%)** | **0/0 (0.0%)** | **1/1 (100.0%)** | `playable_at_1_rate` |
| **Playable @ Attempt 3** | **9/12 (75.0%)** | **0/0 (0.0%)** | **1/1 (100.0%)** | `playable_at_3_rate` |
| **Repair Success Rate** | **0/2 (0.0%)** | **N/A (0/0)** | **N/A (0/0)** | `repair_success_rate` |
| **Failures by Category** | 2 `interaction` (`p06`, `s01`), 1 `schema` (`s02`) | 12 `provider_error` (preflight timeout) | 1 `timeout` (`p02`), 10 `not_run` | `failure_category` taxonomy |
| **Median Latency** | **45,807.6 ms** | **0.0 ms** | **66,639.2 ms** | `median_latency_ms` |

### Key Empirical Findings & Plain Comparison

1. **Completion & Endpoint Reliability**:
   - **Run A (`gemini-3.5-flash-lite`)** successfully completed all 12 benchmark prompts without dropping requests (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`).
   - **Run C (`gemini-3.8-flash`)** timed out in both attempts when fallback was disabled:
     - In the 2026-10-15 rerun (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`), the upstream health ping timed out after 60.0s, resulting in 0 prompts completed and all 12 categorized as `provider_error`. Cause not established.
     - In the 2026-10-14 attempt (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json`), prompt `p01` reached `READY` in 66.6s, but prompt `p02` timed out after 121.9s, halting the run. Cause not established.

2. **Latency Comparison**:
   - `gemini-3.5-flash-lite` demonstrated manageable latency for top-down synthesis: median end-to-end latency was 45,807.6 ms in Run A (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`; min: 3,762.6 ms, max: 68,085.9 ms) and 47,020.5 ms in Run D (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), whereas planner-only median in Phase 0 bench with gemini-3.8-flash was 17.3s (`docs/eval/planner_gemini-3.8-flash_benchmark.json`).
   - `gemini-3.8-flash` timed out in both Run C attempts (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` and `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`), cause not established.

3. **Playability & Synthesis Quality**:
   - On the single prompt that `gemini-3.8-flash` completed (`p01`), it achieved 100% first-response validation and 100% Playable@1 with all 17 automated browser QA checks passing.
   - **Caution on Interpretation**: We do **not** claim `gemini-3.8-flash` is superior or an improvement over `gemini-3.5-flash-lite`. The sample size of successful completions for `gemini-3.8-flash` is essentially negligible ($N=1$ on Oct 14, $N=0$ on Oct 15). Due to upstream timeouts, `gemini-3.5-flash-lite` remains the far more reliable production model for AETHER.

---

## Comparative Analysis: Run A, Run A2, and Run D (Gemini 3.5 Flash Lite across Milestones)

Comparative evaluation of the primary production model (`gemini-3.5-flash-lite`) across the baseline engine (Run A), repair-prompt tuning on dev cases (Run A2), and the upgraded GameIR mechanic variety engine (Run D).

| Metric / Dimension | Run A: Baseline Engine | Run A2: Repair Prompt Tuning | Run D: Upgraded Variety Engine | Primary Artifact Citations |
|---|---|---|---|---|
| **Artifact File** | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json` | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json` | Exact JSON evaluation artifacts |
| **Execution Date** | 2026-10-14 11:55:28 UTC | 2026-10-14 13:47:51 UTC | 2026-10-16 09:17:54 UTC | Benchmark execution timestamp |
| **Engine Scope** | Baseline (chaser-only, open layout, basic repair prompt) | Baseline engine + tuned repair prompt (explicit bounds) | Upgraded engine (5 enemy AI, 4 layouts, defeat_enemies, visual overrides, dynamic QA approach timing) | Architectural engine version |
| **Prompts Attempted** | 12 / 12 | 3 / 3 (dev stress prompts only) | 12 / 12 | Prompt suite scope |
| **Prompts Completed** | **12 / 12 (100.0%)** | **3 / 3 (100.0%)** | **12 / 12 (100.0%)** | Model responses received |
| **Run Status** | `complete` | `complete` | `complete` | Benchmark completion status |
| **First-Response Validation Rate** | **11/12 (91.7%)** (`s02` failed schema) | **3/3 (100.0%)** | **12/12 (100.0%)** (12/12 first-valid) | `spec_validated_first_rate` |
| **Playable @ Attempt 1** | **9/12 (75.0%)** | **0/3 (0.0%)** (stress prompts only) | **9/12 (75.0%)** | `playable_at_1_rate` |
| **Playable @ Attempt 3** | **9/12 (75.0%)** | **2/3 (66.7%)** | **12/12 (100.0%)** | `playable_at_3_rate` |
| **Repair Attempts / Successes** | **0/2 (0.0%)** (p06, s01 failed repair; s02 skipped due to schema) | **2/2 (100.0%)** (s01, s02 repaired; p06 not repaired) | **3/3 (100.0%)** (p06, s01, s02 all repaired to READY) | `repair_success_rate` |
| **Initial Failures (Attempt 1)** | 2 `interaction` (`p06`, `s01`), 1 `schema` (`s02`) | 3 `interaction` (`p06`, `s01`, `s02`) | 3 `interaction` (`p06`, `s01`, `s02`) | Attempt 1 failure taxonomy |
| **Final Unresolved Failures** | 2 `interaction` (`p06`, `s01`), 1 `schema` (`s02`) | 1 `interaction` (`p06`) | **0** (all 12 reached `READY`) | Final failure taxonomy |
| **Median Latency** | **45,807.6 ms** | **75,266.5 ms** (all repairs) | **47,020.5 ms** | `median_latency_ms` |
| **Total Model Requests** | 14 | 7 | 18 | `total_model_requests` |

### Plain-Language Comparison & Engineering Differences

1. **Engine, QA Runner, and Repair Differences**:
   - The engine, QA runner, and repair prompt differ from Run A, so the comparison between Run A and Run D is not single-variable.
   - In Phase 9, `GameIR v1.0` was expanded to support 5 enemy AI types (`chaser`, `bouncer`, `patroller`, `dasher`, `shooter`), 4 arena layouts (`open`, `pillars`, `lanes`, `maze`), the `defeat_enemies` objective, and visual shape/HUD overrides.
   - The repair prompt was updated in Phase 5.7 to include measured vs. required thresholds and valid enum bounds, and the QA runner in Phase 8 was updated with dynamic approach timing in Check 6.
   - Run D prompts are the same 12 prompts as Run A and do not measure the new enemy types and layouts.

2. **Repair Performance & Development-Set Context**:
   - In **Run A** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`), 0 of 2 repairs succeeded (0.0%). `p06` and `s01` failed QA on Attempt 1 and failed repair; `s02` failed Pydantic validation on Attempt 1 and did not enter repair.
   - In **Run A2** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`), evaluating 3 dev stress prompts, 2 of 2 repair attempts succeeded (`s01` and `s02`), while `p06` was not repaired.
   - In **Run D** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), 3 of 3 repair attempts succeeded (100.0%): `p06`, `s01`, and `s02` all failed on Attempt 1 and transitioned to `READY` on Attempt 2.
   - `p06`, `s01`, and `s02` failed first in Runs A, A2, and D and were also the cases used to tune the QA check and repair prompt, so Run D is a development-set result, not a held-out estimate.

3. **Playable@1 vs Playable@3**:
   - Playable@1 equals Run A (9/12, 75.0%). In both Run A and Run D, the same 9 standard prompts (`p01`–`p05`, `p07`–`p10`) passed on Attempt 1.
   - Playable@3 reached 12/12 (100.0%) in Run D with 3/3 repairs completing, compared to 9/12 (75.0%) in Run A where 0/2 repairs succeeded.

4. **Latency Profile**:
   - Median latency in Run D was **47,020.5 ms** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), compared to Run A's **45,807.6 ms** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`). Total model requests were 18 in Run D compared to 14 in Run A.

5. **Sample Size & Variation Caveats**:
   - One run per prompt; results can vary between runs.
   - All runs evaluate a curated 12-prompt benchmark (or 3 prompts in Run A2). This sample size is too small to serve as an unbiased general benchmark.

---

## How to Re-Run with Another Model / Provider

To evaluate against any model without an AI agent, use `scripts/run_real_eval.ps1`:

```powershell
# Run with Gemini 3.5 Flash Lite (default, 12 prompts, real browser QA)
.\scripts\run_real_eval.ps1 -ModelId "gemini-3.5-flash-lite" -Delay 5.0 -MaxRequests 60

# Run with Gemini 3.8 Flash (larger budget & pacing delay)
.\scripts\run_real_eval.ps1 -ModelId "gemini-3.8-flash" -Delay 13.0 -MaxRequests 60

# Safe dry-run test with Mock Provider (zero real API calls)
.\scripts\run_real_eval.ps1 -Mock
```

The script will:
1. Configure process environment variables (disabling fallback and setting the target model ID).
2. Automatically start the Vite server for headless Playwright QA.
3. Execute the full benchmark suite (`run_eval.py`).
4. Stop the Vite server cleanly.
5. Copy artifacts to `docs/eval/` and regenerate `docs/EVAL_RESULTS.md` from all historical runs.
