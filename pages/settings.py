import streamlit as st

from core.session_state import current_user, is_authenticated
from models.model_registry import get_model_status
from services.notification_service import list_notifications, mark_all_read
from ui.components import info_card, status_badge
from ui.theme import render_page_hero, theme_toggle_control


def render() -> None:
    render_page_hero("Settings", "Configure analysis thresholds, reporting, appearance, and model integration")
    settings = st.session_state.settings

    st.subheader("Appearance")
    theme_toggle_control()

    st.subheader("Analysis")
    settings["confidence_threshold"] = st.slider(
        "Confidence threshold", 0.0, 1.0, float(settings["confidence_threshold"])
    )
    settings["show_overlays"] = st.toggle("Show detection overlays by default", value=settings["show_overlays"])
    settings["enable_gpu"] = st.toggle("Prefer GPU (when model weights available)", value=settings["enable_gpu"])

    st.subheader("Report Defaults")
    settings["report_physician"] = st.text_input("Default physician", value=settings["report_physician"])
    settings["report_institution"] = st.text_input("Default institution", value=settings["report_institution"])

    st.subheader("Notifications")
    settings["email_notifications"] = st.toggle("Enable in-app notifications", value=settings.get("email_notifications", True))
    if is_authenticated():
        user = current_user()
        notes = list_notifications(user["id"])
        st.caption(f"{len(notes)} notifications on file.")
        if notes and st.button("Mark all as read"):
            mark_all_read(user["id"])
            st.rerun()

    st.subheader("Model Registry")
    st.caption("Honest status of every model integration point — no result on this page is fabricated.")
    for model in get_model_status():
        kind = {"loaded": "success", "placeholder": "warning", "unavailable": "muted"}[model.status.value]
        st.markdown(f"**{model.name}**")
        status_badge(model.status.value.upper(), kind)
        info_card("Details", f"{model.message}\n\nPath: `{model.path}`")

    if st.button("Reset Analysis Data", type="secondary"):
        from core.session_state import reset_analysis
        reset_analysis()
        st.success("Analysis outputs cleared.")
