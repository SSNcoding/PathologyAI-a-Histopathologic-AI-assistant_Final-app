"""Simple in-app notifications (SQLite-backed)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.database import get_connection, row_to_dict


def create_notification(user_id: int, title: str, body: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, is_read, created_at) VALUES (?, ?, ?, 0, ?)",
            (user_id, title, body, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def list_notifications(user_id: int, unread_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM notifications WHERE user_id = ?"
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY created_at DESC LIMIT 50"
    with get_connection() as conn:
        rows = conn.execute(query, (user_id,)).fetchall()
    return [row_to_dict(r) for r in rows]


def mark_all_read(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
