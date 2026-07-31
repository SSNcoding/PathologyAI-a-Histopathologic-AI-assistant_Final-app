"""Tests for services/pdf_report.py — mostly a smoke test (does it produce a
real PDF without crashing across the report's various optional fields) plus
a check on the new report-ID helper's determinism."""

from __future__ import annotations

from datetime import datetime

from services.pdf_report import _report_id, build_pdf_report


def test_report_id_is_deterministic_for_same_inputs():
    ts = datetime(2026, 1, 1, 12, 0, 0)
    assert _report_id("SPEC-1", "slide.png", ts) == _report_id("SPEC-1", "slide.png", ts)


def test_report_id_differs_for_different_inputs():
    ts = datetime(2026, 1, 1, 12, 0, 0)
    assert _report_id("SPEC-1", "slide.png", ts) != _report_id("SPEC-2", "slide.png", ts)


def test_build_pdf_report_produces_valid_pdf_bytes():
    pdf_bytes = build_pdf_report(
        patient_id="SPEC-TEST-001",
        slide_name="test_slide.png",
        physician="Dr. Test",
        institution="Test Institution",
        summary="Heuristic analysis suggests **Benign** (confidence 82%). _Not a clinical diagnosis._",
        findings=[{"label": "Benign", "confidence": 0.82}, {"label": "DCIS", "confidence": 0.18}],
        tissue_stats={"tissue_coverage_pct": 71.2, "region_count": 3},
        cell_stats={"nuclei_count": 512, "density_per_mpx": 88.4, "mean_area": 42.1},
        tumor_metrics={"tumor_pct": 12.0, "healthy_tissue_pct": 84.0, "inflammation_score": 2.1,
                        "necrosis_score": 0.5, "mitotic_count": 1},
        quality={"label": "Good", "score": 91.0},
        organ="Breast Cancer",
        architecture="Classical CV Heuristic (no trained weights)",
        model_mode="HEURISTIC_PLACEHOLDER",
        model_version="heuristic-cv-v1",
        risk_level="low",
        processing_time_s=1.23,
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000


def test_build_pdf_report_handles_missing_optional_fields():
    pdf_bytes = build_pdf_report(
        patient_id="SPEC-MIN-001",
        slide_name="minimal.png",
        physician="",
        institution="",
        summary="Minimal summary.",
        findings=[{"label": "Benign", "confidence": 1.0}],
        tissue_stats={},
        cell_stats={},
    )
    assert pdf_bytes.startswith(b"%PDF")
