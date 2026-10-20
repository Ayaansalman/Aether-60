# AETHER Real-Model Planner Evaluation Report

> **Target Spec:** 60% Milestone Verification  
> **Source Artifact:** `artifacts/bench/planner_gemini-3.8-flash_20261012_115953.json`

## Executive Summary

| Parameter | Value |
|---|---|
| **Provider** | `OpenAICompatProvider` (`MODEL_PROVIDER=openai_compat`) |
| **Model ID** | `gemini-3.8-flash` |
| **Benchmark Date** | `2026-10-12 11:59:53 UTC` |
| **Sample Size** | 10 prompts |
| **First-Response Validation Rate** | **90.0%** (9 / 10) |
| **Final Success Rate** | **90.0%** (9 / 10) |
| **Theme & Objective Match Rate** | **100.0%** |
| **Limitation Honesty Rate** | **100.0%** |
| **Median Latency** | **17311.0 ms** |
| **Max Latency** | **33039 ms** |

---

## Per-Prompt Detailed Results

| ID | Prompt | 1st Valid | Final OK | Attempts | Latency (ms) | Limitations Disclosed | Notes |
|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | ✅ Yes | ✅ Pass | 1 | 27910 | ✅ (1) | Spooky wizard archetype with crystal collectibles and ghost chasers |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | ✅ Yes | ✅ Pass | 1 | 20446 | ✅ (1) | Robot vs drone waves gathering batteries in sci-fi setting |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | ✅ Yes | ✅ Pass | 1 | 33039 | ✅ (2) | Pirate theme collecting coins/treasure |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | ✅ Yes | ✅ Pass | 1 | 16502 | ✅ (2) | Cozy theme with forest spirit and star collectibles |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | ✅ Yes | ✅ Pass | 1 | 18120 | ✅ (2) | Cyberpunk survival mode with 45 second time limit |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | ✅ Yes | ✅ Pass | 1 | 7856 | ✅ (1) | High difficulty challenge with fast chaser enemies and slow player movement |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | ✅ Yes | ✅ Pass | 1 | 7185 | ✅ (2) | Thematic setting with no explicit genre keywords; must adapt to arena survival |
| `p08` | make something fun and fast-paced | ✅ Yes | ✅ Pass | 1 | 10699 | — (0) | Vague intent without theme or mechanics specified |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | ✅ Yes | ✅ Pass | 1 | 18933 | ✅ (3) | Unsupported 3D MMORPG open world multiplayer racing; must report limitations honestly |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | ❌ No | ❌ Fail | 1 | 0 | — (0) | Contradictory prompt claiming peaceful with no enemies then battling 50 monsters |

---

## Failed Validation / Generation Analysis

### Prompt `p10`:
- **Input Prompt:** `a peaceful game with no enemies where you must battle 50 ferocious monsters to survive`
- **Result:** Failed on first response (`MODEL_HTTP_ERROR`).
- **Raw Error from Endpoint:**
  ```text
  Model HTTP 429 error from https://generativelanguage.googleapis.com/v1beta/openai/chat/completions: [
    {
      "error": {
        "code": 429,
        "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-..."
      }
    }
  ]
  ```
- **Root Cause:** Upstream Google Gemini API free-tier quota exhaustion / rate-limiting (HTTP 429 Too Many Requests). The upstream server refused the completion request due to rapid successive calls exhausting the free tier bucket. In production and evaluation, spacing requests with `BENCH_DELAY_SECONDS` (default 4s) and exponential backoff retry handles transient bursts, but hard daily free-tier quotas result in HTTP 429 errors.
