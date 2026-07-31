"""Theme injection and global page chrome.

Light/dark mode works by re-emitting a `:root { --var: value }` block on
every rerun based on `st.session_state.theme` — no client-side JS needed,
which keeps it 100% reliable inside Streamlit's rerun model.
"""

from __future__ import annotations

import streamlit as st

from config.settings import APP_NAME, APP_TAGLINE, APP_VERSION, ASSETS_DIR
from core.constants import THEME_DARK, THEME_LIGHT, THEME_PRESETS
from core.i18n import t
from core.session_state import init_session_state


def _current_mode() -> str:
    return "light" if st.session_state.get("theme") == "light" else "dark"


def _current_palette() -> dict:
    mode = _current_mode()
    default_name = "Cloud" if mode == "light" else "Midnight"
    preset_name = st.session_state.get(f"{mode}_preset", default_name)
    presets = THEME_PRESETS[mode]
    return presets.get(preset_name) or (THEME_LIGHT if mode == "light" else THEME_DARK)


def current_palette() -> dict:
    """Public accessor for the current theme/preset's color dict.

    streamlit-option-menu (used for the sidebar nav) renders as an isolated
    custom component — it doesn't inherit assets/styles.css or our injected
    :root CSS variables, only whatever literal colors are passed through its
    own Python `styles=` argument. app_create.py calls this to feed it real
    hex values instead of relying on CSS to reach inside the component."""
    return _current_palette()


def inject_theme_variables() -> None:
    palette = _current_palette()
    variables = "\n".join(f"    --{k.replace('_', '-')}: {v};" for k, v in palette.items())
    st.markdown(f"<style>:root {{\n{variables}\n}}</style>", unsafe_allow_html=True)


def load_css() -> None:
    inject_theme_variables()
    css_path = ASSETS_DIR / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_sidebar_branding() -> None:
    st.markdown(
        f"""
        <div class="brand-header">
            <div class="brand-title">\U0001F9EC {APP_NAME}</div>
            <div class="brand-subtitle">{t("app.tagline") or APP_TAGLINE}</div>
            <div class="brand-subtitle">v{APP_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="page-hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def theme_toggle_control(key: str = "theme_toggle_widget") -> None:
    is_light = st.session_state.theme == "light"
    label = "☀️ Light mode" if is_light else "\U0001F319 Dark mode"
    new_value = st.toggle(label, value=is_light, key=key)
    desired_theme = "light" if new_value else "dark"
    if desired_theme != st.session_state.theme:
        st.session_state.theme = desired_theme
        st.rerun()


def background_picker_control() -> None:
    mode = _current_mode()
    presets = list(THEME_PRESETS[mode].keys())
    state_key = f"{mode}_preset"
    current = st.session_state.get(state_key)
    if current not in presets:
        current = presets[0]
    selection = st.selectbox(
        "Background",
        presets,
        index=presets.index(current),
        key=f"bg_preset_select_{mode}",
    )
    if selection != st.session_state.get(state_key):
        st.session_state[state_key] = selection
        st.rerun()


def setup_app() -> None:
    """Call once at startup."""
    init_session_state()
    load_css()
