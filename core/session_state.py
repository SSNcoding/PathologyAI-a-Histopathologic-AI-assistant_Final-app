"""Initialize and manage Streamlit session state."""

from __future__ import annotations

import time

import streamlit as st

from config.settings import DEFAULT_THEME
from core.constants import AnalysisStatus

DEFAULT_STATE = {
    "initialized": True,
    # --- Auth -----------------------------------------------------------
    "auth_user": None,               # dict: id, username, email, full_name, role, institution
    "auth_error": None,
    "auth_login_at": None,           # epoch seconds, set on successful login — used for session expiry
    "public_page": "Home",           # nav choice while logged out
    # --- Theme / UI -------------------------------------------------------
    "theme": DEFAULT_THEME,          # "dark" | "light"
    "dark_preset": "Midnight",       # background choice while theme == "dark"
    "light_preset": "Cloud",         # background choice while theme == "light"
    "language": "en",                # see core/i18n.py — "en" | "es"
    "notifications_open": False,
    # --- Slide / image state ----------------------------------------------
    "current_image": None,           # PIL Image (working copy, post-edit)
    "original_image": None,          # PIL Image (untouched upload)
    "current_image_name": None,
    "current_image_array": None,     # numpy RGB
    "edit_rotation": 0,
    "edit_brightness": 1.0,
    "edit_contrast": 1.0,
    "edit_crop": None,               # (left, top, right, bottom) in %
    "upload_progress_done": False,
    "upload_quality_precheck": None,  # dict from slide_quality_precheck() — set on upload
    # --- Analysis configuration --------------------------------------------
    "selected_organ": "breast",
    "selected_architecture": "Classical CV Heuristic (no trained weights)",
    "use_ensemble": False,
    "use_tta": False,
    "batch_images": [],               # list of (name, PIL.Image)
    "roi_annotations": [],
    # --- Analysis outputs ---------------------------------------------------
    "analysis_status": AnalysisStatus.IDLE,
    "tissue_results": None,
    "cell_results": None,
    "ai_results": None,
    "heatmap_image": None,
    "gradcam_result": None,
    "analysis_history": [],          # list of dict records (in-memory, this session)
    "last_processing_time_s": None,
    "last_saved_analysis_id": None,  # id of the most recently DB-saved analysis, for the comments widget
    "comparison_analysis_ids": [],   # up to 2 saved-analysis ids picked on the Comparison page
    # --- App settings ------------------------------------------------------
    "settings": {
        "confidence_threshold": 0.65,
        "show_overlays": True,
        "enable_gpu": False,
        "report_physician": "Dr. Pathologist",
        "report_institution": "PathologyAI Clinical Lab",
        "email_notifications": True,
    },
    "chat_messages": [
        {
            "role": "assistant",
            "content": (
                "Hello. I'm the PathologyAI assistant. "
                "Upload a slide and run analysis, then ask me to interpret results."
            ),
        }
    ],
}


def init_session_state() -> None:
    """Ensure all session keys exist."""
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_analysis() -> None:
    """Clear analysis outputs but keep settings, auth, and chat."""
    st.session_state.analysis_status = AnalysisStatus.IDLE
    st.session_state.tissue_results = None
    st.session_state.cell_results = None
    st.session_state.ai_results = None
    st.session_state.heatmap_image = None
    st.session_state.gradcam_result = None
    st.session_state.last_processing_time_s = None


def reset_image_edits() -> None:
    st.session_state.edit_rotation = 0
    st.session_state.edit_brightness = 1.0
    st.session_state.edit_contrast = 1.0
    st.session_state.edit_crop = None


def has_image() -> bool:
    return st.session_state.current_image is not None


def is_authenticated() -> bool:
    return st.session_state.get("auth_user") is not None


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def log_in(user: dict) -> None:
    """Call on successful authentication — centralizes what 'being logged in'
    means (user record + timestamp for session-expiry checking) so every
    login path (login page, future SSO) behaves the same way."""
    st.session_state.auth_user = user
    st.session_state.auth_login_at = time.time()
    st.session_state.auth_error = None


def log_out() -> None:
    st.session_state.auth_user = None
    st.session_state.auth_login_at = None


def is_session_expired() -> bool:
    """True if a logged-in user's session has outlived SESSION_TIMEOUT_MINUTES.
    Doesn't log them out itself — app_create.py acts on this so it can show a
    message before clearing the session."""
    from config.settings import SESSION_TIMEOUT_MINUTES

    if not is_authenticated():
        return False
    login_at = st.session_state.get("auth_login_at")
    if login_at is None:
        return False
    return (time.time() - login_at) > (SESSION_TIMEOUT_MINUTES * 60)


def touch_session() -> None:
    """Reset the session-expiry clock on activity. Called on each authenticated
    page render so an active user isn't logged out mid-session — only a user
    who leaves the tab idle for SESSION_TIMEOUT_MINUTES gets signed out."""
    if is_authenticated():
        st.session_state.auth_login_at = time.time()


def toggle_theme() -> None:
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
