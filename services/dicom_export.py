"""DICOM export scaffold — packages an analysis result as a DICOM Secondary
Capture (SC) object, so it can eventually be pushed into a PACS/VNA that
speaks DICOM instead of only PDF/CSV/JSON.

Best-effort, not a full PACS integration. This builds a valid, minimal
DICOM file in memory (Secondary Capture IOD, using the heatmap or slide
thumbnail as pixel data, with the report summary and model provenance
embedded in ImageComments). It deliberately does NOT include:
  - a real DICOM network transfer (see push_to_pacs() below — a documented
    stub, not a working implementation; there was no live PACS available in
    the environment this was built in to test a C-STORE association against)
  - coordination with an existing PACS study's UIDs (each export gets fresh
    Study/Series/SOP UIDs, so it will land as a new study, not attach to one)
  - de-identification review — see the README's HIPAA caveat before using
    this with real patient data

Requires `pydicom` (commented out in requirements.txt by default —
`pip install pydicom` to use this module). Nothing else in the app imports
this at startup, so leaving pydicom uninstalled has zero effect elsewhere;
callers should check is_dicom_available() before offering DICOM export in
the UI (see app_pages/reports.py).
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import numpy as np
from PIL import Image

try:
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid
    _HAS_PYDICOM = True
except ImportError:
    _HAS_PYDICOM = False


def is_dicom_available() -> bool:
    return _HAS_PYDICOM


def build_dicom_secondary_capture(
    *,
    image: Image.Image,
    patient_id: str,
    patient_name: str,
    report_summary: str,
    organ: str,
    model_mode: str,
    model_version: str | None = None,
    institution: str = "",
) -> bytes:
    """Returns DICOM file bytes (a valid .dcm you can save or attempt to
    import into a PACS/DICOM viewer). Raises ImportError if pydicom isn't
    installed — call is_dicom_available() first, the way this module's own
    caller in reports.py does, so the UI can hide the option cleanly instead
    of hitting this exception."""
    if not _HAS_PYDICOM:
        raise ImportError(
            "pydicom is not installed. Run `pip install pydicom` (see requirements.txt) "
            "to enable DICOM export."
        )

    rgb = np.array(image.convert("RGB"))
    rows, cols, _ = rgb.shape

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()

    now = datetime.now()
    ds.StudyDate = now.strftime("%Y%m%d")
    ds.StudyTime = now.strftime("%H%M%S")
    ds.Modality = "SC"  # Secondary Capture — this is a derived/rendered image, not raw scanner output
    ds.ConversionType = "WSD"  # Workstation-generated

    ds.PatientID = patient_id or "UNKNOWN"
    ds.PatientName = (patient_name or "UNKNOWN").replace(" ", "^") or "UNKNOWN"
    ds.InstitutionName = institution or ""

    ds.Manufacturer = "PathologyAI"
    ds.SeriesDescription = f"PathologyAI analysis - {organ} ({model_mode})"
    ds.ImageComments = (
        f"{report_summary[:512]} | model_mode={model_mode} | "
        f"model_version={model_version or 'n/a'} | Research/education use only, "
        f"not a diagnostic device."
    )[:10240]

    ds.Rows, ds.Columns = rows, cols
    ds.SamplesPerPixel = 3
    ds.PhotometricInterpretation = "RGB"
    ds.PlanarConfiguration = 0
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PixelData = rgb.tobytes()

    ds.is_little_endian = True
    ds.is_implicit_VR = False

    buf = io.BytesIO()
    ds.save_as(buf, write_like_original=False)
    return buf.getvalue()


def push_to_pacs(dicom_bytes: bytes, pacs_host: str, pacs_port: int, ae_title: str) -> None:
    """NOT IMPLEMENTED — a real DICOM C-STORE needs a live PACS to test
    against, which wasn't available in the environment this was built in.
    `pynetdicom` is the standard library for this; a real implementation
    would look like:

        import io
        import pydicom
        from pynetdicom import AE
        from pynetdicom.sop_class import SecondaryCaptureImageStorage

        ae = AE()
        ae.add_requested_context(SecondaryCaptureImageStorage)
        assoc = ae.associate(pacs_host, pacs_port, ae_title=ae_title)
        if assoc.is_established:
            assoc.send_c_store(pydicom.dcmread(io.BytesIO(dicom_bytes)))
            assoc.release()

    Left as a documented stub rather than untested guesswork against a
    stateful network protocol where subtle mistakes fail silently.
    """
    raise NotImplementedError(
        "push_to_pacs() is a documented stub, not a working implementation — see this "
        "function's docstring for what a real one needs (a live PACS to test against)."
    )
