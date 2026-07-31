"""
Histopathology image processing with OpenCV.
Real techniques:
- Tissue segmentation via saturation + Otsu + morphology
- Nuclei detection via hematoxylin channel enhancement + adaptive threshold
- Contour filtering by area and circularity
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import cv2
import numpy as np
from PIL import Image

@dataclass
class TissueRegion:
    label: str
    area_px: int
    area_pct: float
    bbox: tuple[int, int, int, int]  # x, y, w, h
    centroid: tuple[int, int]
    color_hex: str

@dataclass
class Nucleus:
    cx: int
    cy: int
    area: float
    circularity: float
    bbox: tuple[int, int, int, int]

def pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

def bgr_to_pil(image_bgr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)

def approximate_hematoxylin_channel(bgr: np.ndarray) -> np.ndarray:
    """
    Approximate hematoxylin (nuclear stain) channel without full Ruifrok deconvolution.
    Works well enough for nuclei segmentation on standard H&E slides.
    """
    b, g, r = cv2.split(bgr.astype(np.float32))
    # Purple/blue nuclei have high blue, moderate red, lower green
    h_channel = 0.65 * (255 - r) + 0.25 * (255 - g) + 0.10 * b
    h_channel = np.clip(h_channel, 0, 255).astype(np.uint8)
    return h_channel

def detect_tissue_regions(image: Image.Image, min_area_ratio: float = 0.005) -> dict[str, Any]:
    """
    Segment tissue from background using HSV saturation + Otsu thresholding.
    Returns annotated overlay and region statistics.
    """
    bgr = pil_to_bgr(image)
    h, w = bgr.shape[:2]
    total_px = h * w
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    blur = cv2.GaussianBlur(sat, (5, 5), 0)
    _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = total_px * min_area_ratio
    overlay = bgr.copy()
    regions: list[TissueRegion] = []
    palette = [
        ("Tissue Region A", "#06B6D4"),
        ("Tissue Region B", "#3B82F6"),
        ("Tissue Region C", "#8B5CF6"),
        ("Tissue Region D", "#10B981"),
        ("Tissue Region E", "#F59E0B"),
    ]
    valid = [c for c in contours if cv2.contourArea(c) >= min_area]
    valid = sorted(valid, key=cv2.contourArea, reverse=True)[:5]
    tissue_area = 0
    for idx, contour in enumerate(valid):
        area = int(cv2.contourArea(contour))
        tissue_area += area
        x, y, bw, bh = cv2.boundingRect(contour)
        moments = cv2.moments(contour)
        cx = int(moments["m10"] / moments["m00"]) if moments["m00"] else x + bw // 2
        cy = int(moments["m01"] / moments["m00"]) if moments["m00"] else y + bh // 2
        label, color_hex = palette[idx % len(palette)]
        color_bgr = tuple(int(color_hex.strip("#")[i : i + 2], 16) for i in (4, 2, 0))
        cv2.drawContours(overlay, [contour], -1, color_bgr, 2)
        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), color_bgr, 1)
        cv2.putText(
            overlay,
            f"{label}",
            (x, max(y - 8, 15)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color_bgr,
            1,
            cv2.LINE_AA,
        )
        regions.append(
            TissueRegion(
                label=label,
                area_px=area,
                area_pct=round((area / total_px) * 100, 2),
                bbox=(x, y, bw, bh),
                centroid=(cx, cy),
                color_hex=color_hex,
            )
        )
    tissue_coverage_pct = round((tissue_area / total_px) * 100, 2)
    background_pct = round(100 - tissue_coverage_pct, 2)
    return {
        "overlay_bgr": overlay,
        "overlay_pil": bgr_to_pil(overlay),
        "mask": mask,
        "regions": [asdict(r) for r in regions],
        "tissue_coverage_pct": tissue_coverage_pct,
        "background_pct": background_pct,
        "region_count": len(regions),
        "method": "HSV saturation + Otsu + morphological cleanup",
    }
def detect_nuclei(
    image: Image.Image,
    min_area: int = 30,
    max_area: int = 2500,
    min_circularity: float = 0.35,
) -> dict[str, Any]:
    """
    Detect nuclei using hematoxylin channel approximation + adaptive threshold.
    """
    bgr = pil_to_bgr(image)
    h_channel = approximate_hematoxylin_channel(bgr)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(h_channel)
    blur = cv2.GaussianBlur(enhanced, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    overlay = bgr.copy()
    nuclei: list[Nucleus] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        if circularity < min_circularity:
            continue
        
        x, y, bw, bh = cv2.boundingRect(contour)
        moments = cv2.moments(contour)
        cx = int(moments["m10"] / moments["m00"]) if moments["m00"] else x + bw // 2
        cy = int(moments["m01"] / moments["m00"]) if moments["m00"] else y + bh // 2
        
        nuclei.append(Nucleus(cx=cx, cy=cy, area=float(area), circularity=float(circularity), bbox=(x, y, bw, bh)))
        cv2.circle(overlay, (cx, cy), max(2, int(np.sqrt(area / np.pi))), (0, 255, 255), 1)
    
    density_per_mpx = round(len(nuclei) / max((bgr.shape[0] * bgr.shape[1]) / 1_000_000, 0.001), 1)
    
    return {
        "overlay_bgr": overlay,
        "overlay_pil": bgr_to_pil(overlay),
        "binary_mask": binary,
        "nuclei": [asdict(n) for n in nuclei],
        "nuclei_count": len(nuclei),
        "density_per_mpx": density_per_mpx,
        "mean_area": round(float(np.mean([n.area for n in nuclei])) if nuclei else 0.0, 2),
        "method": "Hematoxylin channel + CLAHE + adaptive threshold + contour filtering",
    }


# ---------------------------------------------------------------------------
# Image editing (Upload page: rotate / crop / brightness / contrast)
# ---------------------------------------------------------------------------
def apply_edits(
    image: Image.Image,
    rotation: int = 0,
    brightness: float = 1.0,
    contrast: float = 1.0,
    crop_box_pct: tuple[float, float, float, float] | None = None,
) -> Image.Image:
    """Apply rotate -> crop -> brightness -> contrast, in that order.
    `crop_box_pct` is (left, top, right, bottom) as percentages 0-100."""
    from PIL import ImageEnhance

    out = image
    if rotation:
        out = out.rotate(-rotation, expand=True, fillcolor=(255, 255, 255))
    if crop_box_pct:
        w, h = out.size
        left, top, right, bottom = crop_box_pct
        box = (
            int(w * left / 100),
            int(h * top / 100),
            int(w * (100 - right) / 100),
            int(h * (100 - bottom) / 100),
        )
        if box[2] > box[0] and box[3] > box[1]:
            out = out.crop(box)
    if brightness != 1.0:
        out = ImageEnhance.Brightness(out).enhance(brightness)
    if contrast != 1.0:
        out = ImageEnhance.Contrast(out).enhance(contrast)
    return out


# ---------------------------------------------------------------------------
# Quantitative tissue metrics for the Results Dashboard
# ---------------------------------------------------------------------------
def color_histogram(image: Image.Image, bins: int = 32) -> dict[str, list[float]]:
    """Per-channel RGB histogram, normalized to percentages."""
    rgb = np.array(image.convert("RGB"))
    hist = {}
    for i, channel in enumerate(("red", "green", "blue")):
        counts, _ = np.histogram(rgb[:, :, i], bins=bins, range=(0, 255))
        total = counts.sum() or 1
        hist[channel] = (counts / total * 100).round(3).tolist()
    return hist


def tissue_quality_score(tissue: dict[str, Any], cells: dict[str, Any]) -> dict[str, Any]:
    """Composite 0-100 quality heuristic from measurable signal (focus proxy via nuclei
    circularity + adequate tissue coverage). Not a clinical QC replacement."""
    coverage = tissue.get("tissue_coverage_pct", 0)
    nuclei = cells.get("nuclei", [])
    mean_circularity = float(np.mean([n["circularity"] for n in nuclei])) if nuclei else 0.0
    coverage_score = min(coverage / 60.0, 1.0) * 50  # 60%+ coverage -> full marks
    focus_score = min(mean_circularity / 0.8, 1.0) * 50  # sharper contours -> less blur
    score = round(coverage_score + focus_score, 1)
    if score >= 75:
        label = "Good"
    elif score >= 45:
        label = "Adequate"
    else:
        label = "Suboptimal"
    return {"score": score, "label": label, "mean_circularity": round(mean_circularity, 3)}


def slide_quality_precheck(image: Image.Image) -> dict[str, Any]:
    """Fast QC check run BEFORE the full analysis pipeline, so a blurry or
    badly exposed upload gets flagged immediately instead of producing a
    confident-looking result on unusable input. Two real, standard CV
    techniques, not a heuristic dressed up as one:
      - Blur: variance of the Laplacian (Pech-Pacheco et al., 2000) — sharp
        images have high-frequency edge content and therefore high variance;
        blurry images don't. Below ~100 on a 0-255 image is a common
        rule-of-thumb blur threshold.
      - Exposure: mean + std of pixel intensity flags near-black, near-white,
        or extremely low-contrast (washed out) captures.
    Returns pass/warn/fail per check plus an overall verdict; does not block
    analysis on its own — callers decide whether to warn or refuse."""
    gray = cv2.cvtColor(pil_to_bgr(image), cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_intensity = float(np.mean(gray))
    std_intensity = float(np.std(gray))

    if laplacian_var >= 150:
        blur_status = "pass"
    elif laplacian_var >= 60:
        blur_status = "warn"
    else:
        blur_status = "fail"

    if 15 <= mean_intensity <= 240 and std_intensity >= 15:
        exposure_status = "pass"
    elif 5 <= mean_intensity <= 250 and std_intensity >= 8:
        exposure_status = "warn"
    else:
        exposure_status = "fail"

    statuses = [blur_status, exposure_status]
    if "fail" in statuses:
        verdict = "fail"
    elif "warn" in statuses:
        verdict = "warn"
    else:
        verdict = "pass"

    return {
        "verdict": verdict,
        "blur_status": blur_status,
        "laplacian_variance": round(laplacian_var, 1),
        "exposure_status": exposure_status,
        "mean_intensity": round(mean_intensity, 1),
        "std_intensity": round(std_intensity, 1),
        "method": "Laplacian-variance blur detection + intensity/contrast exposure check",
    }


def estimate_tumor_metrics(tissue: dict[str, Any], cells: dict[str, Any]) -> dict[str, Any]:
    """Heuristic proxies for tumor%, healthy tissue%, inflammation, necrosis, and mitotic
    count, derived from measurable CV features (density, coverage, region count). These
    are NOT validated clinical measurements — replace with real segmentation-model outputs
    (see models/segmentation.py) once trained."""
    coverage = tissue.get("tissue_coverage_pct", 0.0)
    density = cells.get("density_per_mpx", 0.0)
    nuclei = cells.get("nuclei", [])
    region_count = tissue.get("region_count", 0)

    tumor_pct = round(min(90.0, max(0.0, (density - 40) / 4)), 1)
    healthy_pct = round(max(0.0, 100 - tumor_pct - (region_count * 1.5)), 1)
    inflammation_score = round(min(10.0, density / 60), 1)
    necrosis_score = round(min(10.0, max(0.0, (100 - coverage) / 12)), 1)
    # Mitotic figures are irregular, small, high-circularity nuclei — proxy via the
    # smallest-area high-circularity tail of the nuclei population.
    if nuclei:
        areas = np.array([n["area"] for n in nuclei])
        circ = np.array([n["circularity"] for n in nuclei])
        mitotic_like = np.sum((areas < np.percentile(areas, 20)) & (circ > 0.75))
    else:
        mitotic_like = 0

    return {
        "tumor_pct": tumor_pct,
        "healthy_tissue_pct": healthy_pct,
        "inflammation_score": inflammation_score,
        "necrosis_score": necrosis_score,
        "mitotic_count": int(mitotic_like),
        "disclaimer": "Heuristic CV proxy — not a validated clinical measurement.",
    }