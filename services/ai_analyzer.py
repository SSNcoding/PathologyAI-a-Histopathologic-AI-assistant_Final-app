"""Orchestrates tissue + nuclei analysis and produces an AI-style summary.

Organ-aware and architecture-aware: if a real trained checkpoint exists for
the selected organ + architecture (see models/model_registry.py), this
module runs genuine neural inference (optionally with an ensemble and/or
test-time augmentation). Otherwise it transparently falls back to the
classical-CV heuristic pipeline that has always shipped with this app, and
labels every result `model_mode="HEURISTIC_PLACEHOLDER"` so the UI can warn
the user accordingly.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from PIL import Image

from models.disease_registry import get_organ
from models.model_registry import get_checkpoint_version, load_disease_classifier
from services.heatmap_generator import generate_attention_heatmap
from services.image_processor import (
    detect_nuclei,
    detect_tissue_regions,
    estimate_tumor_metrics,
    slide_quality_precheck,
    tissue_quality_score,
)

# Bump this when _heuristic_classification's scoring formula changes, so
# saved results/reports can tell which heuristic version produced them —
# the same idea as model-version tagging, applied to the non-neural path.
HEURISTIC_VERSION = "heuristic-cv-v1"


@dataclass
class AIAnalysisResult:
    timestamp: str
    summary: str
    risk_level: str
    confidence: float
    findings: list[dict[str, Any]]
    tissue: dict[str, Any]
    cells: dict[str, Any]
    heatmap: Image.Image
    model_mode: str
    organ: str
    architecture: str
    processing_time_s: float
    tumor_metrics: dict[str, Any]
    quality: dict[str, Any]
    model_version: str | None = None
    calibration_samples: list[float] | None = None
    quality_precheck: dict[str, Any] | None = None


def _heuristic_classification(organ: str, tissue: dict, cells: dict) -> tuple[str, str, float, list[dict], str]:
    """
    Placeholder classifier until PyTorch model weights are wired in.
    Uses measurable CV features — NOT a diagnostic claim. Organ-aware: maps the
    generic heuristic pattern onto that organ's actual class taxonomy so the UI
    displays disease-specific labels even without a trained model.
    """
    disease_organ = get_organ(organ)
    classes = disease_organ.classes  # e.g. ["Benign", "DCIS", "Invasive Ductal Carcinoma", ...]
    benign_label = classes[0]
    malignant_labels = classes[1:] or [benign_label]

    coverage = tissue.get("tissue_coverage_pct", 0)
    nuclei_count = cells.get("nuclei_count", 0)
    density = cells.get("density_per_mpx", 0)

    # Distribute a hypercellularity-driven pseudo-score across this organ's real
    # class list (benign gets the complement of density-derived "abnormality").
    abnormality = min(0.92, density / 350)
    benign_score = max(0.05, 1.0 - abnormality)
    remaining = max(0.0, 1.0 - benign_score)
    n_malignant = len(malignant_labels)
    scores = {benign_label: benign_score}
    for i, label in enumerate(malignant_labels):
        # Weight later (more severe) classes higher as density increases.
        weight = (i + 1) / sum(range(1, n_malignant + 1)) if n_malignant else 0
        scores[label] = round(remaining * weight * (1 + i * 0.15), 4)

    total = sum(scores.values()) or 1.0
    scores = {k: v / total for k, v in scores.items()}
    top_label = max(scores, key=scores.get)
    confidence = float(scores[top_label])

    if top_label == benign_label:
        risk = "low"
    elif confidence > 0.55:
        risk = "high"
    else:
        risk = "moderate"

    findings = [
        {"label": label, "confidence": round(score, 3)}
        for label, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
    summary = (
        f"Heuristic analysis of this **{disease_organ.display_name}** slide suggests predominant "
        f"pattern: **{top_label}** (confidence {confidence:.0%}). "
        f"Tissue coverage {coverage:.1f}%, nuclei density {density:.1f}/Mpx across {nuclei_count} detected nuclei. "
        "_Not a clinical diagnosis — requires pathologist review._"
    )
    return top_label, summary, confidence, findings, risk


def run_full_analysis(
    image: Image.Image,
    organ: str = "breast",
    architecture: str = "Classical CV Heuristic (no trained weights)",
    use_ensemble: bool = False,
    use_tta: bool = False,
) -> AIAnalysisResult:
    start = time.perf_counter()

    quality_precheck = slide_quality_precheck(image)
    tissue = detect_tissue_regions(image)
    cells = detect_nuclei(image)
    points = [(n["cx"], n["cy"]) for n in cells.get("nuclei", [])]
    heatmap = generate_attention_heatmap(image, points)
    tumor_metrics = estimate_tumor_metrics(tissue, cells)
    quality = tissue_quality_score(tissue, cells)

    model, class_names = load_disease_classifier(organ, architecture)
    model_mode = "HEURISTIC_PLACEHOLDER"
    used_architecture = "Classical CV Heuristic (no trained weights)"
    model_version = HEURISTIC_VERSION
    calibration_samples = None

    if model is not None:
        # Real neural path — only reachable once a checkpoint is dropped in models/weights/.
        from models.architectures import predict_single, predict_with_tta

        if use_tta:
            prediction = predict_with_tta(model, image, class_names, architecture)
        else:
            prediction = predict_single(model, image, class_names, architecture)
        top_label = prediction.top_class
        confidence = prediction.top_confidence
        findings = [
            {"label": k, "confidence": round(v, 3)}
            for k, v in sorted(prediction.class_probs.items(), key=lambda x: x[1], reverse=True)
        ]
        top_idx = class_names.index(top_label)
        risk = "high" if top_idx > 0 and confidence > 0.55 else ("moderate" if top_idx > 0 else "low")
        summary = f"Neural inference ({prediction.architecture}) predicts **{top_label}** with {confidence:.0%} confidence."
        model_mode = "PYTORCH"
        used_architecture = prediction.architecture
        model_version = get_checkpoint_version(organ, architecture) or "unknown-checkpoint"
        calibration_samples = prediction.calibration_samples
    else:
        top_label, summary, confidence, findings, risk = _heuristic_classification(organ, tissue, cells)
        used_architecture = architecture if architecture else used_architecture

    elapsed = round(time.perf_counter() - start, 3)

    return AIAnalysisResult(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        summary=summary,
        risk_level=risk,
        confidence=confidence,
        findings=findings,
        tissue=tissue,
        cells=cells,
        heatmap=heatmap,
        model_mode=model_mode,
        organ=organ,
        architecture=used_architecture,
        processing_time_s=elapsed,
        tumor_metrics=tumor_metrics,
        quality=quality,
        model_version=model_version,
        calibration_samples=calibration_samples,
        quality_precheck=quality_precheck,
    )


def result_to_dict(result: AIAnalysisResult) -> dict:
    data = asdict(result)
    data["heatmap"] = result.heatmap  # keep PIL object out of deep copy issues
    return data
