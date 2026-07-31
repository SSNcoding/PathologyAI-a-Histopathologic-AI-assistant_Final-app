"""
PathologyAI — AI-Powered Computational Pathology Platform
Launch: streamlit run app_create.py
"""

import importlib

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


def _lazy_page(module_name: str):
    """Defer importing an app_pages module until it's actually selected,
    instead of loading every page's dependencies at app startup.

    Several authenticated pages (AI Analysis, Explainable AI, Cell/Tissue
    Detection, Upload, Scan Queue) transitively import torch, opencv, and
    scikit-image via models/ and services/. Importing all app_pages modules
    up front — as this used to do — loads that entire heavy stack into
    memory before a single screen is shown, which is enough to blow past
    memory/startup-time limits on constrained hosts (e.g. Streamlit
    Community Cloud's free tier), even though it runs fine locally. Loading
    each page's module only when a user actually navigates to it keeps cold
    boot light and spreads the heavy imports out over time."""
    def _render() -> None:
        module = importlib.import_module(f"app_pages.{module_name}")
        module.render()
    return _render

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
    "Dashboard": _lazy_page("dashboard"),
    "Upload": _lazy_page("upload"),
    "AI Analysis": _lazy_page("ai_analysis"),
    "Results Dashboard": _lazy_page("results_dashboard"),
    "Explainable AI": _lazy_page("explainable_ai"),
    "Tissue Detection": _lazy_page("tissue_detection"),
    "Cell Detection": _lazy_page("cell_detection"),
    "Statistics": _lazy_page("statistics"),
    "Scan Queue": _lazy_page("scan_queue"),
    "Slide Inventory": _lazy_page("slide_inventory"),
    "Comparison": _lazy_page("comparison"),
    "Patient Report": _lazy_page("reports"),
    "ROI Annotation": _lazy_page("roi_annotation"),
    "Audit Log": _lazy_page("audit_log"),
    "Profile": _lazy_page("profile"),
    "Settings": _lazy_page("settings"),
}


def _hex_to_rgb(hex_color: str) -> str:
    """'#06B6D4' -> '6, 182, 212', for building an rgba() string. Needed
    because the "selected" nav item wants a translucent accent tint, not a
    flat fill, and the palette only stores solid hex values."""
    hex_color = hex_color.lstrip("#")
    return ", ".join(str(int(hex_color[i:i + 2], 16)) for i in (0, 2, 4))


def _render_nav_menu(options: list[str], default_index: int = 0) -> str:
    icons = [NAV_ICONS.get(o, "circle") for o in options]
    if _HAS_OPTION_MENU:
        # streamlit-option-menu renders as an isolated custom component — it
        # does NOT inherit assets/styles.css or our injected :root CSS
        # variables, only whatever literal colors are passed through this
        # `styles` dict. Previously this used "transparent" for the
        # container/nav-link backgrounds, banking on the sidebar's own
        # background showing through; that only worked in dark mode by
        # coincidence, so switching to light mode left the nav stuck dark.
        # Passing the current palette's real hex values here fixes it for
        # every mode/preset rather than just the one it happened to look
        # right in.
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



# OAuth callback (only reachable if services/oauth_service.py is configured —
# see its module docstring; a no-op otherwise). Checked before anything else
# so a redirect back from the provider logs the user in immediately.
if not is_authenticated():
    _oauth_userinfo = handle_oauth_callback()
    if _oauth_userinfo:
        _oauth_user = provision_local_account(_oauth_userinfo)
        log_in(_oauth_user)
        log_action(_oauth_user, "login_sso", "Signed in via SSO")
        st.rerun()

# Session expiry is checked once per rerun, before anything authenticated is
# drawn — an idle session past SESSION_TIMEOUT_MINUTES gets logged out here
# rather than silently letting stale credentials sit in session_state.
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
    APP_PAGES.get(selection, _lazy_page("dashboard"))()
    # Rendered last (not tied to the sidebar or any single page) and pinned
    # via CSS position:fixed, so Hoot shows up on top of whatever page you're
    # on rather than being confined to one tab — see ui/assistant_widget.py.
    render_floating_mascot()
else:
    PUBLIC_PAGES.get(selection, home.render)()