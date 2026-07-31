"""Case comments — lets a second reviewer (or the same pathologist later)
leave notes on a saved analysis. SQLite/Postgres-backed via db/database.py."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.database import get_connection, row_to_dict


def add_comment(analysis_id: int, user: dict[str, Any], body: str) -> None:
    if not body or not body.strip():
        return
    author_name = user.get("full_name") or user.get("username") or "Unknown"
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO case_comments (analysis_id, user_id, author_name, body, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (analysis_id, user.get("id"), author_name, body.strip(), datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def list_comments(analysis_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM case_comments WHERE analysis_id = ? ORDER BY created_at ASC",
            (analysis_id,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


def comment_count(analysis_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM case_comments WHERE analysis_id = ?", (analysis_id,)
        ).fetchone()
    return row_to_dict(row)["n"] if row else 0
