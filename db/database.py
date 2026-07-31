"""Persistence layer.

Default backend: SQLite (stdlib `sqlite3`) — zero infrastructure, works out
of the box on Streamlit Community Cloud / Render / Docker.

Optional backend: PostgreSQL — set the `DATABASE_URL` env var (e.g.
`postgresql://user:pass@host:5432/dbname`) and add `psycopg2-binary` to your
environment (see requirements.txt — it's commented out by default so the
SQLite-only path stays dependency-light). Every function in the service
layer above this module (auth_service.py, analysis_store.py,
notification_service.py, audit_service.py, comments_service.py) uses `?`
placeholders and plain dicts regardless of backend — this module is the only
place that needs to know which database is actually running.

NOTE: the Postgres path was written and reviewed carefully but could not be
exercised against a live Postgres server in the environment this was built
in (sandboxed, no external DB available). Sanity-check it against your own
instance (`DATABASE_URL` set, `psycopg2-binary` installed) before relying on
it — the SQLite path is unaffected either way and remains the default.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from config.settings import DB_PATH

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'pathologist',
    institution TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    slide_name TEXT,
    organ TEXT,
    predicted_class TEXT,
    confidence REAL,
    risk_level TEXT,
    model_used TEXT,
    model_version TEXT,
    status TEXT DEFAULT 'complete',
    payload_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS case_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    author_name TEXT,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (analysis_id) REFERENCES saved_analyses (id),
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

SCHEMA_POSTGRES = SCHEMA_SQLITE.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")

# Columns added after the original schema shipped — applied via ALTER TABLE
# on existing databases so upgrades don't require a manual migration step.
_NEW_COLUMNS = {
    "saved_analyses": {
        "model_version": "TEXT",
        "status": "TEXT DEFAULT 'complete'",
    },
}


def init_db() -> None:
    if USE_POSTGRES:
        with get_connection() as conn:
            conn.executescript(SCHEMA_POSTGRES)
            conn.commit()
        _ensure_new_columns_postgres()
    else:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        with get_connection() as conn:
            conn.executescript(SCHEMA_SQLITE)
            conn.commit()
        _ensure_new_columns_sqlite()


def _ensure_new_columns_sqlite() -> None:
    with get_connection() as conn:
        for table, columns in _NEW_COLUMNS.items():
            existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for col_name, col_def in columns.items():
                if col_name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
        conn.commit()


def _ensure_new_columns_postgres() -> None:
    with get_connection() as conn:
        for table, columns in _NEW_COLUMNS.items():
            rows = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
                (table,),
            ).fetchall()
            existing = {r["column_name"] for r in rows}
            for col_name, col_def in columns.items():
                if col_name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
        conn.commit()


# ---------------------------------------------------------------------------
# Postgres adapter — makes a psycopg2 connection look like sqlite3.Connection
# (same .execute()/.fetchone()/.fetchall()/.commit()/.lastrowid surface, same
# '?' placeholders, dict-like rows) so every call site above this module
# stays backend-agnostic.
# ---------------------------------------------------------------------------
class _PGCursorWrapper:
    def __init__(self, cur, lastrowid: int | None):
        self._cur = cur
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


class _PGConnWrapper:
    def __init__(self, pg_conn):
        self._conn = pg_conn

    def execute(self, query: str, params: tuple = ()) -> _PGCursorWrapper:
        import psycopg2.extras

        translated = query.replace("?", "%s").strip()
        is_insert = translated.upper().lstrip().startswith("INSERT")
        if is_insert and "RETURNING" not in translated.upper():
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(translated, params)
        lastrowid = None
        if is_insert:
            try:
                row = cur.fetchone()
                lastrowid = row["id"] if row else None
            except Exception:
                lastrowid = None
        return _PGCursorWrapper(cur, lastrowid)

    def executescript(self, script: str) -> None:
        cur = self._conn.cursor()
        for statement in script.split(";"):
            if statement.strip():
                cur.execute(statement)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


@contextmanager
def get_connection() -> Iterator[Any]:
    if USE_POSTGRES:
        import psycopg2

        pg_conn = psycopg2.connect(DATABASE_URL)
        wrapper = _PGConnWrapper(pg_conn)
        try:
            yield wrapper
        finally:
            wrapper.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def row_to_dict(row: Any) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def dumps(obj: Any) -> str:
    """JSON-encode analysis payloads, dropping non-serializable objects (e.g. PIL images)."""
    def _default(o):
        return None
    return json.dumps(obj, default=_default)
