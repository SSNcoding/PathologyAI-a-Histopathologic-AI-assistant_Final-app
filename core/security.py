"""Password hashing helpers (stdlib-only, no extra dependency).

Uses PBKDF2-HMAC-SHA256 with a per-user random salt. This is adequate for a
research/prototype login system. For a real production deployment, swap in
a maintained library (e.g. argon2-cffi) and move secrets to a proper vault.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets

_ITERATIONS = 260_000
_ALGO = "sha256"


def hash_password(password: str) -> str:
    """Return 'salt$hash' hex string."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest_hex = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(_ALGO, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return hmac.compare_digest(candidate.hex(), digest_hex)


def generate_token(nbytes: int = 24) -> str:
    return secrets.token_urlsafe(nbytes)
