"""Side-by-side comparison — two saved analyses (or one saved case vs. the
slide currently loaded) compared on the same screen. Useful for comparing a
follow-up slide against a prior one, or two model runs on the same slide."""

from __future__ import annotations

import json

import streamlit as st

from core.session_state import current_user
from services.analysis_store import list_analyses
from ui.components import metric_card, status_badge
from ui.theme import render_page_hero


def _load_payload(item: dict) -> dict:
    try:
        return json.loads(item.get("payload_json") or "{}")
    except (TypeError, ValueError):
        return {}


def _render_case_column(item: dict, payload: dict) -> None:
    st.markdown(f"#### {item['slide_name']}")
    st.caption(f"{item['organ']} · saved {item['created_at'][:19]}")
    status_badge(item["risk_level"].upper(), {"low": "success", "moderate": "warning", "high": "danger"}.get(item["risk_level"], "info"))
    status_badge(payload.get("model_mode", "—"), "warning" if payload.get("model_mode") == "HEURISTIC_PLACEHOLDER" else "success")

    m1, m2 = st.columns(2)
    m1.metric("Predicted Class", item.get("predicted_class") or "—")
    m2.metric("Confidence", f"{(item.get('confidence') or 0):.1%}")

    tumor = payload.get("tumor_metrics", {})
    quality = payload.get("quality", {})
    c1, c2 = st.columns(2)
    with c1:
        metric_card("Tumor %", f"{tumor.get('tumor_pct', '—')}")
        metric_card("Necrosis Score", f"{tumor.get('necrosis_score', '—')}/10")
    with c2:
        metric_card("Inflammation", f"{tumor.get('inflammation_score', '—')}/10")
        metric_card("Tissue Quality", f"{quality.get('label', '—')} ({quality.get('score', '—')})")

    cells = payload.get("cells", {})
    st.caption(f"Nuclei detected: {cells.get('nuclei_count', '—')} · density {cells.get('density_per_mpx', '—')}/Mpx")

    if item.get("model_version"):
        st.caption(f"Model version: `{item['model_version']}`")


def render() -> None:
    render_page_hero("Comparison", "Compare two saved cases side by side")
    user = current_user()
    if not user:
        st.warning("Please log in to compare saved cases.")
        return

    analyses = list_analyses(user["id"])
    if len(analyses) < 2:
        st.info("Save at least two analyses (Results Dashboard → Save to Profile) to compare them here.")
        return

    options = {f"#{a['id']} · {a['slide_name']} ({a['created_at'][:10]})": a for a in analyses}
    labels = list(options.keys())

    c1, c2 = st.columns(2)
    with c1:
        left_label = st.selectbox("Case A", labels, index=0, key="cmp_left")
    with c2:
        default_right = 1 if len(labels) > 1 else 0
        right_label = st.selectbox("Case B", labels, index=default_right, key="cmp_right")

    st.markdown("---")
    left_item = options[left_label]
    right_item = options[right_label]

    col_a, col_b = st.columns(2)
    with col_a:
        _render_case_column(left_item, _load_payload(left_item))
    with col_b:
        _render_case_column(right_item, _load_payload(right_item))

    if left_item["id"] == right_item["id"]:
        st.caption("Pick two different cases above to see a meaningful comparison.")
