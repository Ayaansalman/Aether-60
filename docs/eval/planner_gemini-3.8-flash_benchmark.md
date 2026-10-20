# AETHER Game Planner Benchmark Report
**Model ID:** `gemini-3.8-flash`  
**Date:** `2026-10-12 16:33:53 UTC`  
**Provider:** `OpenAICompatProvider`  

## Summary Metrics

| Metric | Rate | Ratio | Details |
|---|---|---|---|
| **First-Response Validation Rate** | **100.0%** | **10/10** | Responded calls that passed schema validation on attempt 1 |
| **Final Success Rate** | **100.0%** | **10/10** | Responded calls that produced valid GameIR within max attempts |
| **Theme Match Rate** | **100.0%** | **5/5** | Skipped: `p06`, `p07`, `p08`, `p09`, `p10` (`expected_theme` is null) |
| **Objective Match Rate** | **100.0%** | **5/5** | Skipped: `p06`, `p07`, `p08`, `p09`, `p10` (`expected_objective_type` is null) |
| **Theme & Objective Match Rate** | **100.0%** | **5/5** | Skipped: `p06`, `p07`, `p08`, `p09`, `p10` (both expected values null) |
| **Limitation Honesty Rate** | **100.0%** | **1/1** | Skipped: `p01`, `p02`, `p03`, `p04`, `p05`, `p06`, `p07`, `p08`, `p10` (`expect_limitation` is false) |
| **Median Latency** | **17311.0 ms** | **10 calls** | Typical completion latency (0 excluded: error before response) |
| **Max Latency** | **33039 ms** | **10 calls** | Peak completion latency (0 excluded: error before response) |

## Detailed Prompt Results

| ID | Prompt | Status | 1st Valid | Attempts | Latency (ms) | Limitations Disclosed | Notes |
|---|---|---|---|---|---|---|---|
| `p01` | a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me | ✅ Pass | ✅ Yes | 1 | 27910 | ✅ (1) | Spooky wizard archetype with crystal collectibles and ghost chasers |
| `p02` | a robot surviving against waves of flying drones while gathering energy batteries | ✅ Pass | ✅ Yes | 1 | 20446 | ✅ (1) | Robot vs drone waves gathering batteries in sci-fi setting |
| `p03` | a pirate captain collecting gold treasure chests while rival skeleton ships pursue | ✅ Pass | ✅ Yes | 1 | 33039 | ✅ (2) | Pirate theme collecting coins/treasure |
| `p04` | a cozy forest spirit gathering fallen glowing stars in a peaceful enchanted grove | ✅ Pass | ✅ Yes | 1 | 16502 | ✅ (2) | Cozy theme with forest spirit and star collectibles |
| `p05` | a neon cyberpunk hacker surviving rogue security grid drones for 45 seconds | ✅ Pass | ✅ Yes | 1 | 18120 | ✅ (2) | Cyberpunk survival mode with 45 second time limit |
| `p06` | a difficult high-stakes arena where the player moves slowly and enemies chase at extreme speeds | ✅ Pass | ✅ Yes | 1 | 7856 | ✅ (1) | High difficulty challenge with fast chaser enemies and slow player movement |
| `p07` | ancient pyramids, pharaohs, scarabs, and sandstorms | ✅ Pass | ✅ Yes | 1 | 7185 | ✅ (2) | Thematic setting with no explicit genre keywords; must adapt to arena survival |
| `p08` | make something fun and fast-paced | ✅ Pass | ✅ Yes | 1 | 10699 | — | Vague intent without theme or mechanics specified |
| `p09` | a 3D open-world MMORPG racing game with 64 players and cross-platform multiplayer | ✅ Pass | ✅ Yes | 1 | 18933 | ✅ (3) | Unsupported 3D MMORPG open world multiplayer racing; must report limitations honestly |
| `p10` | a peaceful game with no enemies where you must battle 50 ferocious monsters to survive | ✅ Pass | ✅ Yes | 1 | 11970 | ✅ (1) | Contradictory prompt claiming peaceful with no enemies then battling 50 monsters |