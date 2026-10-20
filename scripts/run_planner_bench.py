#!/usr/bin/env python3
"""
CLI utility wrapper for run_planner_bench.py.
"""
import sys
from pathlib import Path

backend_script = Path(__file__).resolve().parent.parent / "aether-backend" / "scripts" / "run_planner_bench.py"
if backend_script.exists():
    with open(backend_script, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, str(backend_script), "exec"), globals())
else:
    print(f"Error: {backend_script} not found")
    sys.exit(1)
