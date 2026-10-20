#!/usr/bin/env python3
"""
AETHER Planner Benchmark Suite Runner.
Executes the standardized 10-prompt suite against the configured ModelProvider,
records latency, attempts, validation status, theme/objective fidelity, and limitation honesty,
and outputs both structured JSON artifacts and markdown report tables.
"""

import argparse
import datetime
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "services").exists() else SCRIPT_DIR.parent / "aether-backend"
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from dotenv import load_dotenv
    backend_env = BACKEND_DIR / ".env"
    if backend_env.exists():
        load_dotenv(dotenv_path=backend_env)
    else:
        load_dotenv()
except ImportError:
    pass

from providers.base import ModelProvider
from providers.factory import get_provider
from providers.mock import MockModelProvider
from services.planner import plan_game


def find_prompts_file() -> Path:
    candidates = [
        BACKEND_DIR / "bench" / "prompts.json",
        Path.cwd() / "aether-backend" / "bench" / "prompts.json",
        Path.cwd() / "bench" / "prompts.json",
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    raise FileNotFoundError("Could not locate bench/prompts.json in aether-backend/bench/prompts.json")


def run_benchmark(
    provider: Optional[ModelProvider] = None,
    delay_seconds: Optional[float] = None,
    prompts_path: Optional[Path] = None,
    artifacts_dir: Optional[Path] = None,
    prompt_ids: Optional[List[str]] = None,
    update_from_file: Optional[Path] = None,
) -> Dict[str, Any]:
    active_provider = provider if provider is not None else get_provider()
    is_mock = isinstance(active_provider, MockModelProvider)
    provider_name = "mock" if is_mock else getattr(active_provider, "model_name", "openai_compat")

    if delay_seconds is None:
        delay_seconds = float(os.getenv("BENCH_DELAY_SECONDS", "4.0"))

    prompts_file = prompts_path or find_prompts_file()
    with open(prompts_file, "r", encoding="utf-8") as f:
        all_prompts: List[Dict[str, Any]] = json.load(f)

    # Determine prompts to run
    if prompt_ids:
        active_prompts = [p for p in all_prompts if p["id"] in prompt_ids]
    else:
        active_prompts = all_prompts

    # Base records if updating an existing run
    existing_records_map: Dict[str, Dict[str, Any]] = {}
    if update_from_file and Path(update_from_file).exists():
        with open(update_from_file, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            for r in prev_data.get("records", []):
                existing_records_map[r["id"]] = r

    print("=" * 78)
    if is_mock:
        print("     MOCK PROVIDER: not a real model, results are not evidence")
        print("=" * 78)
    print("                      AETHER PLANNER BENCHMARK RUNNER")
    print("=" * 78)
    print(f"Date:          {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Provider:      {'mock' if is_mock else type(active_provider).__name__}")
    print(f"Model ID:      {'mock' if is_mock else getattr(active_provider, 'model_name', 'unknown')}")
    print(f"Total Prompts: {len(active_prompts)} (of {len(all_prompts)} in suite)")
    print(f"Delay Between: {delay_seconds}s")
    print("-" * 78)

    executed_records: Dict[str, Dict[str, Any]] = {}

    for idx, p in enumerate(active_prompts):
        pid = p["id"]
        prompt_text = p["prompt"]
        exp_theme = p.get("expected_theme")
        exp_obj = p.get("expected_objective_type")
        exp_lim = p.get("expect_limitation", False)

        print(f"[{idx+1}/{len(active_prompts)}] Running prompt {pid}: \"{prompt_text[:50]}...\"")

        result = plan_game(prompt_text, provider=active_provider)

        model_responded = bool(getattr(result, "responded", False) or result.raw_response or result.ok)

        if result.ok:
            status = "PASS"
        elif not model_responded:
            status = "NOT_RUN"
        else:
            status = "VALIDATION_FAILED"

        theme_match = None
        if exp_theme is not None:
            theme_match = bool(result.ok and result.spec and result.spec.theme == exp_theme)

        obj_match = None
        if exp_obj is not None:
            obj_match = bool(result.ok and result.spec and result.spec.objective.type == exp_obj)

        lim_honest = None
        if exp_lim:
            lim_honest = result.ok and len(result.limitations) > 0

        record = {
            "id": pid,
            "prompt": prompt_text,
            "provider": "mock" if is_mock else getattr(active_provider, "model_name", type(active_provider).__name__),
            "status": status,
            "ok": result.ok,
            "attempts": result.attempts,
            "first_attempt_valid": result.first_response_validated,
            "model_responded": model_responded,
            "error_code": result.error_code,
            "latency_ms": result.latency_ms if model_responded else 0,
            "model": "mock" if is_mock else result.model,
            "limitations": result.limitations,
            "expected_theme": exp_theme,
            "theme_match": theme_match,
            "expected_objective_type": exp_obj,
            "objective_match": obj_match,
            "expect_limitation": exp_lim,
            "limitation_honest": lim_honest,
            "raw_response": result.raw_response,
            "errors": result.errors,
            "spec": result.spec.model_dump() if result.spec else None,
            "notes": p.get("notes", ""),
        }
        executed_records[pid] = record

        lat_display = f"{result.latency_ms}ms" if model_responded else "N/A (no response)"
        print(f"   -> Status: {status} | OK: {result.ok} | Attempts: {result.attempts} | 1st Valid: {result.first_response_validated} | Latency: {lat_display}")

        if idx < len(active_prompts) - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)

    # Merge records if updating an existing run
    if existing_records_map:
        records: List[Dict[str, Any]] = []
        for p in all_prompts:
            pid = p["id"]
            if pid in executed_records:
                records.append(executed_records[pid])
            elif pid in existing_records_map:
                prev_rec = dict(existing_records_map[pid])
                if "model_responded" not in prev_rec:
                    prev_rec["model_responded"] = bool(
                        prev_rec.get("ok")
                        or (prev_rec.get("latency_ms", 0) > 0 and prev_rec.get("error_code") not in ("MODEL_HTTP_ERROR", "MODEL_TIMEOUT", "PROMPT_INVALID"))
                    )
                if "status" not in prev_rec:
                    if prev_rec.get("ok"):
                        prev_rec["status"] = "PASS"
                    elif not prev_rec["model_responded"]:
                        prev_rec["status"] = "NOT_RUN"
                    else:
                        prev_rec["status"] = "VALIDATION_FAILED"
                records.append(prev_rec)
    else:
        records = [executed_records[p["id"]] for p in active_prompts]

    # Compute aggregate metrics
    total = len(records)
    responded_records = [r for r in records if r.get("model_responded", False)]
    responded_count = len(responded_records)
    not_run_records = [r for r in records if r.get("status") == "NOT_RUN"]
    not_run_count = len(not_run_records)
    val_failed_records = [r for r in records if r.get("status") == "VALIDATION_FAILED"]
    val_failed_count = len(val_failed_records)
    passed_records = [r for r in records if r.get("ok", False)]
    passed_count = len(passed_records)

    first_valid_count = sum(1 for r in responded_records if r.get("first_attempt_valid", False))
    first_response_val_rate = (first_valid_count / responded_count) if responded_count else 0.0
    first_response_val_denom = f"{first_valid_count}/{responded_count}"

    final_success_rate = (passed_count / responded_count) if responded_count else 0.0
    final_success_denom = f"{passed_count}/{responded_count}"

    # Theme evaluation
    theme_evaluated = [r for r in records if r.get("expected_theme") is not None]
    theme_matched = [r for r in theme_evaluated if r.get("theme_match")]
    theme_match_rate = (len(theme_matched) / len(theme_evaluated)) if theme_evaluated else 1.0
    theme_denom = f"{len(theme_matched)}/{len(theme_evaluated)}"
    theme_skipped = [r["id"] for r in records if r.get("expected_theme") is None]

    # Objective evaluation
    obj_evaluated = [r for r in records if r.get("expected_objective_type") is not None]
    obj_matched = [r for r in obj_evaluated if r.get("objective_match")]
    obj_match_rate = (len(obj_matched) / len(obj_evaluated)) if obj_evaluated else 1.0
    obj_denom = f"{len(obj_matched)}/{len(obj_evaluated)}"
    obj_skipped = [r["id"] for r in records if r.get("expected_objective_type") is None]

    # Combined theme & objective
    combined_eval = [r for r in records if r.get("expected_theme") is not None or r.get("expected_objective_type") is not None]
    combined_matched = [
        r for r in combined_eval
        if (r.get("theme_match") is None or r.get("theme_match")) and (r.get("objective_match") is None or r.get("objective_match"))
    ]
    theme_obj_match_rate = (len(combined_matched) / len(combined_eval)) if combined_eval else 1.0
    theme_obj_denom = f"{len(combined_matched)}/{len(combined_eval)}"
    theme_obj_skipped = [
        r["id"] for r in records
        if r.get("expected_theme") is None and r.get("expected_objective_type") is None
    ]

    # Limitation honesty
    lim_prompts = [r for r in records if r.get("expect_limitation")]
    lim_honest_count = sum(1 for r in lim_prompts if r.get("limitation_honest"))
    limitation_honesty_rate = (lim_honest_count / len(lim_prompts)) if lim_prompts else 1.0
    lim_denom = f"{lim_honest_count}/{len(lim_prompts)}"
    lim_skipped = [r["id"] for r in records if not r.get("expect_limitation")]

    # Latency: Compute median and max ONLY over calls that returned a model response
    # Exclude failed calls (error before response)
    valid_latencies = [
        r["latency_ms"]
        for r in records
        if r.get("model_responded", False) and r.get("latency_ms") is not None and r["latency_ms"] > 0
    ]
    median_latency = statistics.median(valid_latencies) if valid_latencies else 0.0
    max_latency = max(valid_latencies) if valid_latencies else 0
    latency_evaluated_count = len(valid_latencies)
    latency_excluded_count = total - latency_evaluated_count

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    model_id = "mock" if is_mock else getattr(active_provider, "model_name", "unknown")

    summary = {
        "benchmark_date": date_str,
        "provider": "mock" if is_mock else type(active_provider).__name__,
        "model_id": model_id,
        "total_prompts": total,
        "responded_prompts": responded_count,
        "not_run_prompts": not_run_count,
        "validation_failed_prompts": val_failed_count,
        "passed_prompts": passed_count,
        "first_response_validation_rate": round(first_response_val_rate * 100, 1),
        "first_response_validation_denominator": first_response_val_denom,
        "final_success_rate": round(final_success_rate * 100, 1),
        "final_success_denominator": final_success_denom,
        "theme_match_rate": round(theme_match_rate * 100, 1),
        "theme_match_denominator": theme_denom,
        "theme_skipped_prompts": theme_skipped,
        "objective_match_rate": round(obj_match_rate * 100, 1),
        "objective_match_denominator": obj_denom,
        "objective_skipped_prompts": obj_skipped,
        "theme_objective_match_rate": round(theme_obj_match_rate * 100, 1),
        "theme_objective_match_denominator": theme_obj_denom,
        "theme_objective_skipped_prompts": theme_obj_skipped,
        "limitation_honesty_rate": round(limitation_honesty_rate * 100, 1),
        "limitation_honesty_denominator": lim_denom,
        "limitation_skipped_prompts": lim_skipped,
        "latency_evaluated_count": latency_evaluated_count,
        "latency_excluded_count": latency_excluded_count,
        "median_latency_ms": round(median_latency, 1),
        "max_latency_ms": max_latency,
    }

    out_dir = artifacts_dir or (BACKEND_DIR / "artifacts" / "bench")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"planner_{provider_name}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2)

    # Generate Markdown Table
    md_path = out_dir / f"planner_{provider_name}_{timestamp}.md"
    md_content = generate_markdown_report(summary, records, is_mock)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 78)
    print("                         BENCHMARK SUMMARY RESULTS")
    print("=" * 78)
    if is_mock:
        print("MOCK PROVIDER: not a real model, results are not evidence")
        print("-" * 78)
    print(f"Model ID:                        {model_id}")
    print(f"Date:                            {date_str}")
    print(f"Total Prompts:                   {total} (Responded: {responded_count}, Not Run: {not_run_count}, Val Failed: {val_failed_count})")
    print(f"First-Response Validation Rate:  {summary['first_response_validation_rate']}% ({summary['first_response_validation_denominator']})")
    print(f"Final Success Rate:              {summary['final_success_rate']}% ({summary['final_success_denominator']})")
    print(f"Theme Match Rate:                {summary['theme_match_rate']}% ({summary['theme_match_denominator']})")
    print(f"  -> Skipped prompts:            {', '.join(theme_skipped)} (expected_theme is null)")
    print(f"Objective Match Rate:            {summary['objective_match_rate']}% ({summary['objective_match_denominator']})")
    print(f"  -> Skipped prompts:            {', '.join(obj_skipped)} (expected_objective_type is null)")
    print(f"Theme/Objective Match Rate:      {summary['theme_objective_match_rate']}% ({summary['theme_objective_match_denominator']})")
    print(f"  -> Skipped prompts:            {', '.join(theme_obj_skipped)} (expected theme and objective are null)")
    print(f"Limitation Honesty Rate:         {summary['limitation_honesty_rate']}% ({summary['limitation_honesty_denominator']})")
    print(f"  -> Skipped prompts:            {', '.join(lim_skipped)} (expect_limitation is false)")
    print(f"Median Latency:                  {summary['median_latency_ms']} ms (over {latency_evaluated_count} responded calls; {latency_excluded_count} excluded)")
    print(f"Artifact JSON:                   {json_path}")
    print(f"Artifact Markdown:               {md_path}")
    from providers.base import get_model_request_count
    print(f"Total Model Requests (process):  {get_model_request_count()}")
    print("=" * 78 + "\n")

    return {
        "summary": summary,
        "records": records,
        "json_path": str(json_path),
        "md_path": str(md_path),
    }


def generate_markdown_report(summary: Dict[str, Any], records: List[Dict[str, Any]], is_mock: bool) -> str:
    lines = []
    lines.append(f"# AETHER Game Planner Benchmark Report")
    lines.append(f"**Model ID:** `{summary['model_id']}`  ")
    lines.append(f"**Date:** `{summary['benchmark_date']}`  ")
    lines.append(f"**Provider:** `{'mock' if is_mock else summary['provider']}`  \n")

    if is_mock:
        lines.append("> ⚠️ **MOCK PROVIDER: not a real model, results are not evidence**\n")

    lines.append("## Summary Metrics\n")
    lines.append("| Metric | Rate | Ratio | Details |")
    lines.append("|---|---|---|---|")
    lines.append(f"| **First-Response Validation Rate** | **{summary['first_response_validation_rate']}%** | **{summary['first_response_validation_denominator']}** | Responded calls that passed schema validation on attempt 1 |")
    lines.append(f"| **Final Success Rate** | **{summary['final_success_rate']}%** | **{summary['final_success_denominator']}** | Responded calls that produced valid GameIR within max attempts |")
    lines.append(f"| **Theme Match Rate** | **{summary['theme_match_rate']}%** | **{summary['theme_match_denominator']}** | Skipped: {', '.join(f'`{p}`' for p in summary['theme_skipped_prompts'])} (`expected_theme` is null) |")
    lines.append(f"| **Objective Match Rate** | **{summary['objective_match_rate']}%** | **{summary['objective_match_denominator']}** | Skipped: {', '.join(f'`{p}`' for p in summary['objective_skipped_prompts'])} (`expected_objective_type` is null) |")
    lines.append(f"| **Theme & Objective Match Rate** | **{summary['theme_objective_match_rate']}%** | **{summary['theme_objective_match_denominator']}** | Skipped: {', '.join(f'`{p}`' for p in summary['theme_objective_skipped_prompts'])} (both expected values null) |")
    lines.append(f"| **Limitation Honesty Rate** | **{summary['limitation_honesty_rate']}%** | **{summary['limitation_honesty_denominator']}** | Skipped: {', '.join(f'`{p}`' for p in summary['limitation_skipped_prompts'])} (`expect_limitation` is false) |")
    lines.append(f"| **Median Latency** | **{summary['median_latency_ms']} ms** | **{summary['latency_evaluated_count']} calls** | Typical completion latency ({summary['latency_excluded_count']} excluded: error before response) |")
    lines.append(f"| **Max Latency** | **{summary['max_latency_ms']} ms** | **{summary['latency_evaluated_count']} calls** | Peak completion latency ({summary['latency_excluded_count']} excluded: error before response) |")
    lines.append("\n## Detailed Prompt Results\n")
    lines.append("| ID | Prompt | Status | 1st Valid | Attempts | Latency (ms) | Limitations Disclosed | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|")

    for r in records:
        f_val = "✅ Yes" if r.get("first_attempt_valid") else "❌ No"
        if r.get("ok"):
            status_badge = "✅ Pass"
        elif r.get("status") == "NOT_RUN" or not r.get("model_responded"):
            status_badge = f"⚠️ Not Run ({r.get('error_code') or 'NO_RESPONSE'})"
        else:
            status_badge = f"❌ Validation Failed ({r.get('error_code') or 'INVALID_SPEC'})"

        lim_str = f"✅ ({len(r.get('limitations', []))})" if len(r.get("limitations", [])) > 0 else ("⚠️ None" if r.get("expect_limitation") else "—")
        lat_str = f"{r['latency_ms']}" if r.get("model_responded") and r.get("latency_ms") else "— (excluded)"
        prompt_esc = r["prompt"].replace("|", "\\|")
        lines.append(f"| `{r['id']}` | {prompt_esc} | {status_badge} | {f_val} | {r['attempts']} | {lat_str} | {lim_str} | {r['notes']} |")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AETHER Planner Benchmark")
    parser.add_argument("--prompt-id", "-p", help="Run only specific prompt ID, e.g. p10")
    parser.add_argument("--delay", "-d", type=float, help="Delay between prompts in seconds")
    parser.add_argument("--update-from", "-u", type=str, help="Update an existing benchmark JSON file")
    args = parser.parse_args()

    pids = [args.prompt_id] if args.prompt_id else None
    update_file = Path(args.update_from) if args.update_from else None
    run_benchmark(delay_seconds=args.delay, prompt_ids=pids, update_from_file=update_file)
