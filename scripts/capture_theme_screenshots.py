#!/usr/bin/env python3
"""
AETHER Visual Theme Capture & Contact Sheet Generator (Phase 6 / Part 3).
Loads all 5 visual themes in headless Chromium using Playwright:
- fantasy
- sci_fi
- pirate
- spooky
- cozy
Saves individual screenshots to artifacts/themes/ and compiles a contact sheet.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "aether-frontend"
THEMES_DIR = ROOT_DIR / "artifacts" / "themes"

THEMES = [
    {
        "id": "fantasy",
        "route": "http://localhost:5173/play/theme-fantasy?test=1",
        "label": "FANTASY: Arcane Crystal Grove",
        "filename": "theme_fantasy.png",
    },
    {
        "id": "sci_fi",
        "route": "http://localhost:5173/play/theme-sci_fi?test=1",
        "label": "SCI-FI: Cyber Void Surge",
        "filename": "theme_sci_fi.png",
    },
    {
        "id": "pirate",
        "route": "http://localhost:5173/play/theme-pirate?test=1",
        "label": "PIRATE: Treasure Cove Hunt",
        "filename": "theme_pirate.png",
    },
    {
        "id": "spooky",
        "route": "http://localhost:5173/play/theme-spooky?test=1",
        "label": "SPOOKY: Spooky Crypt Haunt",
        "filename": "theme_spooky.png",
    },
    {
        "id": "cozy",
        "route": "http://localhost:5173/play/theme-cozy?test=1",
        "label": "COZY: Enchanted Meadow Gathering",
        "filename": "theme_cozy.png",
    },
]


def is_server_listening(port: int = 5173) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=1.0):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def ensure_vite_server():
    if is_server_listening(5173):
        return None

    print("[theme_capture] Starting Vite dev server on port 5173...")
    env = os.environ.copy()
    nodejs_dir = r"C:\Program Files\nodejs"
    if nodejs_dir not in env.get("PATH", ""):
        env["PATH"] = f"{nodejs_dir};" + env.get("PATH", "")

    node_bin = Path(r"C:\Program Files\nodejs\node.exe")
    vite_bin = FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    if node_bin.exists() and vite_bin.exists():
        cmd = [str(node_bin), str(vite_bin), "--host", "localhost", "--port", "5173"]
    else:
        npm_cmd = str(Path(r"C:\Program Files\nodejs\npm.cmd")) if Path(r"C:\Program Files\nodejs\npm.cmd").exists() else "npm"
        cmd = [npm_cmd, "run", "dev"]

    proc = subprocess.Popen(
        cmd,
        cwd=str(FRONTEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(25):
        if is_server_listening(5173):
            print("  [+] Vite server ready.")
            return proc
        time.sleep(1)

    raise RuntimeError("Vite dev server failed to start within 25 seconds.")


def capture_screenshots():
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    vite_proc = ensure_vite_server()

    captured_paths = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})

            for theme in THEMES:
                page = context.new_page()
                print(f"[theme_capture] Capturing '{theme['id']}' from {theme['route']}...")

                page.goto(theme["route"], timeout=30000)
                page.wait_for_selector("canvas", timeout=15000)

                # Wait for game to initialize and advance at least 15 ticks
                page.wait_for_function(
                    "() => window.__AETHER_GAME__ && window.__AETHER_GAME__.ready && window.__AETHER_GAME__.tick >= 15",
                    timeout=15000,
                )
                time.sleep(0.5)

                # Target canvas element specifically
                canvas_elem = page.query_selector("canvas")
                out_path = THEMES_DIR / theme["filename"]
                if canvas_elem:
                    canvas_elem.screenshot(path=str(out_path))
                else:
                    page.screenshot(path=str(out_path))

                print(f"  [+] Saved {out_path.name}")
                captured_paths.append((theme, out_path))
                page.close()

            browser.close()
    finally:
        if vite_proc:
            print("[theme_capture] Stopping spawned Vite server...")
            vite_proc.terminate()
            vite_proc.wait()

    return captured_paths


def build_contact_sheet(captured_paths):
    print("[theme_capture] Compiling contact sheet...")
    # Contact sheet: 3 columns x 2 rows
    # Cell size: 400x300 plus 40px label banner
    cell_w = 400
    cell_h = 300
    label_h = 36
    total_cell_h = cell_h + label_h

    cols = 3
    rows = 2
    padding = 16

    sheet_w = cols * cell_w + (cols + 1) * padding
    sheet_h = rows * total_cell_h + (rows + 1) * padding + 50  # 50px header

    sheet = Image.new("RGB", (sheet_w, sheet_h), color=(10, 10, 18))
    draw = ImageDraw.Draw(sheet)

    # Header title
    draw.text((padding, 16), "AETHER THEME MATRIX: PALETTES & PRIMITIVE SHAPES", fill=(255, 255, 255))

    for idx, (theme, img_path) in enumerate(captured_paths):
        c = idx % cols
        r = idx // cols

        x = padding + c * (cell_w + padding)
        y = 50 + padding + r * (total_cell_h + padding)

        # Draw cell container background
        draw.rectangle([x, y, x + cell_w, y + total_cell_h], fill=(20, 22, 34), outline=(60, 65, 90))

        # Draw label
        draw.text((x + 10, y + 10), theme["label"], fill=(220, 230, 250))

        # Paste resized screenshot
        if img_path.exists():
            with Image.open(img_path) as im:
                im_resized = im.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
                sheet.paste(im_resized, (x, y + label_h))

    contact_path = THEMES_DIR / "contact_sheet.png"
    sheet.save(contact_path)
    print(f"[theme_capture] Contact sheet saved to {contact_path}")


def main():
    captured = capture_screenshots()
    build_contact_sheet(captured)
    print("\n[theme_capture] Theme capture completed successfully.")


if __name__ == "__main__":
    main()
