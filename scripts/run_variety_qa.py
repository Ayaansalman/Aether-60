#!/usr/bin/env python3
"""
Automated Variety QA Runner.
Executes real Playwright QA checks on each new variety demo route:
- /play/demo-bouncer-pillars
- /play/demo-patrol-lanes
- /play/demo-dasher-defeat
- /play/demo-shooter-pillars
- /play/demo-maze-collect

Captures screenshots to artifacts/variety/ and generates a contact sheet.
Outputs a clean results table.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "aether-backend"
FRONTEND_DIR = PROJECT_ROOT / "aether-frontend"
VARIETY_DIR = PROJECT_ROOT / "artifacts" / "variety"
VARIETY_DIR.mkdir(parents=True, exist_ok=True)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.qa_runner import run_qa

def is_server_listening(host: str = "localhost", port: int = 5173, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def ensure_dev_server() -> Optional[subprocess.Popen]:
    if is_server_listening("localhost", 5173):
        print("[Variety QA] Frontend dev server is already running on http://localhost:5173")
        return None

    print("[Variety QA] Dev server not detected on port 5173. Spawning Vite dev server...")
    env = os.environ.copy()
    nodejs_dir = r"C:\Program Files\nodejs"
    if nodejs_dir not in env.get("PATH", ""):
        env["PATH"] = f"{nodejs_dir};" + env.get("PATH", "")

    node_bin = Path(r"C:\Program Files\nodejs\node.exe")
    vite_bin = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    if node_bin.exists() and vite_bin.exists():
        cmd = [str(node_bin), str(vite_bin), "--host", "localhost", "--port", "5173"]
    else:
        npm_cmd = str(Path(r"C:\Program Files\nodejs\npm.cmd")) if Path(r"C:\Program Files\nodejs\npm.cmd").exists() else ("npm.cmd" if sys.platform == "win32" else "npm")
        cmd = [npm_cmd, "run", "dev"]

    server_process = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    max_wait = 25.0
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_server_listening("localhost", 5173):
            print(f"[Variety QA] Dev server ready on http://localhost:5173 in {time.time() - start_time:.1f}s")
            return server_process
        time.sleep(0.5)

    print("[Variety QA] WARNING: Dev server failed to respond within 25 seconds.")
    return server_process


TARGETS = [
    {
        "name": "demo-bouncer-pillars",
        "route": "/play/demo-bouncer-pillars",
        "url": "http://localhost:5173/play/demo-bouncer-pillars",
        "enemy_types": "bouncer",
        "layout": "pillars",
        "objective": "collect_count (8)",
    },
    {
        "name": "demo-patrol-lanes",
        "route": "/play/demo-patrol-lanes",
        "url": "http://localhost:5173/play/demo-patrol-lanes",
        "enemy_types": "patroller",
        "layout": "lanes",
        "objective": "collect_count (8)",
    },
    {
        "name": "demo-dasher-defeat",
        "route": "/play/demo-dasher-defeat",
        "url": "http://localhost:5173/play/demo-dasher-defeat",
        "enemy_types": "dasher",
        "layout": "open",
        "objective": "defeat_enemies (5)",
    },
    {
        "name": "demo-shooter-pillars",
        "route": "/play/demo-shooter-pillars",
        "url": "http://localhost:5173/play/demo-shooter-pillars",
        "enemy_types": "shooter",
        "layout": "pillars",
        "objective": "survive_seconds (30)",
    },
    {
        "name": "demo-maze-collect",
        "route": "/play/demo-maze-collect",
        "url": "http://localhost:5173/play/demo-maze-collect",
        "enemy_types": "chaser",
        "layout": "maze",
        "objective": "collect_count (6)",
    },
]


def make_contact_sheet(screenshot_paths: List[Path], output_path: Path):
    """Generates a composite contact sheet image from screenshots."""
    images = []
    labels = []
    for p in screenshot_paths:
        if p.exists():
            img = Image.open(p)
            # Resize keeping aspect ratio (width 400, height 300)
            img_thumb = img.resize((400, 300), Image.Resampling.LANCZOS)
            images.append(img_thumb)
            labels.append(p.stem)

    if not images:
        print("[Contact Sheet] No screenshots found.")
        return

    cols = 3
    rows = 2
    cell_w, cell_h = 400, 300
    label_h = 36
    margin = 12

    total_w = cols * cell_w + (cols + 1) * margin
    total_h = rows * (cell_h + label_h) + (rows + 1) * margin

    sheet = Image.new("RGB", (total_w, total_h), color=(15, 23, 42))
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        font = ImageFont.load_default()

    for idx, (img, label) in enumerate(zip(images, labels)):
        r = idx // cols
        c = idx % cols
        x = margin + c * (cell_w + margin)
        y = margin + r * (cell_h + label_h + margin)

        sheet.paste(img, (x, y))
        # Draw border
        draw.rectangle([x, y, x + cell_w, y + cell_h], outline=(56, 189, 248), width=2)
        # Draw label
        draw.text((x + 8, y + cell_h + 8), f"Demo: {label}", fill=(241, 245, 249), font=font)

    sheet.save(output_path, "PNG")
    print(f"[Contact Sheet] Generated composite image at: {output_path}")


def main():
    print("=" * 90)
    print("           AETHER MECHANIC VARIETY QA EVALUATION SUITE")
    print("=" * 90)

    server_proc = ensure_dev_server()
    results = []
    screenshot_files = []

    for t in TARGETS:
        print(f"\n[Running QA] -> {t['name']} ({t['url']}) ...")
        start_t = time.time()
        report = run_qa(t["url"], out_dir=str(VARIETY_DIR))
        dur = time.time() - start_t

        checks = report.get("checks", [])
        passed = sum(1 for c in checks if c.get("passed", False))
        total = len(checks)
        failed = [c["id"] for c in checks if not c.get("passed", False)]

        status = report.get("overall", "UNKNOWN")
        print(f"  Result: [{status}] ({passed}/{total} checks passed in {dur:.2f}s)")
        if failed:
            print(f"  Failed checks: {failed}")

        # Ensure standard demo name screenshot exists
        actual_shot = Path(report.get("screenshot_path", ""))
        canonical_shot = VARIETY_DIR / f"{t['name']}.png"
        if actual_shot.exists() and actual_shot != canonical_shot:
            canonical_shot.write_bytes(actual_shot.read_bytes())
        target_shot = canonical_shot if canonical_shot.exists() else actual_shot

        results.append({
            "target": t,
            "passed": passed,
            "total": total,
            "status": status,
            "failed": failed,
            "duration": dur,
            "screenshot": target_shot,
        })
        screenshot_files.append(target_shot)

    # Generate composite contact sheet
    contact_sheet_path = VARIETY_DIR / "contact_sheet.png"
    make_contact_sheet(screenshot_files, contact_sheet_path)

    print("\n" + "=" * 90)
    print("                        VARIETY QA RESULTS TABLE")
    print("=" * 90)
    header = f"{'Demo Route':<28} | {'QA Result':<10} | {'Failed Checks':<32} | {'Enemy Types':<12} | {'Layout':<8} | {'Objective'}"
    print(header)
    print("-" * 110)
    for r in results:
        t = r["target"]
        assert isinstance(t, dict)
        failed_list = r["failed"]
        assert isinstance(failed_list, list)
        failed_str = ", ".join(failed_list) if failed_list else "None"
        res_str = f"{r['passed']}/{r['total']}"
        route = str(t["route"])
        enemy_types = str(t["enemy_types"])
        layout = str(t["layout"])
        objective = str(t["objective"])
        print(f"{route:<28} | {res_str:<10} | {failed_str:<32} | {enemy_types:<12} | {layout:<8} | {objective}")
    print("=" * 90)


if __name__ == "__main__":
    main()
