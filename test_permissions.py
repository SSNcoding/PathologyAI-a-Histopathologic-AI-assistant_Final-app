"""Tests for core/permissions.py's role-based access control.

Policy as of this round: every registered role (pathologist / researcher /
student / administrator) sees every page and can use every feature — this
is a demo/prototype app, not a clinical deployment, so per-role gating was
removed in favor of open access. These tests lock in that "everyone gets
everything" behavior, plus the safe-by-default handling of unknown roles
and unknown actions.
"""

from __future__ import annotations

from core.permissions import can, pages_for_role, role_label

ALL_ROLES = ("pathologist", "researcher", "student", "administrator")

ALL_PAGES = {
    "Dashboard", "Upload", "AI Analysis", "Results Dashboard", "Explainable AI",
    "Tissue Detection", "Cell Detection", "Statistics", "Assistant",
    "Slide Inventory", "Comparison", "Profile", "Settings",
    "Scan Queue", "Patient Report", "Audit Log",
}


def test_all_known_roles_have_nonempty_page_sets():
    for role in ALL_ROLES:
        pages = pages_for_role(role)
        assert isinstance(pages, set)
        assert len(pages) > 0


def test_every_role_sees_every_page():
    for role in ALL_ROLES:
        assert pages_for_role(role) == ALL_PAGES


def test_every_role_can_run_batch_generate_reports_and_view_audit_log():
    for role in ALL_ROLES:
        assert can(role, "run_batch_analysis")
        assert can(role, "generate_patient_report")
        assert can(role, "view_audit_log")
        assert can(role, "delete_saved_analysis")


def test_unknown_role_falls_back_to_student_defaults():
    assert pages_for_role("not-a-real-role") == pages_for_role("student")
    # An unrecognized role string isn't one of the four named roles, so it
    # gets no page-level access even though pages_for_role falls back to
    # the full page set for display purposes — can() checks role membership
    # directly against each action's role set.
    assert not can("not-a-real-role", "run_batch_analysis")
    assert not can("not-a-real-role", "not-a-real-action")


def test_none_role_falls_back_to_student_defaults():
    assert pages_for_role(None) == pages_for_role("student")


def test_unknown_action_denies_every_role():
    for role in ALL_ROLES:
        assert not can(role, "not-a-real-action")


def test_role_label_returns_nonempty_string_for_every_role():
    for role in ALL_ROLES:
        label = role_label(role)
        assert isinstance(label, str) and len(label) > 0
