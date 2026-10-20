#!/usr/bin/env python3
"""
Playwright Synchronous UI Smoke Test Suite.
Tests the Forge generation flow, timeline status progression, game loading,
and bounded self-repair flow with repair rationale per Section 6 and 7.3 specifications.
"""

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


def find_frontend_dir() -> Path:
    candidates = [
        Path.cwd() / "aether-frontend",
        Path(__file__).resolve().parent / "aether-frontend",
        Path(__file__).resolve().parent.parent / "aether-frontend",
        Path(__file__).resolve().parent.parent.parent / "aether-frontend",
    ]
    for c in candidates:
        if c.is_dir() and (c / "package.json").is_file():
            return c.resolve()
    raise RuntimeError("Could not locate aether-frontend directory")


FRONTEND_DIR = find_frontend_dir()
NODE_PATH = r"C:\Program Files\nodejs\node.exe"
VITE_BIN = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"


def is_server_ready(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UI-Smoke-Tester"})
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status in (200, 304)
    except Exception:
        return False


def ensure_frontend_server():
    """Starts Vite dev server if not already running."""
    if is_server_ready(FRONTEND_URL):
        print(f"[Smoke Test] Frontend server is already listening at {FRONTEND_URL}")
        return None

    print(f"[Smoke Test] Starting frontend dev server at {FRONTEND_URL}...")
    node_exec = NODE_PATH if os.path.exists(NODE_PATH) else "node"
    env = os.environ.copy()
    env["VITE_USE_MOCK_API"] = "true"

    proc = subprocess.Popen(
        [node_exec, str(VITE_BIN), "--host", "localhost", "--port", "5173"],
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait up to 20 seconds for server to respond
    start = time.time()
    while time.time() - start < 20:
        if is_server_ready(FRONTEND_URL):
            print(f"[Smoke Test] Frontend server ready at {FRONTEND_URL}")
            return proc
        time.sleep(0.5)

    proc.terminate()
    raise RuntimeError(f"Timed out waiting for Vite dev server at {FRONTEND_URL}")


def run_tests():
    server_proc = ensure_frontend_server()
    failed = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1400, "height": 900})
            page = context.new_page()

            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            # =================================================================
            # TEST 1: Standard Prompt -> Timeline reaches READY -> Canvas loads
            # =================================================================
            print("\n[Test 1] Testing standard prompt generation flow...")
            page.goto(f"{FRONTEND_URL}/forge")
            page.wait_for_selector("textarea", timeout=10000)

            test_prompt = "Spooky wizard crystal rush arena collecting gems and surviving"
            page.fill("textarea", test_prompt)
            print(f"  - Filled prompt: '{test_prompt}'")

            # Click Construct World
            construct_btn = page.locator("button:has-text('Construct World')")
            construct_btn.click()
            print("  - Clicked 'Construct World' button")

            # Verify active job ID appears
            page.wait_for_selector("text=Active Job ID:", timeout=5000)
            print("  - Active job ID generated")

            # Wait for timeline to reach READY
            print("  - Polling timeline stages until READY...")
            page.wait_for_selector("text=PLAY SIMULATION", timeout=25000)
            print("  - Timeline reached terminal state: READY")

            # Verify QA report summary is displayed
            page.wait_for_selector("text=QA Summary Report", timeout=5000)
            print("  - QA Summary Report verified")

            # Click Play button to launch the game
            play_btn = page.locator("a:has-text('PLAY SIMULATION')")
            play_url = play_btn.get_attribute("href")
            print(f"  - Launching simulation via Play link: {play_url}")
            play_btn.click()

            # Verify canvas loads in the game view
            page.wait_for_selector("canvas", timeout=12000)
            print("  - Phaser Game Canvas successfully loaded in viewport!")

            time.sleep(1.0)
            print("  -> TEST 1 PASSED: Standard prompt lifecycle verified successfully.")

            # =================================================================
            # TEST 2: 'repair demo' Prompt -> REPAIRING stage & Rationale
            # =================================================================
            print("\n[Test 2] Testing 'repair demo' self-repair flow...")
            page.goto(f"{FRONTEND_URL}/forge")
            page.wait_for_selector("textarea", timeout=10000)

            repair_prompt = "repair demo: cozy garden gathering with challenging rogue chasers"
            page.fill("textarea", repair_prompt)
            print(f"  - Filled prompt: '{repair_prompt}'")

            construct_btn = page.locator("button:has-text('Construct World')")
            construct_btn.click()
            print("  - Clicked 'Construct World' button")

            # Wait for 'Repairing' stage to appear in the timeline or status
            print("  - Waiting for 'Repairing' stage to trigger...")
            repair_stage_locator = page.locator("text=Repairing").first
            repair_stage_locator.wait_for(timeout=20000)
            print("  - 'Repairing' stage confirmed in lifecycle pipeline!")

            # Wait for timeline to reach final READY state
            print("  - Waiting for pipeline to reach final READY state after repair...")
            page.wait_for_selector("text=PLAY SIMULATION", timeout=30000)
            print("  - Repaired pipeline successfully reached terminal state: READY")

            # Verify repair rationale is visible on the page
            print("  - Verifying repair rationale visibility...")
            rationale_locator = page.locator("text=Autonomous Self-Repair Sequence Executed").or_(
                page.locator("text=player_moves")
            ).first
            rationale_locator.wait_for(timeout=5000)

            # Check repair diff tab in Technical Trace Drawer
            repair_tab = page.locator("button:has-text('Repair Diff')")
            if repair_tab.count() > 0:
                repair_tab.first.click()
                time.sleep(0.5)
                assert (
                    page.locator("text=Repair Rationale:").is_visible()
                    or page.locator("text=Before (Failing Spec)").is_visible()
                ), "Repair diff content not visible"
                print("  - Repair rationale and before/after diff verified in Technical Trace Drawer!")

            print("  -> TEST 2 PASSED: Self-repair cycle and rationale verified successfully.")

            browser.close()

    except Exception as e:
        print(f"\n[Smoke Test ERROR] Test execution failed: {e}")
        failed = True
    finally:
        if server_proc:
            print("[Smoke Test] Terminating background frontend server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=3)
            except Exception:
                server_proc.kill()

    if failed:
        sys.exit(1)
    else:
        print("\n=======================================================")
        print("ALL UI SMOKE TESTS PASSED (2/2)")
        print("=======================================================\n")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
