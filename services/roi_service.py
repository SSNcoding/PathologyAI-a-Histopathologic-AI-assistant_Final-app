"""ROI (region-of-interest) annotation logic for app_pages/roi_annotation.py.

Regions are stored as percentage-of-image bounding boxes (x1_pct, y1_pct,
x2_pct, y2_pct) rather than raw pixel coordinates, so a saved annotation
still lines up correctly even if the underlying image gets re-cropped or
resized later.

This is a slider-based box tool, not a freehand/click-drag canvas —
deliberately. A real drawing canvas would mean taking on a third-party
dependency like streamlit-drawable-canvas, which has a history of breaking
against newer Streamlit releases. Percentage sliders plus a live
PIL-rendered preview cover the same "mark a region and label it" need
without that risk. Annotations are session-scoped per slide, not written
to the database — this is a lightweight sketch/labeling tool, not a
clinical record.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from PIL import Image, ImageDraw

LABEL_COLORS = {
    "Tumor / Suspected Neoplasia": "#EF4444",
    "Necrosis": "#F59E0B",
    "Inflammatory Infiltrate": "#8B5CF6",
    "Normal Tissue": "#10B981",
    "Artifact / Pitfall": "#94A3B8",
    "Other": "#3B82F6",
}


def color_for_label(label: str) -> str:
    return LABEL_COLORS.get(label, "#3B82F6")


def new_annotation(label: str, note: str, x1_pct: float, y1_pct: float, x2_pct: float, y2_pct: float) -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "label": label,
        "note": note.strip(),
        "x1_pct": round(min(x1_pct, x2_pct), 1),
        "y1_pct": round(min(y1_pct, y2_pct), 1),
        "x2_pct": round(max(x1_pct, x2_pct), 1),
        "y2_pct": round(max(y1_pct, y2_pct), 1),
        "color": color_for_label(label),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def render_overlay(
    image: Image.Image,
    annotations: list[dict],
    draft_box: tuple[float, float, float, float] | None = None,
    draft_color: str = "#3B82F6",
) -> Image.Image:
    """Returns a copy of `image` with every saved annotation's box drawn,
    plus an optional in-progress "draft" box — the one currently being
    positioned by the sliders, before it's saved."""
    overlay = image.convert("RGB").copy()
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size
    line_width = max(2, width // 250)

    def _box_px(x1_pct, y1_pct, x2_pct, y2_pct):
        return (x1_pct / 100 * width, y1_pct / 100 * height, x2_pct / 100 * width, y2_pct / 100 * height)

    for ann in annotations:
        box = _box_px(ann["x1_pct"], ann["y1_pct"], ann["x2_pct"], ann["y2_pct"])
        draw.rectangle(box, outline=ann["color"], width=line_width)
        label_y = max(0, box[1] - 18)
        draw.text((box[0] + 4, label_y), ann["label"], fill=ann["color"])

    if draft_box is not None:
        box = _box_px(*draft_box)
        draw.rectangle(box, outline=draft_color, width=line_width)

    return overlay


def annotations_to_csv_bytes(annotations: list[dict]) -> bytes:
    fieldnames = ["id", "label", "note", "x1_pct", "y1_pct", "x2_pct", "y2_pct", "created_at"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for ann in annotations:
        writer.writerow({k: ann.get(k, "") for k in fieldnames})
    return buf.getvalue().encode("utf-8")