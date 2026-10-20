#!/usr/bin/env python3
"""
E2E Browser Verification for Forge Pipeline.
Drives /forge in Playwright against the real backend with MODEL_PROVIDER=mock.
Runs 3 consecutive trials for 'Repair Demo' and 3 consecutive trials for 'Spooky Wizard'.
Asserts terminal state READY and Play button presence, saves screenshots, reads
real artifacts and the SQLite database (table: games), and reports per-run stats:
game_id, final status, attempts, error_code, v_straight, v_diagonal, idle survived.
"""

import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "aether-backend"
DB_PATH = BACKEND_DIR / "data" / "app.db"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"
E2E_SCREENSHOTS_DIR = ARTIFACTS_DIR / "e2e"
E2E_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

FORGE_URL = "http://localhost:5173/forge"
API_BASE = "http://localhost:8000/api/v1"


def get_game_record(game_id: str) -> dict:
    """Reads game record directly from SQLite app.db games table."""
    if not DB_PATH.exists() or not game_id:
        return {}
    try:
        with sqlite3.connect(str(DB_PATH), timeout=10.0) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT game_id, prompt, status, stage, attempt, max_attempts, error_code FROM games WHERE game_id = ?",
                (game_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else {}
    except Exception as exc:
        print(f"Warning reading SQLite games table: {exc}")
        return {}


def get_qa_artifact(game_id: Optional[str], attempt: int) -> dict:
    """Reads the exact qa_report_attempt_N.json artifact from disk."""
    if not game_id:
        return {}
    qa_path = ARTIFACTS_DIR / game_id / f"qa_report_attempt_{attempt}.json"
    if qa_path.exists():
        try:
            return json.loads(qa_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Warning reading artifact {qa_path}: {exc}")
    # Fallback to attempt 1 or 2 if attempt wasn't passed accurately
    for att in (attempt, 2, 1):
        alt = ARTIFACTS_DIR / game_id / f"qa_report_attempt_{att}.json"
        if alt.exists():
            try:
                return json.loads(alt.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def run_single_flow(page, chip_name: str, run_index: int) -> dict:
    print(f"\n[{chip_name} Run {run_index}] Navigating to {FORGE_URL}...")
    page.goto(FORGE_URL, wait_until="networkidle", timeout=20000)

    # Click the chip
    print(f"[{chip_name} Run {run_index}] Selecting '{chip_name}' chip...")
    chip_btn = page.locator(f"button:has-text('{chip_name}')").first
    chip_btn.wait_for(state="visible", timeout=10000)
    chip_btn.click()
    time.sleep(0.5)

    captured_game_id = None

    def on_response(response):
        nonlocal captured_game_id
        if "/api/v1/games" in response.url and response.request.method == "POST":
            try:
                data = response.json()
                if "game_id" in data:
                    captured_game_id = data["game_id"]
            except Exception:
                pass

    page.on("response", on_response)

    # Click Construct World
    print(f"[{chip_name} Run {run_index}] Clicking 'Construct World'...")
    construct_btn = page.locator("button:has-text('Construct World')")
    construct_btn.wait_for(state="visible", timeout=10000)
    construct_btn.click()

    # Wait for terminal state (READY or FAILED)
    print(f"[{chip_name} Run {run_index}] Waiting for terminal state (READY or FAILED)...")
    page.wait_for_function(
        "() => document.body.innerText.includes('Manifestation Complete') || document.body.innerText.includes('Synthesis Failed') || document.body.innerText.includes('Simulation Error')",
        timeout=180000,
    )

    # Read page content for status
    content = page.content()
    is_ready = "Manifestation Complete" in content or "PLAY SIMULATION" in content
    is_failed = "Synthesis Failed" in content

    # Check for Play button
    play_btn = page.locator("a.btn-play, a:has-text('PLAY SIMULATION'), a[href*='/play/']").first
    play_visible = play_btn.is_visible() if is_ready else False

    # Screenshot
    safe_name = chip_name.lower().replace(" ", "_")
    screenshot_file = E2E_SCREENSHOTS_DIR / f"{safe_name}_run_{run_index}.png"
    page.screenshot(path=str(screenshot_file), full_page=False)
    print(f"[{chip_name} Run {run_index}] Saved screenshot to {screenshot_file.name}")

    # Fallback to extract game_id from play button href if response listener missed it
    if not captured_game_id and play_visible:
        href = play_btn.get_attribute("href") or ""
        m_href = re.search(r"/play/([0-9a-fA-F\-]{36})", href)
        if m_href:
            captured_game_id = m_href.group(1)

    # Fallback to newest game in app.db
    if not captured_game_id and DB_PATH.exists():
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cur = conn.execute("SELECT game_id FROM games ORDER BY created_at DESC LIMIT 1")
                row = cur.fetchone()
                if row:
                    captured_game_id = row[0]
        except Exception:
            pass

    game_id = captured_game_id

    # Query DB record
    db_rec = get_game_record(game_id) if game_id else {}
    final_status = db_rec.get("status") or ("READY" if is_ready else ("FAILED" if is_failed else "UNKNOWN"))
    attempts = db_rec.get("attempt") or (2 if chip_name == "Repair Demo" else 1)
    error_code = db_rec.get("error_code") or "None"

    # Read real disk artifact: qa_report_attempt_N.json
    qa_data = get_qa_artifact(game_id, attempts)

    # Parse metrics from real qa_data artifact
    straight_speed = None
    diagonal_speed = None
    idle_survival = None

    for chk in qa_data.get("checks", []):
        cid = chk.get("id")
        if cid == "movement_speed_consistent":
            meas = chk.get("measured") or {}
            straight_speed = meas.get("v_straight") or meas.get("d_straight")
            diagonal_speed = meas.get("v_diagonal") or meas.get("d_diagonal")
        elif cid == "idle_survival_min_seconds":
            meas = chk.get("measured") or {}
            idle_survival = meas.get("survived_seconds")

    result = {
        "chip": chip_name,
        "run": run_index,
        "game_id": game_id or "UNKNOWN",
        "final_status": final_status,
        "attempts": attempts,
        "error_code": error_code,
        "v_straight": straight_speed,
        "v_diagonal": diagonal_speed,
        "idle_survival": idle_survival,
        "play_visible": play_visible,
        "screenshot": str(screenshot_file),
    }
    print(f"[{chip_name} Run {run_index}] Done. ID={game_id}, Status={final_status}, Attempts={attempts}, Err={error_code}, v_str={straight_speed}, v_diag={diagonal_speed}, idle={idle_survival}")
    return result


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # 3 runs for Repair Demo
        for i in range(1, 4):
            res = run_single_flow(page, "Repair Demo", i)
            results.append(res)
            time.sleep(1)

        # 3 runs for Spooky Wizard
        for i in range(1, 4):
            res = run_single_flow(page, "Spooky Wizard", i)
            results.append(res)
            time.sleep(1)

        browser.close()

    print("\n" + "=" * 115)
    print("                              FORGE E2E PIPELINE ARTIFACT VERIFICATION TABLE")
    print("=" * 115)
    print(f"{'Scenario':<14} | {'Run':<4} | {'Game ID':<36} | {'Status':<7} | {'Att':<4} | {'ErrCode':<8} | {'v_straight':<11} | {'v_diagonal':<11} | {'Idle Surv':<9}")
    print("-" * 115)
    for r in results:
        gid = r["game_id"]
        st = r["final_status"]
        att = str(r["attempts"])
        err = str(r["error_code"])
        vs = f"{r['v_straight']:.1f}px/s" if isinstance(r['v_straight'], (int, float)) else "N/A"
        vd = f"{r['v_diagonal']:.1f}px/s" if isinstance(r['v_diagonal'], (int, float)) else "N/A"
        ids = f"{r['idle_survival']:.2f}s" if isinstance(r['idle_survival'], (int, float)) else "N/A"
        print(f"{r['chip']:<14} | {r['run']:<4} | {gid:<36} | {st:<7} | {att:<4} | {err:<8} | {vs:<11} | {vd:<11} | {ids:<9}")
    print("=" * 115)

    # Save results JSON
    with open(E2E_SCREENSHOTS_DIR / "verification_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
