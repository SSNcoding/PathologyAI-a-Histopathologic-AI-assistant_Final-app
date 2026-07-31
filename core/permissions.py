"""Role-based access control.

Registration lets a user pick a role (pathologist / researcher / student /
administrator, see app_pages/register.py). The role is still recorded and
shown as a label, but every role now sees every page and can use every
feature — this app is a demo/prototype, not a clinical deployment, so gating
advanced features behind role assignment mostly just got in the way of
trying things out. Flip ROLE_PAGES / ACTION_PERMISSIONS back to per-role
sets if this is ever wired up to real patient data and needs actual access
control.
"""

from __future__ import annotations

# Every page in the app. All roles get all of them.
_ALL_PAGES = {
    "Dashboard", "Upload", "AI Analysis", "Results Dashboard", "Explainable AI",
    "Tissue Detection", "Cell Detection", "Statistics", "ROI Annotation",
    "Slide Inventory", "Comparison", "Profile", "Settings",
    "Scan Queue", "Patient Report", "Audit Log",
}

ROLE_PAGES: dict[str, set[str]] = {
    "pathologist": _ALL_PAGES,
    "researcher": _ALL_PAGES,
    "student": _ALL_PAGES,
    "administrator": _ALL_PAGES,
}

ROLE_LABELS: dict[str, str] = {
    "pathologist": "Pathologist",
    "researcher": "Researcher",
    "student": "Student",
    "administrator": "Administrator",
}

# Fine-grained actions that don't map cleanly to "can see this whole page".
# Everyone can do everything for the same reason as ROLE_PAGES above.
_ALL_ROLES = {"pathologist", "researcher", "student", "administrator"}
ACTION_PERMISSIONS: dict[str, set[str]] = {
    "generate_patient_report": _ALL_ROLES,
    "run_batch_analysis": _ALL_ROLES,
    "view_audit_log": _ALL_ROLES,
    "delete_saved_analysis": _ALL_ROLES,
}

_DEFAULT_ROLE = "student"


def pages_for_role(role: str | None) -> set[str]:
    return ROLE_PAGES.get(role or _DEFAULT_ROLE, _ALL_PAGES)


def can(role: str | None, action: str) -> bool:
    # Unknown actions still deny-by-default (empty set) — only actions we've
    # actually named in ACTION_PERMISSIONS are opened up to every role.
    return (role or _DEFAULT_ROLE) in ACTION_PERMISSIONS.get(action, set())


def role_label(role: str | None) -> str:
    return ROLE_LABELS.get(role or _DEFAULT_ROLE, ROLE_LABELS[_DEFAULT_ROLE])
