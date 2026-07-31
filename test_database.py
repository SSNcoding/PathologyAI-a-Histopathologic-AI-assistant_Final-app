"""Tests for db/database.py and the service layer built on it (auth, saved
analyses, audit log, comments). Runs against an isolated temp SQLite file —
see conftest.py, which redirects PATHOLOGYAI_DB_PATH before any of this
imports app code, so this never touches the real dev database."""

from __future__ import annotations

from db.database import init_db
from services.analysis_store import get_analysis, list_analyses, save_analysis, update_status
from services.audit_service import list_recent, log_action
from services.auth_service import authenticate_user, register_user
from services.comments_service import add_comment, list_comments


def setup_module(_module):
    init_db()


def test_register_and_authenticate_round_trip():
    ok, message = register_user("testuser1", "testuser1@example.com", "password123", role="researcher")
    assert ok, message
    user, message = authenticate_user("testuser1", "password123")
    assert user is not None
    assert user["username"] == "testuser1"
    assert user["role"] == "researcher"
    assert "password_hash" not in user


def test_register_rejects_short_password():
    ok, message = register_user("testuser2", "testuser2@example.com", "short")
    assert not ok
    assert "6 characters" in message


def test_register_rejects_duplicate_username():
    register_user("dupeuser", "dupe1@example.com", "password123")
    ok, _ = register_user("dupeuser", "dupe2@example.com", "password123")
    assert not ok


def test_authenticate_wrong_password_fails():
    register_user("wrongpwuser", "wrongpw@example.com", "password123")
    user, _ = authenticate_user("wrongpwuser", "not-the-password")
    assert user is None


def test_authenticate_unknown_user_fails():
    user, message = authenticate_user("nobody-registered-with-this-name", "whatever")
    assert user is None
    assert "No account" in message


def test_save_and_fetch_and_update_analysis_status():
    register_user("analysisuser", "analysisuser@example.com", "password123")
    user, _ = authenticate_user("analysisuser", "password123")
    result = {
        "findings": [{"label": "Benign", "confidence": 0.9}],
        "organ": "breast",
        "confidence": 0.9,
        "risk_level": "low",
        "architecture": "Classical CV Heuristic (no trained weights)",
        "model_version": "heuristic-cv-v1",
        "slide_name": "test_slide.png",
    }
    analysis_id = save_analysis(user["id"], result, status="pending")
    assert analysis_id > 0

    fetched = get_analysis(analysis_id, user["id"])
    assert fetched is not None
    assert fetched["predicted_class"] == "Benign"
    assert fetched["status"] == "pending"
    assert fetched["model_version"] == "heuristic-cv-v1"

    update_status(analysis_id, user["id"], "complete")
    fetched_again = get_analysis(analysis_id, user["id"])
    assert fetched_again["status"] == "complete"

    all_analyses = list_analyses(user["id"])
    assert any(a["id"] == analysis_id for a in all_analyses)


def test_get_analysis_scoped_to_owning_user():
    register_user("owneruser", "owneruser@example.com", "password123")
    register_user("otheruser", "otheruser@example.com", "password123")
    owner, _ = authenticate_user("owneruser", "password123")
    other, _ = authenticate_user("otheruser", "password123")

    analysis_id = save_analysis(owner["id"], {"findings": [{"label": "Benign", "confidence": 0.5}], "slide_name": "x.png"})
    assert get_analysis(analysis_id, owner["id"]) is not None
    assert get_analysis(analysis_id, other["id"]) is None


def test_comments_round_trip():
    register_user("commentuser", "commentuser@example.com", "password123")
    user, _ = authenticate_user("commentuser", "password123")
    analysis_id = save_analysis(user["id"], {"findings": [{"label": "Benign", "confidence": 0.5}], "slide_name": "c.png"})

    assert list_comments(analysis_id) == []
    add_comment(analysis_id, user, "Looks fine to me.")
    comments = list_comments(analysis_id)
    assert len(comments) == 1
    assert comments[0]["body"] == "Looks fine to me."


def test_add_comment_ignores_blank_body():
    register_user("blankcommentuser", "blankcommentuser@example.com", "password123")
    user, _ = authenticate_user("blankcommentuser", "password123")
    analysis_id = save_analysis(user["id"], {"findings": [{"label": "Benign", "confidence": 0.5}], "slide_name": "b.png"})
    add_comment(analysis_id, user, "   ")
    assert list_comments(analysis_id) == []


def test_audit_log_records_actions():
    register_user("audituser", "audituser@example.com", "password123")
    user, _ = authenticate_user("audituser", "password123")
    log_action(user, "test_action", "unit test detail")
    recent = list_recent(limit=10, user_id=user["id"])
    assert any(e["action"] == "test_action" for e in recent)


def test_audit_log_accepts_anonymous_actions():
    log_action(None, "anonymous_action", "no user attached")
    recent = list_recent(limit=200)
    assert any(e["action"] == "anonymous_action" and e["username"] == "anonymous" for e in recent)
