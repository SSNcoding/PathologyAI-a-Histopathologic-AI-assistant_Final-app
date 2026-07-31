"""Tests for services/oauth_service.py's scaffold — mainly that it stays
inert without configuration (the important safety property here) and that
account provisioning validates its input."""

from __future__ import annotations

import pytest

import services.oauth_service as oauth_service


def test_oauth_disabled_by_default_in_test_env():
    # conftest.py doesn't set any PATHOLOGYAI_OAUTH_* vars, so this should be False.
    assert oauth_service.is_oauth_enabled() is False


def test_provision_local_account_requires_email():
    with pytest.raises(ValueError):
        oauth_service.provision_local_account({"name": "No Email User"})


def test_provision_local_account_creates_then_reuses_account():
    from db.database import init_db

    init_db()
    userinfo = {"email": "oauth-test-user@example.com", "name": "OAuth Test User"}
    first = oauth_service.provision_local_account(userinfo)
    assert first["email"] == "oauth-test-user@example.com"
    assert "password_hash" not in first

    second = oauth_service.provision_local_account(userinfo)
    assert second["id"] == first["id"]
