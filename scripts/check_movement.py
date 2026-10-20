#!/usr/bin/env python3
"""
AETHER Movement Speed and Wall Sliding Consistency Checker (Wrapper).
"""
import sys
from pathlib import Path

backend_script = Path(__file__).resolve().parent.parent / "aether-backend" / "scripts" / "check_movement.py"
if backend_script.exists():
    with open(backend_script, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, str(backend_script), "exec"), globals())
else:
    print(f"Error: {backend_script} not found")
    sys.exit(1)
