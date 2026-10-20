"""
API Walkthrough and Acceptance Test Script.
Starts FastAPI backend in the background (mock provider, QA_MODE=fake),
validates all error paths, walks one job to READY, verifies spec, QA, events,
artifacts, shuts down server, and prints a formatted PASS table.
Conforms to Phase 1 Acceptance Criteria.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / "aether-backend"
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

PORT = int(os.getenv("API_PORT", "8000"))
BASE_URL = f"http://127.0.0.1:{PORT}"


def main() -> int:
    env = os.environ.copy()
    env["MODEL_PROVIDER"] = "mock"
    env["QA_MODE"] = "fake"
    env["PYTHONPATH"] = str(BACKEND_DIR)

    server_cmd = [
        str(VENV_PYTHON),
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
    ]

    print(f"[api_walk] Starting backend server on {BASE_URL} (mock provider, QA_MODE=fake)...")
    server_proc = subprocess.Popen(
        server_cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    results: List[Dict[str, Any]] = []

    try:
        # 1. Health check wait
        server_ready = False
        with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
            for _ in range(30):
                if server_proc.poll() is not None:
                    _, err = server_proc.communicate()
                    print(f"[api_walk] ERROR: Server process terminated early:\n{err.decode('utf-8', errors='replace')}")
                    return 1
                try:
                    r = client.get("/api/v1/health")
                    if r.status_code == 200 and r.json().get("status") == "ok":
                        server_ready = True
                        results.append({
                            "name": "Health check /api/v1/health",
                            "status": "PASS",
                            "details": f"Provider={r.json().get('provider')}, Model={r.json().get('model')}"
                        })
                        break
                except Exception:
                    time.sleep(0.5)

        if not server_ready:
            print("[api_walk] ERROR: Timed out awaiting backend startup.")
            return 1

        with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
            # 2. Error Path A: Empty prompt
            r_empty = client.post("/api/v1/games", json={"prompt": "   "})
            if r_empty.status_code == 400 and r_empty.json().get("error_code") == "PROMPT_INVALID":
                results.append({
                    "name": "Error Path: Empty prompt rejection",
                    "status": "PASS",
                    "details": "Returned HTTP 400 with PROMPT_INVALID"
                })
            else:
                results.append({
                    "name": "Error Path: Empty prompt rejection",
                    "status": "FAIL",
                    "details": f"Status={r_empty.status_code}, Body={r_empty.text}"
                })

            # 3. Error Path B: Oversized prompt (>1200 chars)
            oversized = "w" * 1250
            r_over = client.post("/api/v1/games", json={"prompt": oversized})
            if r_over.status_code == 400 and r_over.json().get("error_code") == "PROMPT_INVALID":
                results.append({
                    "name": "Error Path: >1200 chars prompt rejection",
                    "status": "PASS",
                    "details": "Returned HTTP 400 with PROMPT_INVALID"
                })
            else:
                results.append({
                    "name": "Error Path: >1200 chars prompt rejection",
                    "status": "FAIL",
                    "details": f"Status={r_over.status_code}, Body={r_over.text}"
                })

            # 4. Error Path C: Non-existent Game ID
            r_404 = client.get("/api/v1/games/00000000-0000-0000-0000-000000000000")
            if r_404.status_code == 404 and r_404.json().get("error_code") == "GAME_NOT_FOUND":
                results.append({
                    "name": "Error Path: Unknown Game ID",
                    "status": "PASS",
                    "details": "Returned HTTP 404 with GAME_NOT_FOUND"
                })
            else:
                results.append({
                    "name": "Error Path: Unknown Game ID",
                    "status": "FAIL",
                    "details": f"Status={r_404.status_code}, Body={r_404.text}"
                })

            # 5. Error Path D: Safe Artifact Download Rejection
            r_art_rej = client.get("/api/v1/games/00000000-0000-0000-0000-000000000000/artifacts/malicious.exe")
            if r_art_rej.status_code == 403:
                results.append({
                    "name": "Error Path: Forbidden Artifact Download",
                    "status": "PASS",
                    "details": "Returned HTTP 403 for unapproved artifact name"
                })
            else:
                results.append({
                    "name": "Error Path: Forbidden Artifact Download",
                    "status": "FAIL",
                    "details": f"Status={r_art_rej.status_code}, Body={r_art_rej.text}"
                })

            # 6. Happy Path: Submit prompt
            prompt_text = "a spooky wizard collecting glowing crystals while ghosts chase me"
            r_sub = client.post("/api/v1/games", json={"prompt": prompt_text})
            if r_sub.status_code == 202 and r_sub.json().get("status") == "QUEUED":
                game_id = r_sub.json()["game_id"]
                results.append({
                    "name": "Job Submission POST /api/v1/games",
                    "status": "PASS",
                    "details": f"Returned HTTP 202, game_id={game_id}"
                })
            else:
                results.append({
                    "name": "Job Submission POST /api/v1/games",
                    "status": "FAIL",
                    "details": f"Status={r_sub.status_code}, Body={r_sub.text}"
                })
                return 1

            # 7. Walk Job to Terminal State (READY)
            print(f"[api_walk] Polling status for job {game_id}...")
            job_status = "QUEUED"
            terminal_reached = False
            start_poll = time.time()
            final_job_data: Dict[str, Any] = {}

            while time.time() - start_poll < 30.0:
                r_st = client.get(f"/api/v1/games/{game_id}")
                if r_st.status_code == 200:
                    final_job_data = r_st.json()
                    job_status = final_job_data.get("status")
                    if job_status in ("READY", "READY_WITH_WARNINGS", "FAILED"):
                        terminal_reached = True
                        break
                time.sleep(0.3)

            if terminal_reached and job_status == "READY":
                qa_summary = final_job_data.get("qa_summary", {})
                results.append({
                    "name": "Job Lifecycle State Machine walk to READY",
                    "status": "PASS",
                    "details": f"Reached READY in {time.time()-start_poll:.2f}s (Passed checks={qa_summary.get('passed')})"
                })
            else:
                results.append({
                    "name": "Job Lifecycle State Machine walk to READY",
                    "status": "FAIL",
                    "details": f"Final status={job_status}, Body={final_job_data}"
                })

            # 8. Verify GET /spec
            r_spec = client.get(f"/api/v1/games/{game_id}/spec")
            if r_spec.status_code == 200 and r_spec.json().get("genre") == "arena_survival":
                results.append({
                    "name": "Spec Retrieval GET /api/v1/games/{id}/spec",
                    "status": "PASS",
                    "details": f"Title='{r_spec.json().get('title')}', Theme='{r_spec.json().get('theme')}'"
                })
            else:
                results.append({
                    "name": "Spec Retrieval GET /api/v1/games/{id}/spec",
                    "status": "FAIL",
                    "details": f"Status={r_spec.status_code}, Body={r_spec.text}"
                })

            # 9. Verify GET /qa
            r_qa = client.get(f"/api/v1/games/{game_id}/qa")
            if r_qa.status_code == 200 and r_qa.json().get("overall") == "PASS":
                results.append({
                    "name": "QA Report Retrieval GET /api/v1/games/{id}/qa",
                    "status": "PASS",
                    "details": f"Overall PASS, {len(r_qa.json().get('checks', []))} checks recorded"
                })
            else:
                results.append({
                    "name": "QA Report Retrieval GET /api/v1/games/{id}/qa",
                    "status": "FAIL",
                    "details": f"Status={r_qa.status_code}, Body={r_qa.text}"
                })

            # 10. Verify GET /events
            r_events = client.get(f"/api/v1/games/{game_id}/events")
            if r_events.status_code == 200 and len(r_events.json()) >= 4:
                stages = [e["stage"] for e in r_events.json()]
                results.append({
                    "name": "Ordered Events GET /api/v1/games/{id}/events",
                    "status": "PASS",
                    "details": f"{len(r_events.json())} events, Stages: {' -> '.join(stages)}"
                })
            else:
                results.append({
                    "name": "Ordered Events GET /api/v1/games/{id}/events",
                    "status": "FAIL",
                    "details": f"Status={r_events.status_code}, Count={len(r_events.json()) if r_events.status_code == 200 else 0}"
                })

            # 11. Verify Safe Artifact Download
            r_art = client.get(f"/api/v1/games/{game_id}/artifacts/game_ir_v1.json")
            if r_art.status_code == 200 and len(r_art.text) > 0:
                results.append({
                    "name": "Safe Artifact Download GET /artifacts/game_ir_v1.json",
                    "status": "PASS",
                    "details": f"Downloaded {len(r_art.content)} bytes"
                })
            else:
                results.append({
                    "name": "Safe Artifact Download GET /artifacts/game_ir_v1.json",
                    "status": "FAIL",
                    "details": f"Status={r_art.status_code}"
                })

    finally:
        print("[api_walk] Shutting down backend server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()

    # Print Results Table
    print("\n" + "=" * 90)
    print("AETHER API WALKTHROUGH RESULTS TABLE")
    print("=" * 90)
    print(f"{'Check / Test':<45} | {'Result':<8} | {'Details'}")
    print("-" * 90)
    all_passed = True
    for res in results:
        status_str = f"PASS" if res['status'] == "PASS" else f"FAIL"
        if res['status'] != "PASS":
            all_passed = False
        print(f"{res['name']:<45} | {status_str:<8} | {res['details']}")
    print("=" * 90)

    if all_passed:
        print("OVERALL RESULT: ALL CHECKS PASSED (100%)\n")
        return 0
    else:
        print("OVERALL RESULT: FAILURES DETECTED\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
