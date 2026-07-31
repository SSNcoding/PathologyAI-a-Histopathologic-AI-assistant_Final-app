"""Simulated scanner fleet + slide inventory metadata.

Real digital pathology scanners — Leica Aperio GT 450 / AT2, Philips
IntelliSite Ultra Fast Scanner, Hamamatsu NanoZoomer S360, 3DHistech
Pannoramic 250 Flash III, and similar — share a common operating model: a
slide-loading robot feeds an internal rack, each slide gets a barcode/label
read plus a low-res "macro" preview shot before the actual brightfield
scan, and a fleet-management console (Aperio eSlide Manager, Philips IMS,
Sectra, Proscia Concentriq, etc.) shows which units are online / scanning /
idle / offline across a lab, alongside a queue of pending jobs.

This app has no physical scanner attached, so everything below is clearly
simulated — deterministic, derived from data already in session/db, not a
real device/DICOM/LIS integration. Swap this module for actual scanner SDK
calls if real hardware gets wired up; nothing else in Scan Queue or Slide
Inventory assumes it's real.
"""

from __future__ import annotations

import hashlib
import random

# A representative sample of common WSI scanner models across major
# vendors — not an exhaustive or endorsed list, just enough variety to make
# the fleet view feel like a real multi-scanner lab rather than one device.
SCANNER_FLEET = [
    {"name": "Aperio GT 450", "vendor": "Leica Biosystems", "capacity": 400, "max_mag": "40x"},
    {"name": "IntelliSite Ultra Fast Scanner", "vendor": "Philips", "capacity": 300, "max_mag": "40x"},
    {"name": "NanoZoomer S360", "vendor": "Hamamatsu", "capacity": 360, "max_mag": "40x"},
    {"name": "Pannoramic 250 Flash III", "vendor": "3DHistech", "capacity": 250, "max_mag": "40x"},
]

_STATUS_WEIGHTS = ["Idle", "Idle", "Idle", "Scanning", "Offline"]


def fleet_status(seed: int | None = None) -> list[dict]:
    """Deterministic-per-seed simulated fleet status — not a real device
    connection. Pass a changing seed (e.g. a coarse time bucket) if you
    want it to visibly shift between reruns in a demo."""
    rng = random.Random(seed if seed is not None else 7)
    fleet = []
    for unit in SCANNER_FLEET:
        status = rng.choice(_STATUS_WEIGHTS)
        loaded = rng.randint(0, unit["capacity"])
        fleet.append({
            **unit,
            "status": status,
            "loaded_slides": loaded,
            "current_slide": f"SLD-{rng.randint(1000, 9999)}" if status == "Scanning" else None,
            "progress_pct": rng.randint(5, 95) if status == "Scanning" else None,
        })
    return fleet


def barcode_for(analysis_id: int, slide_name: str) -> str:
    """Deterministic fake barcode derived from the analysis id + slide name,
    so the same saved case always shows the same code across reruns without
    an actual barcode reader in the loop."""
    digest = hashlib.sha1(f"{analysis_id}:{slide_name}".encode()).hexdigest()[:8].upper()
    return f"PA-{digest}"


def rack_position_for(analysis_id: int) -> str:
    """Deterministic fake rack/row/column, seeded off the analysis id."""
    rng = random.Random(analysis_id)
    rack = rng.randint(1, 12)
    row = rng.choice("ABCDEFGH")
    col = rng.randint(1, 10)
    return f"Rack {rack} · {row}{col}"
