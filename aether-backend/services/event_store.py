"""
SQLite Event Store for AETHER Lifecycle State Tracking.
Conforms to Sections 4.4, 4.5, and 6 of the AETHER Engineering Specification.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.job_store import get_connection, get_db_path


def init_event_store(db_path: Optional[Path] = None) -> None:
    """Initializes the events table in SQLite."""
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                stage TEXT NOT NULL,
                result TEXT NOT NULL,
                detail TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 1,
                rationale TEXT DEFAULT NULL,
                diff TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_game ON events(game_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")


def add_event(
    game_id: str,
    stage: str,
    result: str,
    detail: str,
    attempt: int = 1,
    rationale: Optional[str] = None,
    diff: Optional[Dict[str, Any]] = None,
    ts: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Appends an immutable lifecycle event to the event store."""
    init_event_store(db_path)
    now = ts or datetime.now(timezone.utc).isoformat()
    diff_json = json.dumps(diff) if diff is not None else None

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (
                game_id, ts, stage, result, detail, attempt, rationale, diff
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (game_id, now, stage, result, detail, attempt, rationale, diff_json),
        )
        event_id = cursor.lastrowid

    return {
        "id": event_id,
        "game_id": game_id,
        "ts": now,
        "stage": stage,
        "result": result,
        "detail": detail,
        "attempt": attempt,
        "rationale": rationale,
        "diff": diff,
    }


def get_events(game_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieves all events for a given game_id ordered chronologically."""
    init_event_store(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM events WHERE game_id = ? ORDER BY id ASC",
            (game_id,),
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("diff"):
                try:
                    d["diff"] = json.loads(d["diff"])
                except Exception:
                    pass
            result.append(d)
        return result
