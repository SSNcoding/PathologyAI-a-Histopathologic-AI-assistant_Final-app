"""Tests for services/demo_slide.py's procedural image generator."""

from __future__ import annotations

import numpy as np
from PIL import Image

from services.demo_slide import generate_demo_slide


def test_generate_demo_slide_returns_rgb_image_of_requested_size():
    image = generate_demo_slide(size=(128, 96))
    assert isinstance(image, Image.Image)
    assert image.mode == "RGB"
    assert image.size == (128, 96)


def test_generate_demo_slide_is_deterministic_for_same_seed():
    a = generate_demo_slide(size=(64, 64), seed=3)
    b = generate_demo_slide(size=(64, 64), seed=3)
    assert np.array_equal(np.array(a), np.array(b))


def test_generate_demo_slide_differs_for_different_seeds():
    a = generate_demo_slide(size=(64, 64), seed=1)
    b = generate_demo_slide(size=(64, 64), seed=2)
    assert not np.array_equal(np.array(a), np.array(b))


def test_generate_demo_slide_is_not_a_flat_solid_color():
    # Sanity check that it actually has visual structure (nuclei/tissue) rather
    # than being an accidental solid fill, which would defeat its purpose.
    arr = np.array(generate_demo_slide(size=(256, 256)))
    assert arr.std() > 5
