#!/usr/bin/env python3
"""
Verification script for slow-player wall-reach QA fix.
Tests:
1. Valid spec with move_speed = 100.0 passes movement_speed_consistent (17/17 pass).
2. p06 initial spec (move_speed = 110, 15 chasers @ 220, 2 HP) passes movement_speed_consistent,
   fails ONLY patchable survival checks (idle_survival_min_seconds / flee_bot_survives),
   and sets repair_recommended = True.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "aether-backend"
FRONTEND_DIR = PROJECT_ROOT / "aether-frontend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.qa_runner import run_qa


def is_listening(port: int = 5173) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=1.0):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def ensure_vite():
    if is_listening(5173):
        return None
    print("[verify_slow_player] Starting Vite on port 5173...")
    env = os.environ.copy()
    if r"C:\Program Files\nodejs" not in env.get("PATH", ""):
        env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    p = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if is_listening(5173):
            print("[verify_slow_player] Vite ready.")
            return p
        time.sleep(0.5)
    raise RuntimeError("Vite failed to start on port 5173")


def main():
    proc = ensure_vite()
    try:
        print("\n============================================================")
        print("  TEST 1: Valid spec with player.move_speed = 100.0 px/s")
        print("============================================================")
        res_100 = run_qa("http://localhost:5173/play/test-slow-100")
        check_speed_100 = next((c for c in res_100["checks"] if c["id"] == "movement_speed_consistent"), None)
        assert check_speed_100 is not None, "Check movement_speed_consistent not found"
        print(f"  movement_speed_consistent: {'PASS' if check_speed_100['passed'] else 'FAIL'}")
        passed_count = len([c for c in res_100["checks"] if c["passed"]])
        print(f"  Overall QA: {res_100['overall']} ({passed_count}/{len(res_100['checks'])} checks passed)")
        assert check_speed_100["passed"], f"movement_speed_consistent failed for speed=100.0: {check_speed_100.get('message')}"
        assert res_100["overall"] == "PASS", f"Overall QA failed for valid 100.0px/s spec: {[c['id'] for c in res_100['checks'] if not c['passed']]}"
        print("  [+] TEST 1 PASSED: 100.0 px/s player passed all checks including movement_speed_consistent.\n")

        print("============================================================")
        print("  TEST 2: p06 Initial Spec (move_speed=110, 15 chasers @ 220, 2 HP)")
        print("============================================================")
        res_p06 = run_qa("http://localhost:5173/play/test-p06")
        check_speed_p06 = next((c for c in res_p06["checks"] if c["id"] == "movement_speed_consistent"), None)
        assert check_speed_p06 is not None, "Check movement_speed_consistent not found"
        print(f"  movement_speed_consistent: {'PASS' if check_speed_p06['passed'] else 'FAIL'}")

        failed_checks = [c for c in res_p06["checks"] if not c["passed"]]
        failed_ids = [c["id"] for c in failed_checks]
        non_patchable_failed = [c["id"] for c in failed_checks if not c.get("patchable", False)]
        patchable_failed = [c["id"] for c in failed_checks if c.get("patchable", False)]

        print(f"  Failed checks total: {failed_ids}")
        print(f"  Non-patchable failed: {non_patchable_failed}")
        print(f"  Patchable failed: {patchable_failed}")
        print(f"  repair_recommended: {res_p06.get('repair_recommended')}")

        assert check_speed_p06["passed"], f"movement_speed_consistent must pass, but failed: {check_speed_p06.get('message')}"
        assert len(non_patchable_failed) == 0, f"Non-patchable checks must NOT fail: {non_patchable_failed}"
        assert "idle_survival_min_seconds" in patchable_failed, "idle_survival_min_seconds should fail due to 15 chasers"
        assert "flee_bot_survives" in patchable_failed, "flee_bot_survives should fail due to 15 chasers @ 220px/s vs 110px/s"
        assert res_p06.get("repair_recommended"), "repair_recommended MUST be True when only patchable checks fail"
        print("  [+] TEST 2 PASSED: p06 passes movement_speed_consistent and triggers bounded repair loop!\n")

        print("============================================================")
        print("  ALL SLOW-PLAYER QA FIX VERIFICATION TESTS PASSED (2/2)")
        print("============================================================")
    finally:
        if proc:
            proc.terminate()
            proc.wait()


if __name__ == "__main__":
    main()
