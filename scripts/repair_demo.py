#!/usr/bin/env python3
"""
AETHER Bounded Self-Repair Loop Demonstration Script.
Conforms to Phase 4 Acceptance Criteria & Capstone Blueprint Section 5.3.

Demonstrates the automated Playwright QA + bounded parameter-repair loop:
1. In MOCK mode (default):
   - Submits a "repair demo" prompt to the pipeline.
   - The mock provider returns the deliberately unplayable TOO_HARD_SPEC (12 enemies at 240px/s, 1 HP).
   - Initial QA run (Attempt 1) fails spec-level playability checks:
     * idle_survival_min_seconds
     * flee_bot_survives
   - Orchestrator detects failed patchable checks and enters REPAIRING stage.
   - The labeled Mock Repair Responder proposes a minimal parameter patch:
     * reduces enemy speed to <=45% player speed (clamped <=99 px/s)
     * caps enemy count to 6
     * raises player HP to 3
   - Orchestrator applies patch, validates spec, saves game_ir_v2.json, and re-tests (Attempt 2).
   - Attempt 2 QA passes all checks, transitioning the job to READY.
   - Prints the before/after spec diff and QA results for each attempt.

2. In --live mode:
   - Submits at most ONE real-model job ("an extremely brutal survival game with 40 fast enemies and only 1 health").
   - If an upstream 429 is encountered, halts immediately and honestly reports MODEL_HTTP_ERROR without looping.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "aether-backend"
FRONTEND_DIR = REPO_ROOT / "aether-frontend"

_env_py = os.getenv("AETHER_PYTHON")
if _env_py and Path(_env_py).exists():
    VENV_PYTHON = Path(_env_py)
elif (BACKEND_DIR / "venv" / "Scripts" / "python.exe").exists():
    VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = Path(sys.executable)

NODE_PATH = Path(r"C:\Program Files\nodejs\node.exe")
NODE_BIN = str(NODE_PATH) if NODE_PATH.exists() else "node"
VITE_BIN = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"


def is_http_ready(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AETHER-Repair-Demo"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 304)
    except Exception:
        return False


def start_backend(is_live: bool, port: int = 8000) -> subprocess.Popen:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["QA_MODE"] = "real"
    env["MODEL_PROVIDER"] = "openai_compat" if is_live else "mock"

    cmd = [
        str(VENV_PYTHON),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    provider_str = "openai_compat" if is_live else "mock"
    print(f"[repair_demo] Spawning backend (provider={provider_str}, QA_MODE=real) on port {port}...")
    b_log = BACKEND_DIR / "backend_server.log"
    out_f = open(b_log, "w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=out_f,
        stderr=subprocess.STDOUT,
    )
    return proc


def start_frontend(port: int = 5173) -> subprocess.Popen:
    env = os.environ.copy()
    env["VITE_USE_MOCK_API"] = "false"
    env["VITE_API_URL"] = "http://localhost:8000"

    cmd = [NODE_BIN, str(VITE_BIN), "--host", "localhost", "--port", str(port)]
    print(f"[repair_demo] Spawning Vite dev server on port {port}...")
    f_log = FRONTEND_DIR / "frontend_server.log"
    out_f = open(f_log, "w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=out_f,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_services(backend_url: str, frontend_url: str, timeout: float = 30.0) -> bool:
    start_time = time.time()
    backend_ok = False
    frontend_ok = False

    while time.time() - start_time < timeout:
        if not backend_ok:
            try:
                with httpx.Client(timeout=2.0) as client:
                    r = client.get(f"{backend_url}/api/v1/health")
                    if r.status_code == 200:
                        backend_ok = True
            except Exception:
                pass

        if not frontend_ok:
            if is_http_ready(frontend_url):
                frontend_ok = True

        if backend_ok and frontend_ok:
            return True
        time.sleep(0.5)

    return backend_ok and frontend_ok


def stop_process(proc: Optional[subprocess.Popen], name: str):
    if not proc:
        return
    print(f"[repair_demo] Stopping {name} process...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def print_qa_report_summary(attempt_num: int, report: Dict[str, Any]):
    overall = report.get("overall", "UNKNOWN")
    checks = report.get("checks", [])
    passed_count = sum(1 for c in checks if c.get("passed"))
    total_count = len(checks)

    status_str = "[PASS]" if overall == "PASS" else "[FAIL]"
    print(f"\n--- Attempt {attempt_num} QA Results: {status_str} ({passed_count}/{total_count} checks passed) ---")
    print(f"{'Check ID':<30} | {'Critical':<9} | {'Patchable':<10} | {'Result':<8} | {'Details'}")
    print("-" * 90)

    for c in checks:
        cid = c.get("id", "")
        crit = "Yes" if c.get("critical", True) else "No"
        patch = "Yes" if c.get("patchable", False) else "No"
        res = "PASS" if c.get("passed") else "FAIL"
        msg = c.get("message", "")
        measured = c.get("measured")
        if measured:
            surv = measured.get("survived_seconds")
            if surv is not None:
                msg = f"{msg} (survived {surv}s)" if msg else f"survived {surv}s"
        print(f"{cid:<30} | {crit:<9} | {patch:<10} | {res:<8} | {msg}")
    print("-" * 90)


def print_diff_table(diff: Dict[str, Dict[str, Any]]):
    before = diff.get("before", {})
    after = diff.get("after", {})
    all_keys = sorted(set(before.keys()) | set(after.keys()))

    print("\n" + "=" * 80)
    print("                     GAMEIR BEFORE / AFTER SPEC DIFF")
    print("=" * 80)
    print(f"{'Parameter / Field Path':<36} | {'Before Repair':<20} | {'After Repair'}")
    print("-" * 80)
    for k in all_keys:
        b_val = str(before.get(k, "—"))
        a_val = str(after.get(k, "—"))
        print(f"{k:<36} | {b_val:<20} | {a_val}")
    print("=" * 80)


def run_repair_demo(is_live: bool, prompt_override: Optional[str] = None) -> int:
    backend_port = 8000
    frontend_port = 5173
    backend_url = f"http://127.0.0.1:{backend_port}"
    frontend_url = f"http://localhost:{frontend_port}"

    if is_live:
        prompt = prompt_override or "an extremely brutal survival game with 40 fast enemies and only 1 health"
    else:
        prompt = prompt_override or "repair demo: neon gauntlet with fast drones"

    mode_label = "LIVE (Real Model)" if is_live else "MOCK (Deterministic Repair Responder)"
    print("\n" + "=" * 90)
    print(f"       AETHER BOUNDED REPAIR LOOP DEMONSTRATION — MODE: {mode_label}")
    print(f"       Prompt: \"{prompt}\"")
    print("=" * 90)

    backend_proc = None
    frontend_proc = None
    exit_code = 0

    try:
        # Check if already running or spawn
        b_running = is_http_ready(f"{backend_url}/api/v1/health")
        f_running = is_http_ready(frontend_url)

        if not b_running:
            backend_proc = start_backend(is_live=is_live, port=backend_port)
        if not f_running:
            frontend_proc = start_frontend(port=frontend_port)

        print("[repair_demo] Waiting for services to be ready...")
        if not wait_for_services(backend_url, frontend_url, timeout=30.0):
            print("[repair_demo] ERROR: Services failed to start within timeout.")
            return 1

        with httpx.Client(base_url=backend_url, timeout=20.0) as client:
            r_health = client.get("/api/v1/health")
            h_data = r_health.json() if r_health.status_code == 200 else {}
            print(f"[repair_demo] Backend connected: provider={h_data.get('provider')}, model={h_data.get('model')}")

            # 1. Submit prompt
            r_submit = client.post("/api/v1/games", json={"prompt": prompt})
            if r_submit.status_code != 202:
                print(f"[repair_demo] ERROR submitting game: {r_submit.status_code} {r_submit.text}")
                return 1

            game_id = r_submit.json()["game_id"]
            print(f"[repair_demo] Submitted game job: {game_id}")

            max_wait = 300.0
            poll_start = time.time()
            last_stage = ""
            last_status = ""
            terminal_data: Dict[str, Any] = {}
            last_progress_print = 0.0

            while time.time() - poll_start < max_wait:
                try:
                    r_st = client.get(f"/api/v1/games/{game_id}", timeout=10.0)
                    if r_st.status_code == 200:
                        data = r_st.json()
                        status = data.get("status")
                        stage = data.get("stage")
                        attempt = data.get("attempt", 1)

                        if (stage, status) != (last_stage, last_status):
                            elapsed = time.time() - poll_start
                            print(f"  [{elapsed:5.1f}s] Stage: {stage:<16} Status: {status:<16} Attempt: {attempt}")
                            last_stage = stage
                            last_status = status
                            last_progress_print = elapsed

                        if status in ("READY", "READY_WITH_WARNINGS", "FAILED"):
                            terminal_data = data
                            break
                except (httpx.TimeoutException, httpx.NetworkError):
                    # Transient poll timeout/busy wait while Playwright runner is actively asserting
                    pass

                now = time.time() - poll_start
                if now - last_progress_print >= 15.0:
                    print(f"  [{now:5.1f}s] Still in {last_stage} (attempt {last_status})...")
                    last_progress_print = now

                time.sleep(1.0)

            if not terminal_data:
                print("[repair_demo] ERROR: Job timed out waiting for terminal state.")
                return 1

            terminal_status = terminal_data.get("status")
            error_code = terminal_data.get("error_code")
            print(f"\n[repair_demo] Reached terminal state: {terminal_status} (error_code={error_code})")

            # Handle 429 live condition
            if is_live and error_code == "MODEL_HTTP_ERROR":
                print("\n" + "=" * 90)
                print("                     LIVE RUN DIAGNOSTIC: 429 QUOTA EXCEEDED")
                print("=" * 90)
                print(f"Model ID:      {terminal_data.get('model_id') or h_data.get('model')}")
                print(f"Terminal State:{terminal_status}")
                print(f"Error Code:    {error_code}")
                print("Diagnostic:    Upstream model returned HTTP 429 (quota exceeded / rate limit).")
                print("               As required by the specification, halting immediately without retry.")
                print("=" * 90)
                return 0

            # Fetch events
            r_events = client.get(f"/api/v1/games/{game_id}/events")
            raw_ev = r_events.json() if r_events.status_code == 200 else []
            events = raw_ev if isinstance(raw_ev, list) else raw_ev.get("events", [])

            # Locate repair event if present
            repair_events = [e for e in events if e.get("stage") == "REPAIRING" and e.get("result") == "SUCCESS"]

            # Load artifacts from backend filesystem
            artifacts_dir = BACKEND_DIR / "artifacts" / game_id

            qa_report_1_path = artifacts_dir / "qa_report_attempt_1.json"
            qa_report_2_path = artifacts_dir / "qa_report_attempt_2.json"
            spec_v1_path = artifacts_dir / "game_ir_v1.json"
            spec_v2_path = artifacts_dir / "game_ir_v2.json"

            if qa_report_1_path.exists():
                rep1 = json.loads(qa_report_1_path.read_text(encoding="utf-8"))
                print_qa_report_summary(1, rep1)

            if repair_events:
                rep_ev = repair_events[0]
                print("\n" + "=" * 80)
                print("                      REPAIR PROPOSAL DETAILS")
                print("=" * 80)
                print(f"Rationale: {rep_ev.get('rationale')}")
                diff = rep_ev.get("diff", {})
                if diff:
                    print_diff_table(diff)
            elif spec_v1_path.exists() and spec_v2_path.exists():
                from services.repair import compute_spec_diff
                from schemas.game_ir import GameIR
                v1_spec = GameIR.model_validate_json(spec_v1_path.read_text(encoding="utf-8"))
                v2_spec = GameIR.model_validate_json(spec_v2_path.read_text(encoding="utf-8"))
                diff = compute_spec_diff(v1_spec, v2_spec)
                print_diff_table(diff)

            if qa_report_2_path.exists():
                rep2 = json.loads(qa_report_2_path.read_text(encoding="utf-8"))
                print_qa_report_summary(2, rep2)

            # Final summary table
            print("\n" + "=" * 90)
            print("                       REPAIR LOOP EXECUTION SUMMARY")
            print("=" * 90)
            print(f"{'Metric':<35} | {'Value'}")
            print("-" * 90)
            print(f"{'Game ID':<35} | {game_id}")
            print(f"{'Provider / Mode':<35} | {h_data.get('provider')} ({h_data.get('model')})")
            print(f"{'Final Status':<35} | {terminal_status}")
            print(f"{'Total Attempts / Runs':<35} | {terminal_data.get('attempt')}")
            repairs_count = len(repair_events)
            print(f"{'Repairs Executed':<35} | {repairs_count}")
            if repair_events:
                print(f"{'Repair Rationale':<35} | {repair_events[0].get('rationale', '')[:80]}...")
            print(f"{'Total Elapsed Time':<35} | {time.time() - poll_start:.2f}s")
            backend_reqs = None
            try:
                with httpx.Client(timeout=2.0) as client:
                    hr = client.get(f"{backend_url}/api/v1/health")
                    if hr.status_code == 200:
                        backend_reqs = hr.json().get("model_requests")
            except Exception:
                pass
            try:
                from providers.base import get_model_request_count
                process_reqs = get_model_request_count()
            except Exception:
                process_reqs = 0
            if backend_reqs is not None:
                print(f"{'Total Model Requests (backend)':<35} | {backend_reqs}")
            print(f"{'Total Model Requests (process)':<35} | {process_reqs}")
            print("=" * 90)

            if not is_live and terminal_status not in ("READY", "READY_WITH_WARNINGS"):
                exit_code = 1

    finally:
        if backend_proc:
            stop_process(backend_proc, "backend")
        if frontend_proc:
            stop_process(frontend_proc, "frontend")

    return exit_code


def main():
    parser = argparse.ArgumentParser(description="AETHER Bounded Repair Loop Demonstration")
    parser.add_argument("--live", action="store_true", help="Execute single job with real model provider from .env")
    parser.add_argument("--prompt", type=str, default=None, help="Custom prompt override")
    args = parser.parse_args()

    sys.exit(run_repair_demo(is_live=args.live, prompt_override=args.prompt))


if __name__ == "__main__":
    main()
