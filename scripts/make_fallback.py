#!/usr/bin/env python3
"""
AETHER Offline Fallback Generator (Phase 6).
Bundles 3 real evaluation artifacts into static offline demo assets:
1. Spooky Collect Game (Run A, p01: gemini-3.5-flash-lite)
2. Pirate Survive Game (Run A, p03: gemini-3.5-flash-lite)
3. Repaired Too-Hard Game (Run A2, s01 real repair: gemini-3.5-flash-lite)

Saves assets to aether-frontend/public/fallback/<name>/ and generates
aether-frontend/src/game/savedDemos.ts for zero-network offline loading.
"""

import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "aether-backend"
FRONTEND_DIR = ROOT_DIR / "aether-frontend"
PUBLIC_FALLBACK_DIR = FRONTEND_DIR / "public" / "fallback"
SAVED_DEMOS_TS = FRONTEND_DIR / "src" / "game" / "savedDemos.ts"
DB_PATH = BACKEND_DIR / "data" / "app.db"
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"


class DemoConfig(TypedDict, total=False):
    id: str
    slug: str
    title: str
    prompt: str
    source_game_id: str
    model_label: str
    provider: str
    is_repaired: bool
    spec_file: str
    initial_spec_file: Optional[str]
    qa_file: str
    initial_qa_file: Optional[str]
    screenshot_file: str


# Target demo configurations matching real benchmark runs
DEMO_CONFIGS: List[DemoConfig] = [
    {
        "id": "fallback-spooky",
        "slug": "spooky",
        "title": "Spooky Crystal Dungeon",
        "prompt": "a spooky wizard collecting glowing crystals in a dark dungeon while ghosts chase me",
        "source_game_id": "699db4c8-4d87-44af-a287-a34c57fbe7a4",
        "model_label": "gemini-3.5-flash-lite (Run A)",
        "provider": "openai_compat",
        "is_repaired": False,
        "spec_file": "game_ir_v1.json",
        "qa_file": "qa_report_attempt_1.json",
        "screenshot_file": "play_699db4c8-4d87-44af-a287-a34c57fbe7a4.png",
    },
    {
        "id": "fallback-pirate",
        "slug": "pirate",
        "title": "Pirate Cove Treasure Hunt",
        "prompt": "a pirate captain collecting gold treasure chests while rival skeleton ships pursue",
        "source_game_id": "fd80dc0f-68bb-4936-b839-c06bb99d86c7",
        "model_label": "gemini-3.5-flash-lite (Run A)",
        "provider": "openai_compat",
        "is_repaired": False,
        "spec_file": "game_ir_v1.json",
        "qa_file": "qa_report_attempt_1.json",
        "screenshot_file": "play_fd80dc0f-68bb-4936-b839-c06bb99d86c7.png",
    },
    {
        "id": "fallback-repaired",
        "slug": "repaired",
        "title": "Shadow Pursuit (Repaired)",
        "prompt": "an impossible bullet-hell arena with 50 pursuers moving twice the player's speed, zero recovery, and 1 hit point",
        "source_game_id": "54a6fdce-eea5-446f-a47f-66a844259b09",
        "model_label": "gemini-3.5-flash-lite (Run A2 Real Repair)",
        "provider": "openai_compat",
        "is_repaired": True,
        "spec_file": "game_ir_v2.json",
        "initial_spec_file": "game_ir_v1.json",
        "qa_file": "qa_report_attempt_2.json",
        "initial_qa_file": "qa_report_attempt_1.json",
        "screenshot_file": "play_54a6fdce-eea5-446f-a47f-66a844259b09.png",
    },
]


def fetch_events_for_game(conn: sqlite3.Connection, game_id: str) -> List[Dict[str, Any]]:
    c = conn.cursor()
    events = []
    for r in c.execute(
        "SELECT id, ts, stage, result, detail, attempt, rationale, diff FROM events WHERE game_id = ? ORDER BY id",
        (game_id,),
    ):
        diff_obj = None
        if r[7]:
            try:
                diff_obj = json.loads(r[7])
            except Exception:
                pass
        events.append({
            "id": r[0],
            "ts": r[1],
            "timestamp": r[1],
            "stage": r[2],
            "result": r[3],
            "detail": r[4] or "",
            "message": r[4] or "",
            "attempt": r[5],
            "rationale": r[6],
            "diff": diff_obj,
        })
    return events


def fetch_game_row(conn: sqlite3.Connection, game_id: str) -> Dict[str, Any]:
    c = conn.cursor()
    c.execute(
        "SELECT status, error_code, limitations, created_at FROM games WHERE game_id = ?",
        (game_id,),
    )
    row = c.fetchone()
    if not row:
        return {}
    limitations = []
    if row[2]:
        try:
            limitations = json.loads(row[2])
        except Exception:
            limitations = [row[2]]
    return {
        "status": row[0],
        "error_code": row[1],
        "limitations": limitations,
        "created_at": row[3],
    }


def make_fallbacks():
    print(f"[make_fallback] Initializing fallback bundle in {PUBLIC_FALLBACK_DIR}...")
    PUBLIC_FALLBACK_DIR.mkdir(parents=True, exist_ok=True)

    conn = None
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)

    bundled_demos = []

    for cfg in DEMO_CONFIGS:
        slug = cfg["slug"]
        gid = cfg["source_game_id"]
        target_dir = PUBLIC_FALLBACK_DIR / slug
        target_dir.mkdir(parents=True, exist_ok=True)

        source_dir = ARTIFACTS_DIR / gid
        if not source_dir.exists():
            print(f"[WARNING] Artifact dir not found for {slug}: {source_dir}")
            continue

        # 1. Spec
        spec_path = source_dir / cfg["spec_file"]
        spec_data = {}
        if spec_path.exists():
            with open(spec_path, "r", encoding="utf-8") as f:
                spec_data = json.load(f)
            shutil.copyfile(spec_path, target_dir / "spec.json")

        initial_spec_data = None
        initial_spec_file = cfg.get("initial_spec_file")
        if initial_spec_file:
            init_path = source_dir / initial_spec_file
            if init_path.exists():
                with open(init_path, "r", encoding="utf-8") as f:
                    initial_spec_data = json.load(f)
                shutil.copyfile(init_path, target_dir / "spec_v1.json")

        # 2. QA Report
        qa_path = source_dir / cfg["qa_file"]
        qa_data = {}
        if qa_path.exists():
            with open(qa_path, "r", encoding="utf-8") as f:
                qa_data = json.load(f)
            shutil.copyfile(qa_path, target_dir / "qa.json")

        # 3. Screenshot
        ss_path = source_dir / cfg["screenshot_file"]
        if ss_path.exists():
            shutil.copyfile(ss_path, target_dir / "screenshot.png")

        # 4. Events & Metadata from DB
        events = []
        game_meta = {}
        if conn:
            events = fetch_events_for_game(conn, gid)
            game_meta = fetch_game_row(conn, gid)

        with open(target_dir / "events.json", "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)

        # Extract repair rationale and diff if applicable
        repair_rationale = None
        repair_diff = None
        for ev in events:
            if ev.get("stage") == "REPAIRING" and ev.get("rationale"):
                repair_rationale = ev["rationale"]
                repair_diff = ev.get("diff")

        meta = {
            "id": cfg["id"],
            "slug": slug,
            "title": cfg["title"],
            "prompt": cfg["prompt"],
            "model_label": cfg["model_label"],
            "provider": cfg["provider"],
            "status": "READY",
            "is_repaired": cfg["is_repaired"],
            "limitations": game_meta.get("limitations", []),
            "repair_rationale": repair_rationale,
            "repair_diff": repair_diff,
            "source_game_id": gid,
        }

        with open(target_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        bundled_demos.append({
            **meta,
            "spec": spec_data,
            "initial_spec": initial_spec_data,
            "qa": qa_data,
            "events": events,
        })
        print(f"  [+] Bundled '{slug}' from {gid}")

    if conn:
        conn.close()

    # Write public manifest
    manifest_path = PUBLIC_FALLBACK_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump([
            {k: d[k] for k in ["id", "slug", "title", "prompt", "model_label", "provider", "is_repaired"]}
            for d in bundled_demos
        ], f, indent=2)
    print(f"[make_fallback] Wrote manifest to {manifest_path}")

    # Generate static TypeScript module for instant, 100% offline access
    SAVED_DEMOS_TS.parent.mkdir(parents=True, exist_ok=True)
    ts_content = f"""// AUTO-GENERATED by scripts/make_fallback.py. Do not edit directly.
// Offline fallback demos bundled from real evaluation artifacts.
// Loads instantly with zero network calls and backend stopped.

import type {{ GameIR }} from './gameir';
import type {{ QAReport, GameEvent }} from '../lib/mockApi';

export interface SavedDemo {{
  id: string;
  slug: string;
  title: string;
  prompt: string;
  model_label: string;
  provider: string;
  status: 'READY';
  is_repaired: boolean;
  limitations: string[];
  repair_rationale?: string | null;
  repair_diff?: {{ before?: Record<string, unknown>; after?: Record<string, unknown> }} | null;
  source_game_id: string;
  spec: GameIR;
  initial_spec?: GameIR | null;
  qa: QAReport | null;
  events: GameEvent[];
}}

export const SAVED_DEMOS: SavedDemo[] = {json.dumps(bundled_demos, indent=2)};

export function getSavedDemo(idOrSlug: string): SavedDemo | undefined {{
  return SAVED_DEMOS.find(
    (d) => d.id === idOrSlug || d.slug === idOrSlug || d.source_game_id === idOrSlug
  );
}}
"""
    with open(SAVED_DEMOS_TS, "w", encoding="utf-8") as f:
        f.write(ts_content)
    print(f"[make_fallback] Generated TypeScript bundle at {SAVED_DEMOS_TS}")


if __name__ == "__main__":
    make_fallbacks()
