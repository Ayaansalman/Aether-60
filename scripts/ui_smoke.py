#!/usr/bin/env python3
"""
AETHER UI Smoke Test Suite Runner (Root wrapper).
Forwards to aether-backend/scripts/ui_smoke.py.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
backend_script = root_dir / "aether-backend" / "scripts" / "ui_smoke.py"

if backend_script.exists():
    with open(backend_script, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, str(backend_script), "exec"), globals())
else:
    print(f"Error: Could not locate ui_smoke script at {backend_script}")
    sys.exit(1)
