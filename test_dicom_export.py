"""Tests for services/dicom_export.py — pydicom is an optional dependency
(commented out in requirements.txt), so this test adapts to whether it's
actually installed rather than assuming either way."""

from __future__ import annotations

import pytest
from PIL import Image

from services.dicom_export import build_dicom_secondary_capture, is_dicom_available, push_to_pacs


def test_push_to_pacs_is_a_documented_stub():
    with pytest.raises(NotImplementedError):
        push_to_pacs(b"", "localhost", 104, "PATHAI")


def test_build_dicom_without_pydicom_raises_clear_import_error():
    if is_dicom_available():
        pytest.skip("pydicom is installed in this environment — see the other test for the happy path.")
    with pytest.raises(ImportError):
        build_dicom_secondary_capture(
            image=Image.new("RGB", (16, 16), (128, 128, 128)),
            patient_id="SPEC-1",
            patient_name="Test Patient",
            report_summary="Test summary",
            organ="Breast Cancer",
            model_mode="HEURISTIC_PLACEHOLDER",
        )


def test_build_dicom_with_pydicom_produces_valid_bytes():
    if not is_dicom_available():
        pytest.skip("pydicom is not installed in this environment.")
    dicom_bytes = build_dicom_secondary_capture(
        image=Image.new("RGB", (16, 16), (128, 128, 128)),
        patient_id="SPEC-1",
        patient_name="Test Patient",
        report_summary="Test summary",
        organ="Breast Cancer",
        model_mode="HEURISTIC_PLACEHOLDER",
        model_version="heuristic-cv-v1",
    )
    assert isinstance(dicom_bytes, bytes)
    # Valid DICOM files have a 128-byte preamble followed by "DICM".
    assert dicom_bytes[128:132] == b"DICM"
