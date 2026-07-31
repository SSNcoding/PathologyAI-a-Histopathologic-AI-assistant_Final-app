"""Pytest configuration.

Runs before any test_*.py module is collected/imported (pytest loads
conftest.py first), which matters here because several app modules touch the
database at import time (e.g. services/auth_service.py calls init_db() as
soon as it's imported). Without this, running the test suite would create/
modify the real dev database at output/data/pathologyai.db. Redirecting
PATHOLOGYAI_DB_PATH to an isolated temp file before anything else imports
keeps tests from touching real data.

NOTE: test files live at the project root (test_*.py) rather than in a
tests/ package — a deliberate choice made while this repo's directory
creation was unavailable in the environment this was written in. Feel free
to move them into tests/ later; pytest will find them either way.
"""

from __future__ import annotations

import os
import tempfile

_tmp_db = tempfile.NamedTemporaryFile(prefix="pathologyai_test_", suffix=".db", delete=False)
_tmp_db.close()
os.environ.setdefault("PATHOLOGYAI_DB_PATH", _tmp_db.name)
os.environ.setdefault("PATHOLOGYAI_SECRET_KEY", "test-secret-key-not-for-production-use")
