"""Superseded by app_pages/slide_inventory.py — kept in place (not deleted)
since app_create.py no longer imports or routes to this module. Slide
Inventory keeps the exact same triage/comments/delete behavior this page
had, plus a simulated barcode + rack-position lookup layer. Safe to delete
once you're sure nothing else references it.

Original docstring, for reference: Worklist / case queue — saved analyses
as a triage queue (pending / in review / complete) instead of a flat
history list. Builds on the same saved_analyses table profile.py already
used; this page adds a status column and lets you move cases through it."""

from __future__ import annotations

import json

import streamlit as st

from core.permissions import can
from core.session_state import current_user
from core.constants import WORKLIST_STATUS_BADGE_KIND, WORKLIST_STATUS_LABELS, WORKLIST_STATUSES
from services.analysis_store import delete_analysis, list_analyses, update_status
from services.audit_service import log_action
from services.comments_service import comment_count
from ui.components import status_badge
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Worklist", "Cases as a queue — pending, in review, or complete")
    user = current_user()
    if not user:
        st.warning("Please log in to view your worklist.")
        return

    search = st.text_input("Search by slide name, organ, or predicted class", "")
    analyses = list_analyses(user["id"], search=search)

    if not analyses:
        st.info("No saved cases yet. Run an AI Analysis and click **Save to Profile** on the Results Dashboard.")
        return

    tabs = st.tabs([f"{WORKLIST_STATUS_LABELS[s]} ({sum(1 for a in analyses if (a.get('status') or 'complete') == s)})" for s in WORKLIST_STATUSES])
    for status_key, tab in zip(WORKLIST_STATUSES, tabs):
        with tab:
            bucket = [a for a in analyses if (a.get("status") or "complete") == status_key]
            if not bucket:
                st.caption("Nothing here.")
                continue
            for item in bucket:
                with st.container(border=True):
                    cols = st.columns([3, 1.3, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{item['slide_name']}** — {item['organ']}")
                        st.caption(
                            f"{item['predicted_class']} · confidence {item['confidence']:.0%} · "
                            f"{item['created_at'][:19]}"
                            + (f" · model `{item['model_version']}`" if item.get("model_version") else "")
                        )
                        n_comments = comment_count(item["id"])
                        if n_comments:
                            st.caption(f"\U0001F4AC {n_comments} comment(s)")
                    with cols[1]:
                        status_badge(item["risk_level"].upper(),
                                     {"low": "success", "moderate": "warning", "high": "danger"}.get(item["risk_level"], "info"))
                    with cols[2]:
                        new_status = st.selectbox(
                            "Status", WORKLIST_STATUSES,
                            index=WORKLIST_STATUSES.index(status_key),
                            key=f"status_{item['id']}",
                            format_func=lambda s: WORKLIST_STATUS_LABELS[s],
                            label_visibility="collapsed",
                        )
                        if new_status != status_key:
                            update_status(item["id"], user["id"], new_status)
                            log_action(user, "update_case_status", f"Case #{item['id']} -> {new_status}")
                            st.rerun()
                    with cols[3]:
                        if can(user.get("role"), "delete_saved_analysis"):
                            if st.button("Delete", key=f"del_{item['id']}"):
                                delete_analysis(item["id"], user["id"])
                                log_action(user, "delete_analysis", f"Deleted case #{item['id']}")
                                st.rerun()
                    with st.expander("Details"):
                        try:
                            payload = json.loads(item.get("payload_json") or "{}")
                        except (TypeError, ValueError):
                            payload = {}
                        tumor = payload.get("tumor_metrics", {})
                        d1, d2, d3, d4 = st.columns(4)
                        d1.metric("Tumor %", f"{tumor.get('tumor_pct', '—')}")
                        d2.metric("Necrosis", f"{tumor.get('necrosis_score', '—')}/10")
                        d3.metric("Inflammation", f"{tumor.get('inflammation_score', '—')}/10")
                        d4.metric("Model mode", payload.get("model_mode", "—"))

    st.caption(
        "Select up to two cases here to compare — the Comparison page reads from "
        "your saved analyses, not this list directly, so open it separately and pick by name."
    )
