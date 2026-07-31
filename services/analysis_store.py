"""Save / search a user's past analyses (SQLite-backed)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from db.database import dumps, get_connection, row_to_dict


def save_analysis(user_id: int, result: dict[str, Any], status: str = "complete") -> int:
    top = (result.get("findings") or [{}])[0]
    payload = {k: v for k, v in result.items() if k != "heatmap"}
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO saved_analyses
               (user_id, slide_name, organ, predicted_class, confidence, risk_level,
                model_used, model_version, status, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                result.get("slide_name") or result.get("current_image_name") or "unnamed_slide",
                result.get("organ"),
                top.get("label"),
                result.get("confidence"),
                result.get("risk_level"),
                result.get("architecture"),
                result.get("model_version"),
                status,
                dumps(payload),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def list_analyses(user_id: int, search: str = "") -> list[dict[str, Any]]:
    query = "SELECT * FROM saved_analyses WHERE user_id = ?"
    params: list[Any] = [user_id]
    if search:
        query += " AND (slide_name LIKE ? OR organ LIKE ? OR predicted_class LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [row_to_dict(r) for r in rows]


def get_analysis(analysis_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM saved_analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id)
        ).fetchone()
    return row_to_dict(row)


def update_status(analysis_id: int, user_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE saved_analyses SET status = ? WHERE id = ? AND user_id = ?",
            (status, analysis_id, user_id),
        )
        conn.commit()


def delete_analysis(analysis_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM saved_analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id))
        conn.commit()
