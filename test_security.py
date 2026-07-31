"""Tests for core/security.py's password hashing — the one place a silent
bug is both easy to introduce and hard to notice in manual testing (a broken
hash still 'looks' like it works right up until someone can't log in, or
worse, until verification always returns True)."""

from __future__ import annotations

from core.security import generate_token, hash_password, verify_password


def test_hash_password_produces_salt_and_digest():
    hashed = hash_password("correct horse battery staple")
    assert "$" in hashed
    salt, digest = hashed.split("$")
    assert len(salt) == 32  # secrets.token_hex(16) -> 32 hex chars
    assert len(digest) == 64  # sha256 digest hex-encoded


def test_hash_password_is_salted_differently_each_time():
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b


def test_verify_password_accepts_correct_password():
    hashed = hash_password("s3cret!")
    assert verify_password("s3cret!", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("s3cret!")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_empty_password_against_real_hash():
    hashed = hash_password("s3cret!")
    assert verify_password("", hashed) is False


def test_verify_password_handles_malformed_stored_hash_without_raising():
    assert verify_password("anything", "not-a-valid-hash") is False
    assert verify_password("anything", "") is False


def test_generate_token_is_url_safe_and_unique_across_calls():
    tokens = {generate_token() for _ in range(50)}
    assert len(tokens) == 50
    for t in tokens:
        assert all(c.isalnum() or c in "-_" for c in t)
