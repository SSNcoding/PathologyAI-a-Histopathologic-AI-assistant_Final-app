"""User profile — account details, saved analyses, search."""

from __future__ import annotations

import streamlit as st

from core.permissions import can, role_label
from core.session_state import current_user
from services.analysis_store import delete_analysis, list_analyses
from ui.components import info_card, status_badge
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Profile", "Your account and saved analyses")
    user = current_user()
    if not user:
        st.warning("Please log in to view your profile.")
        return

    c1, c2 = st.columns([1, 2])
    with c1:
        info_card(
            "Account",
            f"<b>{user.get('full_name') or user['username']}</b><br>"
            f"@{user['username']}<br>{user['email']}<br>"
            f"{user.get('institution') or '—'}<br>Role: {user.get('role', 'pathologist')}",
        )
        st.caption(role_label(user.get("role")))
    with c2:
        st.subheader("Saved Analyses")
        st.caption("For a status-driven view (pending/in review/complete) with barcode lookup, see the Slide Inventory page.")
        search = st.text_input("Search by slide name, organ, or predicted class", "")
        analyses = list_analyses(user["id"], search=search)
        if not analyses:
            st.info("No saved analyses yet. Run an AI Analysis and click **Save to Profile**.")
        can_delete = can(user.get("role"), "delete_saved_analysis")
        for item in analyses:
            with st.container(border=True):
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{item['slide_name']}** — {item['organ']}")
                    st.caption(f"{item['predicted_class']} · confidence {item['confidence']:.0%} · {item['created_at'][:19]}")
                    status_badge(item["risk_level"].upper(), {"low": "success", "moderate": "warning", "high": "danger"}.get(item["risk_level"], "info"))
                with cols[1]:
                    if can_delete:
                        if st.button("Delete", key=f"del_{item['id']}"):
                            delete_analysis(item["id"], user["id"])
                            st.rerun()
                    else:
                        st.caption("Delete restricted for your role.")
