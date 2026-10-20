#!/usr/bin/env python3
"""
AETHER Automated QA Test Suite Runner (Backend wrapper).
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
v3_dir = backend_dir.parent
script_path = v3_dir / "scripts" / "run_qa_all.py"

if script_path.exists():
    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, str(script_path), "exec"), globals())
else:
    print(f"Error: Could not locate master script at {script_path}")
    sys.exit(1)
