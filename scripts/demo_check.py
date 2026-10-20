#!/usr/bin/env python3
"""
AETHER Pre-Demo Verification Suite (Phase 6).
Validates system readiness for presentations:
1. Backend service health check (/api/v1/health)
2. Frontend service accessibility (port 5173 or static assets)
3. Provider & API key configuration (without printing secrets)
4. Offline fallback demo asset integrity (spooky, pirate, repaired)
5. Spec validity against GameIR schema
6. Optional model ping (1 request only, default: OFF to protect free-tier quota)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "aether-backend"
FRONTEND_DIR = ROOT_DIR / "aether-frontend"

# Add backend directory to sys.path
sys.path.insert(0, str(BACKEND_DIR))


def check_api_key_configuration() -> bool:
    """Verifies that API key is set without printing secret characters."""
    print("\n[1/5] Checking Provider & Model Configuration...")
    env_file = BACKEND_DIR / ".env"
    key_found = False
    key_len = 0
    provider = os.environ.get("MODEL_PROVIDER", "")
    model_name = os.environ.get("MODEL_NAME", "")
    fallbacks = os.environ.get("MODEL_FALLBACKS", "")

    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODEL_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        key_found = True
                        key_len = len(val)
                elif line.startswith("MODEL_PROVIDER=") and not provider:
                    provider = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("MODEL_NAME=") and not model_name:
                    model_name = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("MODEL_FALLBACKS=") and not fallbacks:
                    fallbacks = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not provider:
        provider = "openai_compat"
    if not model_name:
        model_name = "gemini-3.5-flash-lite"

    print(f"  - Provider       : {provider}")
    print(f"  - Model ID       : {model_name}")
    print(f"  - Fallbacks      : {fallbacks if fallbacks else '(none configured)'}")
    if key_found or os.environ.get("MODEL_API_KEY"):
        k = os.environ.get("MODEL_API_KEY", "")
        if k:
            key_len = len(k)
        print(f"  - API Key Status : CONFIGURED ({key_len} characters, key hidden for security)")
        return True
    else:
        print("  - API Key Status : NOT CONFIGURED (Mock & offline demo mode available)")
        return False


def check_backend_health() -> bool:
    """Checks FastAPI backend health endpoint."""
    print("\n[2/5] Checking Backend Health (/api/v1/health)...")
    url = "http://127.0.0.1:8000/api/v1/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AETHER-DemoCheck/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                print(f"  [PASS] Backend online: {body}")
                return True
            else:
                print(f"  [FAIL] Backend returned HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"  [WARN] Backend is not currently running on port 8000 ({e}).")
        print("         Offline fallback demos will still work via Vite frontend.")
        return False


def check_frontend_status() -> bool:
    """Checks if frontend dev server is running or dist assets exist."""
    print("\n[3/5] Checking Frontend Accessibility...")
    url = "http://127.0.0.1:5173/"
    dev_server_running = False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AETHER-DemoCheck/1.0"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                dev_server_running = True
                print("  [PASS] Frontend Vite dev server is running at http://localhost:5173/")
    except Exception:
        pass

    if not dev_server_running:
        dist_index = FRONTEND_DIR / "dist" / "index.html"
        if dist_index.exists():
            print("  [INFO] Vite dev server not detected, but production build exists at dist/index.html")
        else:
            print("  [WARN] Neither Vite dev server nor dist/index.html detected. Run start_all.ps1 or npm run build.")

    return True


def check_offline_fallbacks() -> bool:
    """Verifies that all 3 offline fallback demos exist and conform to GameIR."""
    print("\n[4/5] Checking Offline Fallback Demos & GameIR Schema...")
    fallback_dir = FRONTEND_DIR / "public" / "fallback"
    manifest_file = fallback_dir / "manifest.json"
    saved_demos_ts = FRONTEND_DIR / "src" / "game" / "savedDemos.ts"

    if not manifest_file.exists():
        print(f"  [FAIL] Manifest missing: {manifest_file}")
        return False
    if not saved_demos_ts.exists():
        print(f"  [FAIL] savedDemos.ts missing: {saved_demos_ts}")
        return False

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Import Pydantic schema for validation
    from schemas.game_ir import GameIR

    required_slugs = ["spooky", "pirate", "repaired"]
    all_valid = True

    for slug in required_slugs:
        slug_dir = fallback_dir / slug
        spec_path = slug_dir / "spec.json"
        qa_path = slug_dir / "qa.json"
        events_path = slug_dir / "events.json"
        screenshot_path = slug_dir / "screenshot.png"

        missing = []
        for p, name in [
            (spec_path, "spec.json"),
            (qa_path, "qa.json"),
            (events_path, "events.json"),
            (screenshot_path, "screenshot.png"),
        ]:
            if not p.exists():
                missing.append(name)

        if missing:
            print(f"  [FAIL] Demo '{slug}' is missing files: {', '.join(missing)}")
            all_valid = False
            continue

        # Validate GameIR
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec_data = json.load(f)
            validated = GameIR(**spec_data)

            # Check QA overall
            with open(qa_path, "r", encoding="utf-8") as f:
                qa_data = json.load(f)
            qa_overall = qa_data.get("overall", "UNKNOWN")
            checks_count = len(qa_data.get("checks", []))

            print(f"  [PASS] Demo '{slug}': '{validated.title}' ({validated.genre}, theme: {validated.theme})")
            print(f"         QA: {qa_overall} ({checks_count} checks) | Screenshot: OK")
        except Exception as e:
            print(f"  [FAIL] GameIR schema validation error for '{slug}': {e}")
            all_valid = False

    return all_valid


def execute_optional_ping() -> bool:
    """Sends exactly 1 lightweight model completion request to measure latency."""
    print("\n[5/5] Executing Model Ping (--ping enabled)...")
    try:
        from providers.factory import get_provider
        provider = get_provider()
        prompt = "Reply with the single word 'ok'."
        t0 = time.time()
        res = provider.complete("You are a helpful assistant.", prompt)
        dt_ms = (time.time() - t0) * 1000.0

        print(f"  [PASS] Live Model Ping succeeded!")
        print(f"         Provider Response : '{res.text.strip()}'")
        print(f"         Latency           : {dt_ms:.1f} ms")
        return True
    except Exception as e:
        print(f"  [FAIL] Model Ping failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="AETHER Demo Verification Suite (Phase 6)")
    parser.add_argument(
        "--ping",
        action="store_true",
        default=False,
        help="Send 1 live model request to verify upstream connectivity (off by default to preserve quota).",
    )
    args = parser.parse_args()

    print("============================================================")
    print("             AETHER PRE-DEMO VERIFICATION SUITE             ")
    print("============================================================")

    check_api_key_configuration()
    check_backend_health()
    check_frontend_status()
    fallbacks_ok = check_offline_fallbacks()

    if args.ping:
        ping_ok = execute_optional_ping()
    else:
        print("\n[5/5] Model Ping:")
        print("  [SKIP] Model ping skipped (default: OFF to preserve free-tier API quota).")
        print("         Pass --ping to execute 1 live completion test.")
        ping_ok = True

    print("\n============================================================")
    if fallbacks_ok and ping_ok:
        print("  RESULT: DEMO ENVIRONMENT READY (Offline fallbacks verified)")
        print("============================================================")
        sys.exit(0)
    else:
        print("  RESULT: DEMO ENVIRONMENT HAS WARNINGS OR FAILURES")
        print("============================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
