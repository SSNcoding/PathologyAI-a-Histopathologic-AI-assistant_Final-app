"""Persistent audit log (SQLite/Postgres-backed via db/database.py).

Formalizes what used to live only in the in-memory `analysis_history`
session-state list: every significant action — login, analysis run, report
export, settings change — is written to the `audit_log` table so it survives
page reruns and, more importantly, so there's an actual accountability trail
for a clinical-adjacent tool. Not a substitute for a real compliance-grade
audit system (see README's HIPAA caveat), but a genuine persisted record
instead of nothing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.database import get_connection, row_to_dict


def log_action(user: dict[str, Any] | None, action: str, detail: str = "") -> None:
    """Record one audit event. Safe to call for anonymous/pre-login actions
    (user=None) — e.g. failed login attempts, public contact form submits."""
    user_id = user.get("id") if user else None
    username = user.get("username") if user else "anonymous"
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (user_id, username, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, action, detail, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def list_recent(limit: int = 100, user_id: int | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM audit_log"
    params: list[Any] = []
    if user_id is not None:
        query += " WHERE user_id = ?"
        params.append(user_id)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [row_to_dict(r) for r in rows]
