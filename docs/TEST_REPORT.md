# AETHER Comprehensive Test & Verification Report

This document records the empirical results across all test suites, automated QA fixtures, end-to-end smoke pipelines, and full-pipeline evaluation benchmarks. All metrics are sourced directly from committed machine artifacts.

---

## 1. Test Suite Summary Dashboard

| Suite | Harness | Target / Description | Pass / Total | Result |
|---|---|---|---|---|
| **Backend Unit & Integration** | `pytest 8.2.0` | Schemas, Jobs, Orchestrator, Repair, Providers, Fallback, Wall Physics | **88 / 88** | **PASS** |
| **Frontend TypeScript** | `tsc --noEmit` | Strict type checking across React 19 / Vite / Phaser client | **0 errors** | **PASS** |
| **Frontend Production Build** | `npm run build` | Production bundle generation | **0 errors** | **PASS** |
| **Browser QA: Demo Routes** | `Playwright Sync` | 17 spec-level checks on all 4 demo routes (`run_qa_all.py`) | **68 / 68 (17/17 x 4)** | **PASS** |
| **Browser QA: Fixture Traps** | `Playwright Sync` | Detection of 3 seeded failure modes (`run_qa_fixtures.py`) | **3 / 3 detected** | **PASS** |
| **End-to-End Pipeline Smoke** | `e2e_smoke.py` | Full prompt $\rightarrow$ SQLite $\rightarrow$ QA $\rightarrow$ Playwright canvas render | **1 / 1** | **PASS** |
| **Automated Repair Loop Demo** | `repair_demo.py` | Lethal spec diagnosis $\rightarrow$ `GameIRPatch` $\rightarrow$ Playable@2 | **1 / 1** | **PASS** |
| **Slow-Player Wall Physics QA** | `verify_slow_player_qa.py` | Scaled wall-slide approach for slow speeds ($100\text{ px/s}$ and `p06`) | **2 / 2** | **PASS** |

---

## 2. Headless Browser QA Verification (`run_qa_all.py`)

All 4 baseline game routes pass all 17 spec-level checks:

| Route | Theme | Attack Mode | Objective | Idle Survival Margin | Overall QA |
|---|---|---|---|---|---|
| `/play/demo` | `fantasy` | `projectile` | `collect_count` (8 crystals) | 5.31s (+77.0% margin above 3.0s) | **17 / 17 PASS** |
| `/play/demo-survive` | `sci_fi` | `projectile` | `survive_seconds` (30s) | 4.23s (+41.0% margin above 3.0s) | **17 / 17 PASS** |
| `/play/demo-melee` | `spooky` | `melee` | `collect_count` (10 items) | 5.34s (+78.0% margin above 3.0s) | **17 / 17 PASS** |
| `/play/demo-avoid` | `cozy` | `avoid_only` | `collect_count` (5 stars) | 5.28s (+76.0% margin above 3.0s) | **17 / 17 PASS** |

---

## 3. Known-Broken Fixture Detection (`run_qa_fixtures.py`)

Proves that QA checks are sensitive and reject broken behavior:

| Fixture URL | Injected Fault | Detected Failure Mode | Duration | Result |
|---|---|---|---|---|
| `/play/demo?test=1&bug=restart_keeps_hp` | Health retained across restart | `restart_resets_after_win` & `restart_resets_after_lose` failed | 41.34s | **DETECTED** |
| `/play/demo?test=1&bug=no_win` | Objective completion ignores win trigger | `win_reachable` failed | 46.19s | **DETECTED** |
| `/play/demo-too-hard` | 12 enemies @ 240 px/s, 1 HP | `idle_survival_min_seconds` (0.8s) & `flee_bot_survives` failed | 31.65s | **DETECTED** |

---

## 4. Full Pipeline Empirical Evaluation Runs

The numbers below are copied directly from the evaluation artifacts stored in `docs/eval/`.

### 4.1 Comparative Model Performance Summary

| Evaluation Run | Target Model | Provider | Artifact File | First Valid | Playable@1 | Playable@3 | Repair Rate | Median Latency |
|---|---|---|---|---|---|---|---|---|
| **Run A** | `gemini-3.5-flash-lite` | `openai_compat` | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` | **11/12 (91.7%)** | **9/12 (75.0%)** | **9/12 (75.0%)** | 0/2 (0.0%)\* | **45808 ms** |
| **Run A2** | `gemini-3.5-flash-lite` | `openai_compat` | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json` | **3/3 (100.0%)** | 0/3 (0.0%)\*\* | **2/3 (66.7%)** | **2/2 (100.0%)** | **75266 ms** |
| **Run C** | `gemini-3.8-flash` | `openai_compat` | `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` | **1/1 (100.0%)** | **1/1 (100.0%)** | **1/1 (100.0%)** | N/A | **66639 ms** |
| **Mock Run** | `mock-planner-v1` | `mock` | `docs/eval/eval_mock_mock_20261014_142213.json` | **11/11 (100.0%)** | **10/11 (90.9%)** | **11/11 (100.0%)** | **1/1 (100.0%)** | **44111 ms** |
| **Planner Bench** | `gemini-3.8-flash` | `openai_compat` | `docs/eval/planner_gemini-3.8-flash_benchmark.json` | **9/10 (90.0%)** | N/A (plan only) | N/A (plan only) | N/A | **17311 ms** |

\* *Note on Run A Repair Rate:* In Run A, `p06` (move_speed = 110 px/s) and `s01` (move_speed = 150 px/s) failed `movement_speed_consistent` because the static 1.6s wall approach did not allow reaching the wall in time. Because `movement_speed_consistent` is non-patchable, repair was skipped. This was diagnosed and resolved in Part 1 by dynamically scaling wall approach time.  
\*\* *Note on Run A2:* Evaluated exclusively on stress prompts `p06`, `s01`, `s02` engineered to fail Playable@1. `s01` and `s02` were successfully repaired to `READY`.

---

## 5. Slow-Player Wall-Reach Dynamic Approach Verification

In Part 1, the wall approach duration in `services/qa_runner.py` was scaled dynamically based on measured player speed:
$$\text{max\_wall\_time} = \max\left(5.0, \frac{800.0}{\text{player\_speed}} + 1.5\right)$$
with coordinate stabilization early-exit.

Verification executed on 2 dedicated test routes (`scripts/verify_slow_player_qa.py`):
1. **Speed 100.0 px/s (`/play/test-slow-100`)**:
   - `movement_speed_consistent`: **PASSED** (straight: 97.4 px/s, diagonal: 98.1 px/s, wall-slide: 96.8 px/s).
   - Overall checks: **17 / 17 PASSED**.
2. **`p06` Initial Spec (`/play/test-p06`, move_speed=110, 15 chasers @ 220, 2 HP)**:
   - `movement_speed_consistent`: **PASSED** (non-patchable check passes).
   - `idle_survival_min_seconds`: **FAILED** (0.9s survival $\le$ 3.0s).
   - `flee_bot_survives`: **FAILED**.
   - Result: All failed checks are patchable $\rightarrow$ `repair_recommended: true` $\rightarrow$ Repair loop successfully triggered!
