"""Tests for core/i18n.py's translation lookup logic (not the Streamlit
widgets, which need a real app context)."""

from __future__ import annotations

from core.i18n import DEFAULT_LANGUAGE, STRINGS, SUPPORTED_LANGUAGES


def test_default_language_is_supported():
    assert DEFAULT_LANGUAGE in SUPPORTED_LANGUAGES


def test_every_supported_language_has_a_string_table():
    for lang in SUPPORTED_LANGUAGES:
        assert lang in STRINGS
        assert len(STRINGS[lang]) > 0


def test_every_key_in_default_language_exists_in_every_other_language():
    default_keys = set(STRINGS[DEFAULT_LANGUAGE].keys())
    for lang, table in STRINGS.items():
        missing = default_keys - set(table.keys())
        assert not missing, f"Language '{lang}' is missing translations for: {missing}"


def test_no_empty_string_values():
    for lang, table in STRINGS.items():
        for key, value in table.items():
            assert value.strip(), f"Empty translation for '{key}' in '{lang}'"
