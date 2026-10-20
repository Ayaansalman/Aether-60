#!/usr/bin/env python3
"""
AETHER Evaluation Results Aggregator (Phase 6 / Blueprint Section 15.2).
Reads ALL eval_*.json artifacts in docs/eval/ and generates an aggregated,
chronologically organized docs/EVAL_RESULTS.md document.
Allows running additional models in the future without an AI agent.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_EVAL_DIR = ROOT_DIR / "docs" / "eval"
DOCS_FILE = ROOT_DIR / "docs" / "EVAL_RESULTS.md"


def load_eval_artifacts() -> List[Dict[str, Any]]:
    artifacts = []
    if not DOCS_EVAL_DIR.exists():
        return artifacts

    for json_file in sorted(DOCS_EVAL_DIR.glob("eval_*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_filename"] = json_file.name
            artifacts.append(data)
        except Exception as e:
            print(f"[WARN] Failed to load {json_file.name}: {e}")

    # Sort descending by date (most recent first)
    artifacts.sort(key=lambda x: x.get("benchmark_date", ""), reverse=True)
    return artifacts


def generate_markdown(artifacts: List[Dict[str, Any]]) -> str:
    lines = [
        "# AETHER Pipeline Evaluation Results",
        "",
        "This document records empirical evaluation results of the AETHER Game Synthesis and Self-Repair pipeline across models and runs.",
        "",
        "---",
        "",
        "## Multi-Model Evaluation Comparison",
        "",
        "| Run | Model | Provider | Date (UTC) | Status | Playable@1 | Playable@3 | Repair Rate | Median Latency | Requests |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for a in artifacts:
        label = a.get("run_label") or a.get("model", "Unknown")
        # Shorten label for comparison table
        short_label = label.split(":")[0] if ":" in label else label[:24]
        model = a.get("model", "unknown")
        provider = a.get("provider", "unknown")
        date_str = a.get("benchmark_date", "").replace(" UTC", "")
        status = a.get("run_status", "unknown")
        p1 = a.get("playable_at_1_rate", "N/A")
        p3 = a.get("playable_at_3_rate", "N/A")
        rep = a.get("repair_success_rate", "N/A")
        med = f"{a.get('median_latency_ms', 0):.0f}ms" if a.get("median_latency_ms") else "N/A"
        reqs = str(a.get("total_model_requests", "—"))

        lines.append(
            f"| `{short_label}` | `{model}` | `{provider}` | {date_str} | `{status}` | {p1} | {p3} | {rep} | {med} | {reqs} |"
        )

    lines.extend(["", "---", ""])

    for a in artifacts:
        title = a.get("run_label") or f"Evaluation Run: {a.get('model')} ({a.get('benchmark_date')})"
        is_mock = a.get("is_mock", False)
        filename = a.get("_filename", "")

        banner = ""
        if is_mock:
            banner = "> **MOCK PROVIDER: not a real model, results are not evidence**  \n"

        lines.extend([
            f"## {title}",
            "",
            banner,
            f"> **Date:** {a.get('benchmark_date', 'N/A')}  ",
            f"> **Provider:** `{a.get('provider', 'N/A')}`  ",
            f"> **Model:** `{a.get('model', 'N/A')}`  ",
            f"> **Fallback Status:** disabled (`MODEL_FALLBACKS=\"\"`, `AETHER_ALLOW_FALLBACK=0`)  ",
            f"> **QA Mode:** `{a.get('qa_mode', 'N/A')}`  ",
            f"> **Artifacts:** `docs/eval/{filename}`  ",
            f"> **Total Model Requests:** {a.get('total_model_requests', 'N/A')}",
            "",
            "### Summary Metrics",
            "",
            "| Evaluation Metric | Rate / Value | Note |",
            "|---|---|---|",
            f"| **First-Response Validation Rate** | **{a.get('spec_validated_first_rate', 'N/A')}** | Evaluated over prompts with model response |",
            f"| **Playable @ Attempt 1** | **{a.get('playable_at_1_rate', 'N/A')}** | Initial build passed all critical QA |",
            f"| **Playable @ Attempt 3** | **{a.get('playable_at_3_rate', 'N/A')}** | Pass after up to 2 repair iterations |",
            f"| **Repair Success Rate** | **{a.get('repair_success_rate', 'N/A')}** | Successful repairs over repair attempts |",
            f"| **Theme Fidelity** | **{a.get('theme_match_rate', 'N/A')}** | Faithful to target prompt theme |",
            f"| **Objective Fidelity** | **{a.get('objective_match_rate', 'N/A')}** | Faithful to target objective criteria |",
            f"| **Limitation Honesty** | **{a.get('limitation_honesty_rate', 'N/A')}** | Prompts with expect_limitation=True |",
            f"| **Non-Limitation Disclosed** | **{a.get('non_limit_disclosed_count', 0)} prompt(s)** | Disclosed limitations on standard prompts |",
            f"| **Median Latency** | **{a.get('median_latency_ms', 0):.1f} ms** | Model response prompts only |",
            "",
            "### Per-Prompt Results",
            "",
            "| ID | Prompt | Status | 1st Valid | Playable@1 | Playable@3 | Repair | Att | Latency | Category |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ])

        for r in a.get("records", []):
            v1 = "✅" if r.get("spec_validated_first_response") else ("❌" if r.get("spec_validated_first_response") is False else "—")
            p1 = "✅" if r.get("playable_at_1") else ("❌" if r.get("playable_at_1") is False else "—")
            p3 = "✅" if r.get("playable_at_3") else ("❌" if r.get("playable_at_3") is False else "—")
            rep = "Succ" if r.get("repair_succeeded") else ("Att" if r.get("repair_attempted") else "No")
            att = str(r.get("attempts", "1"))
            cat = r.get("failure_category") or "none"
            lat = f"{r.get('total_latency_ms', 0):.0f} ms" if r.get("total_latency_ms") is not None else "—"
            clean_p = r.get("prompt", "").replace("|", "\\/")
            lines.append(f"| `{r.get('id')}` | {clean_p} | `{r.get('final_status')}` | {v1} | {p1} | {p3} | {rep} | {att} | {lat} | `{cat}` |")

        lines.extend(["", "---", ""])

    # Comparative Analysis Section: Run C (gemini-3.8-flash) vs Run A (gemini-3.5-flash-lite)
    lines.extend([
        "## Comparative Analysis: Run C (gemini-3.8-flash) vs Run A (gemini-3.5-flash-lite)",
        "",
        "Empirical head-to-head comparison between Run A (`gemini-3.5-flash-lite`, 12 prompts complete) and Run C (`gemini-3.8-flash`, standalone real-model evaluation with fallback disabled).",
        "",
        "| Evaluation Dimension | Run A: `gemini-3.5-flash-lite` | Run C Rerun (2026-10-15): `gemini-3.8-flash` | Run C Attempt 1 (2026-10-14): `gemini-3.8-flash` | Primary Artifact Citation |",
        "|---|---|---|---|---|",
        "| **Artifact File** | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` | `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json` | `docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` | JSON benchmark artifacts |",
        "| **Execution Date** | `2026-10-14 11:55:28 UTC` | `2026-10-15 17:22:36 UTC` | `2026-10-14 12:05:23 UTC` | UTC timestamp |",
        "| **Provider / Fallback** | `openai_compat` / Disabled | `openai_compat` / Disabled | `openai_compat` / Disabled | Fallback strictly disabled |",
        "| **Prompts Attempted** | 12 / 12 | 12 / 12 | 2 / 12 | Canonical prompt benchmark |",
        "| **Prompts Completed** | **12 / 12 (100.0%)** | **0 / 12 (0.0%)** | **1 / 12 (8.3%)** | Completed model responses |",
        "| **Run Status** | `complete` | `incomplete` (preflight timeout) | `incomplete` (p02 timeout) | Upstream provider status |",
        "| **First-Response Validation Rate** | **11/12 (91.7%)** | **0/0 (0.0%)** | **1/1 (100.0%)** | `spec_validated_first_rate` |",
        "| **Playable @ Attempt 1** | **9/12 (75.0%)** | **0/0 (0.0%)** | **1/1 (100.0%)** | `playable_at_1_rate` |",
        "| **Playable @ Attempt 3** | **9/12 (75.0%)** | **0/0 (0.0%)** | **1/1 (100.0%)** | `playable_at_3_rate` |",
        "| **Repair Success Rate** | **0/2 (0.0%)** | **N/A (0/0)** | **N/A (0/0)** | `repair_success_rate` |",
        "| **Failures by Category** | 2 `interaction` (`p06`, `s01`), 1 `schema` (`s02`) | 12 `provider_error` (preflight timeout) | 1 `timeout` (`p02`), 10 `not_run` | `failure_category` taxonomy |",
        "| **Median Latency** | **45,807.6 ms** | **0.0 ms** | **66,639.2 ms** | `median_latency_ms` |",
        "",
        "### Key Empirical Findings & Plain Comparison",
        "",
        "1. **Completion & Endpoint Reliability**:",
        "   - **Run A (`gemini-3.5-flash-lite`)** successfully completed all 12 benchmark prompts without dropping requests (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`).",
        "   - **Run C (`gemini-3.8-flash`)** timed out in both attempts when fallback was disabled:",
        "     - In the 2026-10-15 rerun (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`), the upstream health ping timed out after 60.0s, resulting in 0 prompts completed and all 12 categorized as `provider_error`. Cause not established.",
        "     - In the 2026-10-14 attempt (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json`), prompt `p01` reached `READY` in 66.6s, but prompt `p02` timed out after 121.9s, halting the run. Cause not established.",
        "",
        "2. **Latency Comparison**:",
        "   - `gemini-3.5-flash-lite` demonstrated manageable latency for top-down synthesis: median end-to-end latency was 45,807.6 ms in Run A (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`; min: 3,762.6 ms, max: 68,085.9 ms) and 47,020.5 ms in Run D (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), whereas planner-only median in Phase 0 bench with gemini-3.8-flash was 17.3s (`docs/eval/planner_gemini-3.8-flash_benchmark.json`).",
        "   - `gemini-3.8-flash` timed out in both Run C attempts (`docs/eval/eval_openai_compat_gemini-3.8-flash_20261014_120523.json` and `docs/eval/eval_openai_compat_gemini-3.8-flash_20261015_172236.json`), cause not established.",
        "",
        "3. **Playability & Synthesis Quality**:",
        "   - On the single prompt that `gemini-3.8-flash` completed (`p01`), it achieved 100% first-response validation and 100% Playable@1 with all 17 automated browser QA checks passing.",
        "   - **Caution on Interpretation**: We do **not** claim `gemini-3.8-flash` is superior or an improvement over `gemini-3.5-flash-lite`. The sample size of successful completions for `gemini-3.8-flash` is essentially negligible ($N=1$ on Oct 14, $N=0$ on Oct 15). Due to upstream timeouts, `gemini-3.5-flash-lite` remains the far more reliable production model for AETHER.",
        "",
        "---",
        "",
        "## Comparative Analysis: Run A, Run A2, and Run D (Gemini 3.5 Flash Lite across Milestones)",
        "",
        "Comparative evaluation of the primary production model (`gemini-3.5-flash-lite`) across the baseline engine (Run A), repair-prompt tuning on dev cases (Run A2), and the upgraded GameIR mechanic variety engine (Run D).",
        "",
        "| Metric / Dimension | Run A: Baseline Engine | Run A2: Repair Prompt Tuning | Run D: Upgraded Variety Engine | Primary Artifact Citations |",
        "|---|---|---|---|---|",
        "| **Artifact File** | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json` | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json` | `docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json` | Exact JSON evaluation artifacts |",
        "| **Execution Date** | 2026-10-14 11:55:28 UTC | 2026-10-14 13:47:51 UTC | 2026-10-16 09:17:54 UTC | Benchmark execution timestamp |",
        "| **Engine Scope** | Baseline (chaser-only, open layout, basic repair prompt) | Baseline engine + tuned repair prompt (explicit bounds) | Upgraded engine (5 enemy AI, 4 layouts, defeat_enemies, visual overrides, dynamic QA approach timing) | Architectural engine version |",
        "| **Prompts Attempted** | 12 / 12 | 3 / 3 (dev stress prompts only) | 12 / 12 | Prompt suite scope |",
        "| **Prompts Completed** | **12 / 12 (100.0%)** | **3 / 3 (100.0%)** | **12 / 12 (100.0%)** | Model responses received |",
        "| **Run Status** | `complete` | `complete` | `complete` | Benchmark completion status |",
        "| **First-Response Validation Rate** | **11/12 (91.7%)** (`s02` failed schema) | **3/3 (100.0%)** | **12/12 (100.0%)** (12/12 first-valid) | `spec_validated_first_rate` |",
        "| **Playable @ Attempt 1** | **9/12 (75.0%)** | **0/3 (0.0%)** (stress prompts only) | **9/12 (75.0%)** | `playable_at_1_rate` |",
        "| **Playable @ Attempt 3** | **9/12 (75.0%)** | **2/3 (66.7%)** | **12/12 (100.0%)** | `playable_at_3_rate` |",
        "| **Repair Attempts / Successes** | **0/2 (0.0%)** (p06, s01 failed repair; s02 skipped due to schema) | **2/2 (100.0%)** (s01, s02 repaired; p06 not repaired) | **3/3 (100.0%)** (p06, s01, s02 all repaired to READY) | `repair_success_rate` |",
        "| **Initial Failures (Attempt 1)** | 2 `interaction` (`p06`, `s01`), 1 `schema` (`s02`) | 3 `interaction` (`p06`, `s01`, `s02`) | 3 `interaction` (`p06`, `s01`, `s02`) | Attempt 1 failure taxonomy |",
        "| **Final Unresolved Failures** | 2 `interaction` (`p06`, `s01`), 1 `schema` (`s02`) | 1 `interaction` (`p06`) | **0** (all 12 reached `READY`) | Final failure taxonomy |",
        "| **Median Latency** | **45,807.6 ms** | **75,266.5 ms** (all repairs) | **47,020.5 ms** | `median_latency_ms` |",
        "| **Total Model Requests** | 14 | 7 | 18 | `total_model_requests` |",
        "",
        "### Plain-Language Comparison & Engineering Differences",
        "",
        "1. **Engine, QA Runner, and Repair Differences**:",
        "   - The engine, QA runner, and repair prompt differ from Run A, so the comparison between Run A and Run D is not single-variable.",
        "   - In Phase 9, `GameIR v1.0` was expanded to support 5 enemy AI types (`chaser`, `bouncer`, `patroller`, `dasher`, `shooter`), 4 arena layouts (`open`, `pillars`, `lanes`, `maze`), the `defeat_enemies` objective, and visual shape/HUD overrides.",
        "   - The repair prompt was updated in Phase 5.7 to include measured vs. required thresholds and valid enum bounds, and the QA runner in Phase 8 was updated with dynamic approach timing in Check 6.",
        "   - Run D prompts are the same 12 prompts as Run A and do not measure the new enemy types and layouts.",
        "",
        "2. **Repair Performance & Development-Set Context**:",
        "   - In **Run A** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`), 0 of 2 repairs succeeded (0.0%). `p06` and `s01` failed QA on Attempt 1 and failed repair; `s02` failed Pydantic validation on Attempt 1 and did not enter repair.",
        "   - In **Run A2** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_134751.json`), evaluating 3 dev stress prompts, 2 of 2 repair attempts succeeded (`s01` and `s02`), while `p06` was not repaired.",
        "   - In **Run D** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), 3 of 3 repair attempts succeeded (100.0%): `p06`, `s01`, and `s02` all failed on Attempt 1 and transitioned to `READY` on Attempt 2.",
        "   - `p06`, `s01`, and `s02` failed first in Runs A, A2, and D and were also the cases used to tune the QA check and repair prompt, so Run D is a development-set result, not a held-out estimate.",
        "",
        "3. **Playable@1 vs Playable@3**:",
        "   - Playable@1 equals Run A (9/12, 75.0%). In both Run A and Run D, the same 9 standard prompts (`p01`–`p05`, `p07`–`p10`) passed on Attempt 1.",
        "   - Playable@3 reached 12/12 (100.0%) in Run D with 3/3 repairs completing, compared to 9/12 (75.0%) in Run A where 0/2 repairs succeeded.",
        "",
        "4. **Latency Profile**:",
        "   - Median latency in Run D was **47,020.5 ms** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261016_091754.json`), compared to Run A's **45,807.6 ms** (`docs/eval/eval_openai_compat_gemini-3.5-flash-lite_20261014_115528.json`). Total model requests were 18 in Run D compared to 14 in Run A.",
        "",
        "5. **Sample Size & Variation Caveats**:",
        "   - One run per prompt; results can vary between runs.",
        "   - All runs evaluate a curated 12-prompt benchmark (or 3 prompts in Run A2). This sample size is too small to serve as an unbiased general benchmark.",
        "",
        "---",
        "",
        "## How to Re-Run with Another Model / Provider",
        "",
        "To evaluate against any model without an AI agent, use `scripts/run_real_eval.ps1`:",
        "",
        "```powershell",
        "# Run with Gemini 3.5 Flash Lite (default, 12 prompts, real browser QA)",
        ".\\scripts\\run_real_eval.ps1 -ModelId \"gemini-3.5-flash-lite\" -Delay 5.0 -MaxRequests 60",
        "",
        "# Run with Gemini 3.8 Flash (larger budget & pacing delay)",
        ".\\scripts\\run_real_eval.ps1 -ModelId \"gemini-3.8-flash\" -Delay 13.0 -MaxRequests 60",
        "",
        "# Safe dry-run test with Mock Provider (zero real API calls)",
        ".\\scripts\\run_real_eval.ps1 -Mock",
        "```",
        "",
        "The script will:",
        "1. Configure process environment variables (disabling fallback and setting the target model ID).",
        "2. Automatically start the Vite server for headless Playwright QA.",
        "3. Execute the full benchmark suite (`run_eval.py`).",
        "4. Stop the Vite server cleanly.",
        "5. Copy artifacts to `docs/eval/` and regenerate `docs/EVAL_RESULTS.md` from all historical runs.",
        "",
    ])

    return "\n".join(lines)


def aggregate():
    artifacts = load_eval_artifacts()
    print(f"[aggregate_eval_results] Found {len(artifacts)} evaluation artifact(s) in {DOCS_EVAL_DIR}")
    content = generate_markdown(artifacts)
    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[aggregate_eval_results] Successfully regenerated {DOCS_FILE}")


if __name__ == "__main__":
    aggregate()
