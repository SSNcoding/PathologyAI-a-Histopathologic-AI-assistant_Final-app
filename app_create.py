"""
PathologyAI — AI-Powered Computational Pathology Platform
Launch: streamlit run app_create.py
"""

import streamlit as st

from core.constants import NAV_APP, NAV_ICONS
from core.permissions import pages_for_role, role_label
from core.session_state import current_user, is_authenticated, is_session_expired, log_in, log_out, touch_session
from services.audit_service import log_action
from services.notification_service import list_notifications
from services.oauth_service import handle_callback as handle_oauth_callback
from services.oauth_service import provision_local_account
from ui.assistant_widget import render_floating_mascot
from ui.theme import background_picker_control, current_palette, render_sidebar_branding, setup_app, theme_toggle_control

# Public pages (no login required)
from app_pages import about, contact, home, login, register

# Authenticated app pages
from app_pages import (
    ai_analysis,
    audit_log,
    cell_detection,
    comparison,
    dashboard,
    explainable_ai,
    profile,
    reports,
    results_dashboard,
    roi_annotation,
    scan_queue,
    settings,
    slide_inventory,
    statistics,
    tissue_detection,
    upload,
)

try:
    from streamlit_option_menu import option_menu
    _HAS_OPTION_MENU = True
except ImportError:
    _HAS_OPTION_MENU = False

st.set_page_config(
    page_title="PathologyAI",
    page_icon="\U0001F9EC",
    layout="wide",
    initial_sidebar_state="expanded",
)
setup_app()

PUBLIC_PAGES = {
    "Home": home.render,
    "About": about.render,
    "Contact": contact.render,
    "Login": login.render,
    "Register": register.render,
}

APP_PAGES = {
    "Dashboard": dashboard.render,
    "Upload": upload.render,
    "AI Analysis": ai_analysis.render,
    "Results Dashboard": results_dashboard.render,
    "Explainable AI": explainable_ai.render,
    "Tissue Detection": tissue_detection.render,
    "Cell Detection": cell_detection.render,
    "Statistics": statistics.render,
    "Scan Queue": scan_queue.render,
    "Slide Inventory": slide_inventory.render,
    "Comparison": comparison.render,
    "Patient Report": reports.render,
    "ROI Annotation": roi_annotation.render,
    "Audit Log": audit_log.render,
    "Profile": profile.render,
    "Settings": settings.render,
}


def _hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    return ", ".join(str(int(hex_color[i:i + 2], 16)) for i in (0, 2, 4))


def _render_nav_menu(options: list[str], default_index: int = 0) -> str:
    icons = [NAV_ICONS.get(o, "circle") for o in options]
    if _HAS_OPTION_MENU:
        palette = current_palette()
        accent_rgb = _hex_to_rgb(palette["accent_cyan"])
        return option_menu(
            menu_title=None,
            options=options,
            icons=icons,
            default_index=default_index,
            styles={
                "container": {"padding": "0", "background-color": palette["bg_surface"]},
                "icon": {"font-size": "0.95rem", "color": palette["text_muted"]},
                "nav-link": {
                    "font-size": "0.92rem",
                    "text-align": "left",
                    "margin": "2px 0",
                    "border-radius": "10px",
                    "color": palette["text_primary"],
                    "background-color": palette["bg_surface"],
                },
                "nav-link-selected": {
                    "background-color": f"rgba({accent_rgb}, 0.18)",
                    "color": palette["text_primary"],
                },
            },
        )
    return st.radio("Navigation", options, label_visibility="collapsed")


# OAuth callback (only reachable if services/oauth_service.py is configured)
if not is_authenticated():
    _oauth_userinfo = handle_oauth_callback()
    if _oauth_userinfo:
        _oauth_user = provision_local_account(_oauth_userinfo)
        log_in(_oauth_user)
        log_action(_oauth_user, "login_sso", "Signed in via SSO")
        st.rerun()

if is_session_expired():
    expired_user = current_user()
    log_out()
    log_action(expired_user, "session_expired", "Auto-logged-out after inactivity timeout")
    st.session_state.public_page = "Login"
    st.info("You were signed out after a period of inactivity. Please log in again.")

with st.sidebar:
    render_sidebar_branding()

    if is_authenticated():
        user = current_user()
        touch_session()
        st.markdown(f"**{user.get('full_name') or user['username']}**")
        st.caption(f"{user.get('role', 'pathologist').title()} · {user.get('institution') or 'Independent'}")
        st.caption(role_label(user.get("role")))

        unread = len(list_notifications(user["id"], unread_only=True))
        if unread:
            st.caption(f"\U0001F514 {unread} unread notification(s) — see Settings")

        visible_pages = [p for p in NAV_APP if p in pages_for_role(user.get("role"))]
        selection = _render_nav_menu(visible_pages)

        st.markdown("---")
        theme_toggle_control()
        background_picker_control()
        if st.button("Log Out", use_container_width=True):
            log_action(user, "logout", "")
            log_out()
            st.rerun()
    else:
        public_options = ["Home", "About", "Contact", "Login", "Register"]
        default_page = st.session_state.get("public_page", "Home")
        default_index = public_options.index(default_page) if default_page in public_options else 0
        selection = _render_nav_menu(public_options, default_index=default_index)
        st.session_state.public_page = selection
        st.markdown("---")
        theme_toggle_control()
        background_picker_control()

    st.markdown("---")
    st.caption("Computational pathology • Research & education use only • Not a medical device")

if is_authenticated():
    APP_PAGES.get(selection, dashboard.render)()
    render_floating_mascot()
else:
    PUBLIC_PAGES.get(selection, home.render)()