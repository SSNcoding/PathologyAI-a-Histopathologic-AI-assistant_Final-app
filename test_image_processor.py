"""Tests for services/image_processor.py's pure-function metrics — the parts
most likely to silently drift as the heuristic formulas get tweaked, since
nothing today would catch a change that breaks bounds/labels."""

from __future__ import annotations

import numpy as np
from PIL import Image

from services.image_processor import (
    apply_edits,
    estimate_tumor_metrics,
    slide_quality_precheck,
    tissue_quality_score,
)


def _solid_image(color=(200, 150, 180), size=(64, 64)) -> Image.Image:
    return Image.new("RGB", size, color)


def _noisy_image(size=(128, 128), seed=0) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 255, size=(size[1], size[0], 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


def test_tissue_quality_score_bounds():
    tissue = {"tissue_coverage_pct": 80.0}
    cells = {"nuclei": [{"circularity": 0.8}, {"circularity": 0.9}]}
    result = tissue_quality_score(tissue, cells)
    assert 0 <= result["score"] <= 100
    assert result["label"] in {"Good", "Adequate", "Suboptimal"}


def test_tissue_quality_score_empty_input():
    result = tissue_quality_score({}, {"nuclei": []})
    assert result["score"] == 0
    assert result["label"] == "Suboptimal"


def test_estimate_tumor_metrics_ranges():
    tissue = {"tissue_coverage_pct": 60.0, "region_count": 3}
    cells = {
        "density_per_mpx": 120.0,
        "nuclei": [{"area": a, "circularity": c} for a, c in zip([10, 20, 30, 40], [0.9, 0.5, 0.85, 0.6])],
    }
    metrics = estimate_tumor_metrics(tissue, cells)
    assert 0 <= metrics["tumor_pct"] <= 100
    assert 0 <= metrics["healthy_tissue_pct"] <= 100
    assert 0 <= metrics["inflammation_score"] <= 10
    assert 0 <= metrics["necrosis_score"] <= 10
    assert metrics["mitotic_count"] >= 0
    assert "Heuristic" in metrics["disclaimer"]


def test_estimate_tumor_metrics_handles_no_nuclei():
    metrics = estimate_tumor_metrics({"tissue_coverage_pct": 50.0, "region_count": 0}, {"density_per_mpx": 0, "nuclei": []})
    assert metrics["mitotic_count"] == 0


def test_apply_edits_rotation_changes_size_for_non_square():
    image = Image.new("RGB", (100, 40), (255, 255, 255))
    rotated = apply_edits(image, rotation=90)
    assert rotated.size == (40, 100)


def test_apply_edits_crop_shrinks_image():
    image = Image.new("RGB", (200, 200), (255, 255, 255))
    cropped = apply_edits(image, crop_box_pct=(10, 10, 10, 10))
    assert cropped.size[0] < 200
    assert cropped.size[1] < 200


def test_apply_edits_no_ops_returns_same_size():
    image = Image.new("RGB", (50, 50), (100, 100, 100))
    out = apply_edits(image)
    assert out.size == (50, 50)


def test_slide_quality_precheck_flags_solid_color_as_low_sharpness():
    # A perfectly solid-color image has zero edge content -> should not cleanly pass blur check.
    result = slide_quality_precheck(_solid_image())
    assert result["blur_status"] in {"warn", "fail"}
    assert result["verdict"] in {"warn", "fail"}


def test_slide_quality_precheck_returns_expected_shape():
    result = slide_quality_precheck(_noisy_image())
    assert result["verdict"] in {"pass", "warn", "fail"}
    assert {"verdict", "blur_status", "exposure_status", "laplacian_variance", "mean_intensity", "std_intensity"} <= set(result)


def test_slide_quality_precheck_verdict_is_worst_of_subchecks():
    result = slide_quality_precheck(_solid_image())
    statuses = [result["blur_status"], result["exposure_status"]]
    if "fail" in statuses:
        assert result["verdict"] == "fail"
    elif "warn" in statuses:
        assert result["verdict"] == "warn"
    else:
        assert result["verdict"] == "pass"
