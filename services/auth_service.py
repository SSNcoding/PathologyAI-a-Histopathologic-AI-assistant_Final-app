"""Registration / login backed by SQLite (db/database.py) + PBKDF2 hashing
(core/security.py). Prototype-grade auth: adequate for a demo/research
deployment, not a HIPAA-compliant identity system. See README for the
production upgrade path (proper session/JWT management, MFA, audit log)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.security import hash_password, verify_password
from db.database import get_connection, init_db, row_to_dict

init_db()


def register_user(
    username: str,
    email: str,
    password: str,
    full_name: str = "",
    institution: str = "",
    role: str = "pathologist",
) -> tuple[bool, str]:
    if not username or not email or not password:
        return False, "Username, email, and password are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
        ).fetchone()
        if existing:
            return False, "A user with that username or email already exists."
        conn.execute(
            """INSERT INTO users (username, email, password_hash, full_name, role, institution, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (username, email, hash_password(password), full_name, role, institution,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return True, "Account created — you can now log in."


def authenticate_user(username_or_email: str, password: str) -> tuple[dict[str, Any] | None, str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username_or_email, username_or_email),
        ).fetchone()
    user = row_to_dict(row)
    if not user:
        return None, "No account found with that username/email."
    if not verify_password(password, user["password_hash"]):
        return None, "Incorrect password."
    user.pop("password_hash", None)
    return user, "Welcome back."


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    user = row_to_dict(row)
    if user:
        user.pop("password_hash", None)
    return user
