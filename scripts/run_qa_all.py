#!/usr/bin/env python3
"""
AETHER Automated QA Test Suite Runner.
Runs Playwright QA checks against all demo routes:
- /play/demo (collect_count, projectile)
- /play/demo-survive (survive_seconds, projectile)
- /play/demo-melee (collect_count, melee)
- /play/demo-avoid (collect_count, avoid_only)

Ensures the Vite frontend dev server is running before executing tests.
Outputs a clean PASS/FAIL report table.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


class QAResult(TypedDict):
    name: str
    url: str
    overall: str
    passed_checks: int
    total_checks: int
    failed_checks: List[str]
    screenshot: str
    page_errors: List[str]
    duration: float
    report: Dict[str, Any]

# Resolve directory structure
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "aether-backend").exists() else SCRIPT_DIR.parent.parent
BACKEND_DIR = PROJECT_ROOT / "aether-backend"
FRONTEND_DIR = PROJECT_ROOT / "aether-frontend"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts" / "qa"

# Ensure backend directory is in sys.path
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from services.qa_runner import run_qa
except ImportError as err:
    print(f"Error importing run_qa from services.qa_runner: {err}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


TARGETS = [
    {
        "name": "demo (projectile)",
        "route": "/play/demo",
        "url": "http://localhost:5173/play/demo"
    },
    {
        "name": "demo-survive (timer)",
        "route": "/play/demo-survive",
        "url": "http://localhost:5173/play/demo-survive"
    },
    {
        "name": "demo-melee (melee flash)",
        "route": "/play/demo-melee",
        "url": "http://localhost:5173/play/demo-melee"
    },
    {
        "name": "demo-avoid (avoid only)",
        "route": "/play/demo-avoid",
        "url": "http://localhost:5173/play/demo-avoid"
    },
]


def is_server_listening(host: str = "localhost", port: int = 5173, timeout: float = 1.5) -> bool:
    """Checks if a TCP port is currently accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def ensure_dev_server() -> Optional[subprocess.Popen]:
    """Ensures Vite dev server is running on http://localhost:5173."""
    if is_server_listening("localhost", 5173):
        print("[QA Suite] Frontend dev server is already running on http://localhost:5173")
        return None

    print("[QA Suite] Dev server not detected on port 5173. Spawning Vite dev server...")
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

    server_process = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Poll until ready
    max_wait = 25.0
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_server_listening("localhost", 5173):
            print(f"[QA Suite] Dev server ready on http://localhost:5173 in {time.time() - start_time:.1f}s")
            return server_process
        time.sleep(0.5)

    print("[QA Suite] WARNING: Dev server failed to respond within 25 seconds.")
    return server_process


def main():
    print("=" * 90)
    print("                 AETHER CAPSTONE AUTOMATED QA TEST SUITE")
    print("=" * 90)

    server_proc = ensure_dev_server()
    results: List[QAResult] = []

    try:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

        for target in TARGETS:
            name = target["name"]
            url = target["url"]
            print(f"\n[Running QA] -> {name} ({url}) ...")
            start = time.time()
            report = run_qa(url, str(ARTIFACTS_DIR))
            duration = time.time() - start

            passed_checks = sum(1 for c in report["checks"] if c["passed"])
            total_checks = len(report["checks"])
            failed_checks = [c["id"] for c in report["checks"] if not c["passed"]]

            results.append({
                "name": name,
                "url": url,
                "overall": report["overall"],
                "passed_checks": passed_checks,
                "total_checks": total_checks,
                "failed_checks": failed_checks,
                "screenshot": report.get("screenshot_path", ""),
                "page_errors": report.get("page_errors", []),
                "duration": duration,
                "report": report
            })

            status_symbol = "[PASS]" if report["overall"] == "PASS" else "[FAIL]"
            print(f"  Result: {status_symbol} ({passed_checks}/{total_checks} checks passed in {duration:.2f}s)")
            if failed_checks:
                print(f"  Failed checks: {', '.join(failed_checks)}")

    finally:
        # Note: If server was started by us, we keep it running or cleanly exit
        pass

    # Print Summary Table
    print("\n" + "=" * 90)
    print("                                SUMMARY QA REPORT TABLE")
    print("=" * 90)
    header = f"{'Target Mode':<26} | {'Route / URL':<34} | {'Status':<8} | {'Checks':<8} | {'Screenshot'}"
    print(header)
    print("-" * 90)

    all_passed = True
    for res in results:
        mode_str = res["name"]
        url_str = res["url"].replace("http://localhost:5173", "")
        status_str = res["overall"]
        checks_str = f"{res['passed_checks']}/{res['total_checks']}"
        screenshot_name = Path(res["screenshot"]).name if res["screenshot"] else "None"

        idle_surv = None
        for c in res["report"]["checks"]:
            if c["id"] == "idle_survival_min_seconds":
                idle_surv = c.get("measured", {}).get("survived_seconds")

        if res["overall"] != "PASS":
            all_passed = False

        idle_str = f"idle={idle_surv}s" if idle_surv is not None else ""
        row = f"{mode_str:<26} | {url_str:<24} | {status_str:<8} | {checks_str:<8} | {idle_str:<12} | {screenshot_name}"
        print(row)

    print("-" * 90)
    suite_status = "ALL PASS" if all_passed else "FAILURES DETECTED"
    print(f"OVERALL SUITE STATUS: {suite_status} ({sum(1 for r in results if r['overall'] == 'PASS')}/{len(results)} modes passed)")
    print("=" * 90)

    # Print failed details if any
    if not all_passed:
        print("\nFAILURE DETAILS:")
        for res in results:
            if res["overall"] != "PASS":
                print(f"\nMode: {res['name']} ({res['url']})")
                for c in res["report"]["checks"]:
                    if not c["passed"]:
                        print(f"  - Check [{c['id']}]: {c.get('message', 'Failed')}")
                if res["page_errors"]:
                    print(f"  - Console/Page Errors: {res['page_errors']}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
