#!/usr/bin/env python3
"""
AETHER Movement Speed and Wall Sliding Consistency Checker.
Validates:
1. Straight movement distance d_straight over 500 ms.
2. Diagonal movement distance hypot(dx, dy) in open space within 15% of d_straight.
3. Wall sliding distance along each of the 4 arena walls within 15% of d_straight.
Uses Playwright Sync API against http://localhost:5173/play/demo?test=1.
"""

import math
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

from playwright.sync_api import Page, sync_playwright

_this_file = Path(__file__).resolve()
if _this_file.parent.name == "scripts" and _this_file.parent.parent.name == "aether-backend":
    BACKEND_DIR = _this_file.parent.parent
    FRONTEND_DIR = BACKEND_DIR.parent / "aether-frontend"
else:
    REPO_ROOT = _this_file.parent.parent
    BACKEND_DIR = REPO_ROOT / "aether-backend"
    FRONTEND_DIR = REPO_ROOT / "aether-frontend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def is_server_listening(host: str = "localhost", port: int = 5173, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def ensure_dev_server() -> None:
    if is_server_listening("localhost", 5173):
        return

    print("[check_movement] Starting Vite dev server in background...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=(sys.platform == "win32")
    )
    start_time = time.time()
    while time.time() - start_time < 20.0:
        if is_server_listening("localhost", 5173):
            print(f"[check_movement] Dev server ready in {time.time() - start_time:.1f}s")
            return
        time.sleep(0.5)
    raise RuntimeError("Dev server failed to start on port 5173")


sys.path.insert(0, str(BACKEND_DIR))
from services.qa_runner import run_movement_checks


def main():
    print("=" * 70)
    print("        AETHER PLAYWRIGHT MOVEMENT & WALL SLIDING TEST")
    print("=" * 70)

    ensure_dev_server()

    url = "http://localhost:5173/play/demo?test=1"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_function(
                "() => window.__AETHER_GAME__ && window.__AETHER_GAME__.ready === true",
                timeout=7000,
            )

            passed, msg, details = run_movement_checks(page)

            print(f"\n[Case 1] Straight Movement (500ms):")
            print(f"  Distance: {details.get('d_straight', 0):.2f} px -> PASS")

            print(f"\n[Case 2] Diagonal Open-Space Movement (500ms):")
            diag_res = "PASS" if details.get("diag_pass") else "FAIL"
            print(
                f"  Distance: {details.get('d_diagonal', 0):.2f} px (Diff: {details.get('diag_diff_pct', 0)}%) -> {diag_res}"
            )

            for w in ["right_wall", "left_wall", "bottom_wall", "top_wall"]:
                info = details.get(w, {})
                w_res = "PASS" if info.get("passed") else "FAIL"
                print(f"\n[Case] {w.replace('_', ' ').title()} Sliding (500ms):")
                print(
                    f"  Distance Along Wall: {info.get('d_along', 0):.2f} px (Diff: {info.get('diff_pct', 0)}%) -> {w_res}"
                )

            print("\n" + "=" * 70)
            status_text = "OVERALL MOVEMENT CHECK: PASS" if passed else "OVERALL MOVEMENT CHECK: FAIL"
            print(f"  {status_text}")
            if not passed:
                print(f"  Failure Details: {msg}")
            print("=" * 70)

            sys.exit(0 if passed else 1)

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
