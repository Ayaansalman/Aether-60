"""
SQLite Job Store for AETHER Game Generation Pipeline.
Conforms to Sections 4.4, 4.5, and 6 of the AETHER Engineering Specification.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_db_path() -> Path:
    """Resolves the SQLite database path."""
    env_path = os.getenv("AETHER_DB_PATH")
    if env_path:
        path = Path(env_path)
    else:
        base_dir = Path(__file__).resolve().parent.parent
        path = base_dir / "data" / "app.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Creates a connection with row factory and busy timeout."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(str(target_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_job_store(db_path: Optional[Path] = None) -> None:
    """Initializes the games table in SQLite."""
    with get_connection(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 1,
                max_attempts INTEGER NOT NULL DEFAULT 3,
                model_id TEXT DEFAULT '',
                prompt_version TEXT DEFAULT '1.0',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                error_code TEXT,
                artifact_paths TEXT DEFAULT '[]',
                limitations TEXT DEFAULT '[]',
                qa_summary TEXT DEFAULT NULL,
                game_url TEXT DEFAULT NULL,
                spec_json TEXT DEFAULT NULL,
                latest_qa_json TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_status ON games(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_created ON games(created_at)")


def create_job(
    game_id: str,
    prompt: str,
    model_id: str = "",
    prompt_version: str = "1.0",
    max_attempts: int = 3,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Persists a new job before processing begins."""
    init_job_store(db_path)
    now = datetime.now(timezone.utc).isoformat()
    clean_prompt = prompt.strip()
    status = "QUEUED"
    stage = "QUEUED"

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO games (
                game_id, prompt, status, stage, attempt, max_attempts,
                model_id, prompt_version, created_at, updated_at,
                artifact_paths, limitations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                clean_prompt,
                status,
                stage,
                1,
                max_attempts,
                model_id,
                prompt_version,
                now,
                now,
                json.dumps([]),
                json.dumps([]),
            ),
        )

    return get_job(game_id, db_path=db_path)  # type: ignore


def get_job(game_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single job by its UUID string."""
    init_job_store(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def update_job(
    game_id: str,
    db_path: Optional[Path] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Updates fields on an existing job and sets updated_at."""
    init_job_store(db_path)
    if not kwargs:
        return get_job(game_id, db_path)

    now = datetime.now(timezone.utc).isoformat()
    kwargs["updated_at"] = now

    # Serialize JSON fields if dict or list
    for key in ["artifact_paths", "limitations", "qa_summary"]:
        if key in kwargs and isinstance(kwargs[key], (list, dict)):
            kwargs[key] = json.dumps(kwargs[key])

    set_clauses = [f"{k} = ?" for k in kwargs.keys()]
    values = list(kwargs.values()) + [game_id]

    with get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE games SET {', '.join(set_clauses)} WHERE game_id = ?",
            values,
        )

    return get_job(game_id, db_path)


def list_jobs(limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Lists recent jobs ordered by created_at descending."""
    init_job_store(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM games ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def get_next_queued_job(db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Gets the oldest QUEUED job for FIFO execution."""
    init_job_store(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM games WHERE status = 'QUEUED' AND prompt_version != '2.0' ORDER BY created_at ASC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_dict(row)


def mark_interrupted_jobs_on_startup(db_path: Optional[Path] = None) -> List[str]:
    """
    On system boot, marks all non-terminal jobs as FAILED (interrupted by restart).
    Terminal statuses: READY, READY_WITH_WARNINGS, FAILED.
    """
    init_job_store(db_path)
    now = datetime.now(timezone.utc).isoformat()
    interrupted_ids: List[str] = []

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT game_id FROM games
            WHERE status NOT IN ('READY', 'READY_WITH_WARNINGS', 'FAILED')
            """
        )
        interrupted_ids = [row["game_id"] for row in cursor.fetchall()]

        if interrupted_ids:
            conn.execute(
                """
                UPDATE games
                SET status = 'FAILED',
                    stage = 'INTERNAL_ERROR',
                    error_code = 'INTERNAL_ERROR',
                    updated_at = ?
                WHERE status NOT IN ('READY', 'READY_WITH_WARNINGS', 'FAILED')
                """,
                (now,),
            )

    return interrupted_ids


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a sqlite3.Row into a structured dictionary with JSON deserialization."""
    d = dict(row)
    for field_name in ["artifact_paths", "limitations"]:
        if d.get(field_name):
            try:
                d[field_name] = json.loads(d[field_name])
            except Exception:
                d[field_name] = []
        else:
            d[field_name] = []

    if d.get("qa_summary"):
        try:
            d["qa_summary"] = json.loads(d["qa_summary"])
        except Exception:
            d["qa_summary"] = None

    return d
