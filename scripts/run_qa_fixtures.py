#!/usr/bin/env python3
"""
AETHER Known-Broken Fixtures QA Test Runner.
Conforms to Section 7.4 of the Capstone Engineering Blueprint.

Executes Playwright QA checks against intentional fault fixtures:
1. ?bug=restart_keeps_hp -> Expects QA FAIL (failing: restart_resets_after_lose / restart_resets_after_win)
2. ?bug=no_win           -> Expects QA FAIL (failing: win_reachable)

Exits 0 ONLY if every fixture is positively detected with actionable error messages.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

# Resolve directory paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "aether-backend").exists() else SCRIPT_DIR.parent.parent
BACKEND_DIR = PROJECT_ROOT / "aether-backend"
FRONTEND_DIR = PROJECT_ROOT / "aether-frontend"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts" / "qa"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from services.qa_runner import run_qa
except ImportError as err:
    print(f"Error importing run_qa: {err}")
    sys.exit(1)


class FixtureDef(TypedDict):
    name: str
    url: str
    expected_check_ids: List[str]
    description: str


FIXTURES: List[FixtureDef] = [
    {
        "name": "restart_keeps_hp",
        "url": "http://localhost:5173/play/demo?bug=restart_keeps_hp",
        "expected_check_ids": ["restart_resets_after_lose", "restart_resets_after_win"],
        "description": "Restart does not restore player HP to max_health"
    },
    {
        "name": "no_win",
        "url": "http://localhost:5173/play/demo?bug=no_win",
        "expected_check_ids": ["win_reachable"],
        "description": "Win condition never triggers upon fulfilling objective"
    },
    {
        "name": "demo-too-hard",
        "url": "http://localhost:5173/play/demo-too-hard",
        "expected_check_ids": ["idle_survival_min_seconds", "flee_bot_survives"],
        "description": "Deliberately unplayable spec (12 fast enemies, 1 HP) fails spec-level QA checks"
    },
]


def is_server_listening(host: str = "localhost", port: int = 5173, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def ensure_dev_server():
    if is_server_listening("localhost", 5173):
        return None

    print("[fixtures_runner] Starting Vite dev server in background...")
    import os
    env = os.environ.copy()
    nodejs_dir = r"C:\Program Files\nodejs"
    if nodejs_dir not in env.get("PATH", ""):
        env["PATH"] = f"{nodejs_dir};" + env.get("PATH", "")

    node_bin = Path(r"C:\Program Files\nodejs\node.exe")
    vite_bin = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    if node_bin.exists() and vite_bin.exists():
        cmd = [str(node_bin), str(vite_bin), "--host", "localhost", "--port", "5173"]
    else:
        npm_cmd = str(Path(r"C:\Program Files\nodejs\npm.cmd")) if Path(r"C:\Program Files\nodejs\npm.cmd").exists() else ("npm.cmd" if sys.platform == "win32" else "npm")
        cmd = [npm_cmd, "run", "dev"]

    proc = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    start_time = time.time()
    while time.time() - start_time < 25.0:
        if is_server_listening("localhost", 5173):
            print(f"[fixtures_runner] Dev server ready in {time.time() - start_time:.1f}s")
            return proc
        time.sleep(0.5)
    raise RuntimeError("Dev server failed to start on port 5173")


def main():
    print("=" * 96)
    print("           AETHER BLUEPRINT 7.4: KNOWN-BROKEN FIXTURES VALIDATION SUITE")
    print("=" * 96)

    ensure_dev_server()
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    all_fixtures_detected = True

    for fix in FIXTURES:
        name = fix["name"]
        url = fix["url"]
        expected_ids = fix["expected_check_ids"]

        print(f"\n[Running Fixture] -> {name} ({url}) ...")
        start = time.time()
        report = run_qa(url, str(ARTIFACTS_DIR))
        duration = time.time() - start

        # Fixture detection evaluation
        overall_is_fail = (report["overall"] == "FAIL")
        failed_checks = [c for c in report["checks"] if not c["passed"]]
        failed_check_ids = [c["id"] for c in failed_checks]

        # Check if at least one expected failing check ID was triggered
        matching_failures = [c for c in failed_checks if c["id"] in expected_ids]
        matched_expected = len(matching_failures) > 0

        # Check that error messages are non-empty and clear
        has_clear_messages = all(len(c.get("message", "").strip()) > 0 for c in matching_failures)

        fixture_detected = overall_is_fail and matched_expected and has_clear_messages

        if not fixture_detected:
            all_fixtures_detected = False

        results.append({
            "name": name,
            "url": url,
            "overall": report["overall"],
            "expected_ids": expected_ids,
            "failed_check_ids": failed_check_ids,
            "matching_failures": matching_failures,
            "detected": fixture_detected,
            "duration": duration,
        })

        res_str = "[DETECTED]" if fixture_detected else "[MISSED / UNEXPECTED PASS]"
        print(f"  Result: {res_str} (QA Overall: {report['overall']}, Matched: {[c['id'] for c in matching_failures]} in {duration:.2f}s)")
        for c in matching_failures:
            print(f"    Evidence: [{c['id']}] -> {c['message']}")

    # Print Summary Table
    print("\n" + "=" * 110)
    print("                          FIXTURE DETECTION SUMMARY TABLE")
    print("=" * 110)
    header = f"{'Fixture Name':<20} | {'Expected Check':<46} | {'QA Status':<10} | {'Detection':<14} | {'Time'}"
    print(header)
    print("-" * 110)

    for r in results:
        expected_str = "/".join(r["expected_ids"])
        qa_stat = r["overall"]
        det_str = "PASS (FOUND)" if r["detected"] else "FAIL (MISSED)"
        time_str = f"{r['duration']:.2f}s"
        row = f"{r['name']:<20} | {expected_str:<46} | {qa_stat:<10} | {det_str:<14} | {time_str}"
        print(row)

    print("-" * 110)
    status_summary = (
        "ALL FIXTURES SUCCESSFULLY DETECTED"
        if all_fixtures_detected
        else "FIXTURE DETECTION FAILURE"
    )
    detected_count = sum(1 for r in results if r["detected"])
    print(f"SUITE STATUS: {status_summary} ({detected_count}/{len(results)} fixtures detected)")
    print("=" * 110)

    if not all_fixtures_detected:
        print("\nERROR: One or more known-broken fixtures were not detected as expected.")
        for r in results:
            if not r["detected"]:
                print(f"  - Fixture '{r['name']}': QA overall={r['overall']}, Failed checks={r['failed_check_ids']}, Expected={r['expected_ids']}")
        sys.exit(1)

    print("\n[SUCCESS] QA test suite accurately caught all deliberate faults per Section 7.4.")
    sys.exit(0)


if __name__ == "__main__":
    main()
