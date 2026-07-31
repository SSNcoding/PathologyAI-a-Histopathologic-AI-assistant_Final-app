"""Audit Log — administrator-only view of services/audit_service.py's
persisted event trail (logins, saved analyses, status changes, deletions).
Gated by core/permissions.py's 'view_audit_log' action; app_create.py also
excludes this page from the nav entirely for non-administrators, so this
check is a second layer, not the only one."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.permissions import can
from core.session_state import current_user
from services.audit_service import list_recent
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Audit Log", "Who did what, and when")
    user = current_user()
    if not user or not can(user.get("role"), "view_audit_log"):
        st.error("This page is restricted to administrators.")
        return

    limit = st.slider("Events to show", 20, 500, 100, step=20)
    events = list_recent(limit=limit)
    if not events:
        st.info("No audit events recorded yet.")
        return

    df = pd.DataFrame(events)[["created_at", "username", "action", "detail"]]
    df.columns = ["When (UTC)", "User", "Action", "Detail"]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(
        "This is a straightforward event log for accountability — it is not a "
        "compliance-grade (e.g. HIPAA/SOC2) audit system. See README for the "
        "production auth/security upgrade path."
    )
