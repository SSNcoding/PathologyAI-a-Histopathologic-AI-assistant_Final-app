"""Minimal internationalization scaffold.

This is real, working translation infrastructure — not a stub — but only a
representative slice of the UI's strings are wired through `t()` so far
(sidebar branding, the Settings page, and the landing page hero). Extending
coverage to every page is mechanical, not architectural: replace a
hardcoded string with `t("some.key")` and add that key to STRINGS below for
each language you support.

Usage:
    from core.i18n import t
    st.write(t("settings.appearance"))

Language is read from st.session_state.language (defaults to "en"), set via
language_picker() on the Settings page.
"""

from __future__ import annotations

import streamlit as st

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en": "English", "es": "Español"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app.tagline": "AI-Powered Computational Pathology Platform",
        "settings.title": "Settings",
        "settings.subtitle": "Configure analysis thresholds, reporting, appearance, and model integration",
        "settings.appearance": "Appearance",
        "settings.language": "Language",
        "settings.analysis": "Analysis",
        "settings.report_defaults": "Report Defaults",
        "settings.notifications": "Notifications",
        "settings.model_registry": "Model Registry",
        "home.hero.eyebrow": "AI-Powered Computational Pathology",
        "home.hero.title": "See what the microscope alone can't tell you.",
        "home.upload_button": "Upload a Slide",
        "home.learn_more_button": "Learn More",
    },
    "es": {
        "app.tagline": "Plataforma de Patología Computacional con IA",
        "settings.title": "Configuración",
        "settings.subtitle": "Configura umbrales de análisis, informes, apariencia e integración de modelos",
        "settings.appearance": "Apariencia",
        "settings.language": "Idioma",
        "settings.analysis": "Análisis",
        "settings.report_defaults": "Valores predeterminados del informe",
        "settings.notifications": "Notificaciones",
        "settings.model_registry": "Registro de modelos",
        "home.hero.eyebrow": "Patología Computacional con IA",
        "home.hero.title": "Vea lo que el microscopio por sí solo no puede decirle.",
        "home.upload_button": "Subir una Muestra",
        "home.learn_more_button": "Más Información",
    },
}


def current_language() -> str:
    return st.session_state.get("language", DEFAULT_LANGUAGE)


def set_language(lang: str) -> None:
    if lang in SUPPORTED_LANGUAGES:
        st.session_state.language = lang


def t(key: str, **kwargs) -> str:
    """Look up `key` in the current language, falling back to English, then
    to the key itself — a missing translation shows up as a visibly-odd
    string (the raw key) instead of crashing the page or silently going
    blank, the same fail-open behavior most i18n libraries use."""
    lang = current_language()
    value = STRINGS.get(lang, {}).get(key) or STRINGS[DEFAULT_LANGUAGE].get(key) or key
    return value.format(**kwargs) if kwargs else value


def language_picker() -> None:
    """Dropdown to switch languages — call from the Settings page (or
    anywhere else you want to expose it)."""
    options = list(SUPPORTED_LANGUAGES.keys())
    labels = list(SUPPORTED_LANGUAGES.values())
    current = current_language()
    idx = options.index(current) if current in options else 0
    selection = st.selectbox(t("settings.language"), labels, index=idx, key="language_picker_widget")
    chosen_key = options[labels.index(selection)]
    if chosen_key != current:
        set_language(chosen_key)
        st.rerun()
