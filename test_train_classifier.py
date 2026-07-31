"""Tests for train_classifier.py's label-remapping logic — the part most
likely to produce a silently-wrong model (right prediction, wrong index)
if it has a bug, since training would still 'succeed' either way."""

from __future__ import annotations

import pytest
from PIL import Image
from torchvision.datasets import ImageFolder
from torchvision import transforms

from train_classifier import _RemappedLabels

_TO_TENSOR = transforms.Compose([transforms.Resize((8, 8)), transforms.ToTensor()])


def _make_dataset_dir(tmp_path, class_to_count: dict[str, int]):
    for class_name, count in class_to_count.items():
        class_dir = tmp_path / class_name
        class_dir.mkdir()
        for i in range(count):
            Image.new("RGB", (8, 8), (i * 10 % 255, 0, 0)).save(class_dir / f"img_{i}.png")
    return tmp_path


def test_remapped_labels_matches_registry_order(tmp_path):
    # ImageFolder sorts alphabetically: Alpha=0, Beta=1 — deliberately the
    # OPPOSITE of the registry order below, to actually exercise remapping.
    data_dir = _make_dataset_dir(tmp_path, {"Alpha": 2, "Beta": 2})
    base = ImageFolder(str(data_dir))
    assert base.classes == ["Alpha", "Beta"]  # sanity-check ImageFolder's own ordering assumption

    registry_order = ["Beta", "Alpha"]  # our desired (registry) order is reversed vs. ImageFolder's
    remapped = _RemappedLabels(base, registry_order, _TO_TENSOR)

    for idx in range(len(base)):
        _, original_label = base.samples[idx]
        _, remapped_label = remapped[idx]
        original_class_name = base.classes[original_label]
        assert registry_order[remapped_label] == original_class_name


def test_remapped_labels_raises_on_missing_class_folder(tmp_path):
    data_dir = _make_dataset_dir(tmp_path, {"Alpha": 1})
    base = ImageFolder(str(data_dir))
    with pytest.raises(ValueError, match="missing subfolders"):
        _RemappedLabels(base, ["Alpha", "Beta"], _TO_TENSOR)


def test_remapped_labels_length_matches_base(tmp_path):
    data_dir = _make_dataset_dir(tmp_path, {"Alpha": 3, "Beta": 2})
    base = ImageFolder(str(data_dir))
    remapped = _RemappedLabels(base, ["Beta", "Alpha"], _TO_TENSOR)
    assert len(remapped) == len(base) == 5
