"""Tests for models/disease_registry.py — every page, chart, and report reads
from this taxonomy, so a malformed entry here breaks multiple pages at once."""

from __future__ import annotations

from models.disease_registry import DISEASE_REGISTRY, get_organ, organ_options


def test_registry_is_nonempty():
    assert len(DISEASE_REGISTRY) >= 1


def test_every_organ_has_consistent_key_and_real_content():
    for key, organ in DISEASE_REGISTRY.items():
        assert organ.key == key, f"registry key '{key}' doesn't match organ.key '{organ.key}'"
        assert len(organ.classes) >= 2, f"{key} needs a benign class plus at least one disease class"
        assert len(organ.datasets) >= 1, f"{key} should reference at least one dataset"
        assert len(organ.reference_architectures) >= 1
        assert organ.display_name
        assert organ.icon


def test_no_duplicate_class_labels_within_an_organ():
    for key, organ in DISEASE_REGISTRY.items():
        assert len(organ.classes) == len(set(organ.classes)), f"{key} has duplicate class labels"


def test_get_organ_unknown_key_falls_back_to_breast():
    fallback = get_organ("does-not-exist")
    assert fallback.key == "breast"


def test_get_organ_known_key():
    organ = get_organ("lung")
    assert organ.display_name == "Lung Cancer"


def test_organ_options_sorted_by_display_name_and_covers_whole_registry():
    options = organ_options()
    names = [name for _, name in options]
    assert names == sorted(names)
    assert len(options) == len(DISEASE_REGISTRY)
    assert set(key for key, _ in options) == set(DISEASE_REGISTRY.keys())
