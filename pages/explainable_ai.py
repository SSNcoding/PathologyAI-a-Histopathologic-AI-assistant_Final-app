"""Explainable AI — Grad-CAM (neural, once real weights exist) or occlusion-sensitivity
(model-agnostic fallback, works today) with a plain-language explanation of *why*."""

from __future__ import annotations

import streamlit as st
from PIL import Image

from core.session_state import has_image
from models.model_registry import load_disease_classifier
from services.gradcam import explain_with_best_available
from services.image_processor import detect_nuclei
from ui.components import disclaimer_banner, image_preview, no_image_warning, placeholder_notice
from ui.theme import render_page_hero


def _heuristic_abnormality_score(image: Image.Image) -> float:
    """Cheap proxy score (nuclei density on a downscaled patch) used to explain the
    classical-CV heuristic pipeline via occlusion sensitivity."""
    cells = detect_nuclei(image, min_area=15)
    return min(1.0, cells.get("density_per_mpx", 0.0) / 350.0)


def render() -> None:
    render_page_hero("Explainable AI", "See which regions drove the prediction, and why")
    if not has_image():
        no_image_warning("view an explanation")
        return
    if not st.session_state.ai_results:
        st.warning("Run **AI Analysis** first so there is a prediction to explain.")
        return

    data = st.session_state.ai_results
    organ = data.get("organ", "breast")
    architecture = data.get("architecture", "")
    model, _ = load_disease_classifier(organ, architecture) if data.get("model_mode") == "PYTORCH" else (None, None)

    if model is None:
        placeholder_notice(
            "Explanation Method",
            "No trained neural classifier is loaded, so this uses **occlusion sensitivity** "
            "(a model-agnostic, gradient-free technique) over the classical-CV heuristic score. "
            "Once you load real weights, this page automatically switches to true Grad-CAM.",
        )

    # Downscale for speed — occlusion sensitivity requires many forward passes.
    small = st.session_state.current_image.copy()
    small.thumbnail((256, 256))

    with st.spinner("Computing explanation (this runs many small forward passes)..."):
        explanation = explain_with_best_available(
            image=small,
            model=model,
            target_layer=None,
            input_tensor=None,
            fallback_score_fn=_heuristic_abnormality_score,
        )

    st.markdown(f"**Method:** {explanation['method']}")
    if explanation["method"].startswith("Occlusion"):
        disclaimer_banner("This is a heuristic explanation of a non-neural score — not a validated clinical explanation.")

    left, right = st.columns(2)
    with left:
        image_preview(small, "Analyzed region (downscaled for speed)")
    with right:
        image_preview(explanation["overlay"], "Explanation overlay")

    top_finding = data["findings"][0]
    st.subheader("Why this prediction?")
    st.markdown(
        f"The model's top finding is **{top_finding['label']}** at **{top_finding['confidence']:.0%}** "
        f"confidence. The highlighted (red/yellow) regions above are the areas that most increased "
        f"the model's abnormality score when present — removing them dropped the score the most. "
        f"Tissue coverage was **{data['tissue']['tissue_coverage_pct']}%** and nuclei density was "
        f"**{data['cells']['density_per_mpx']}/Mpx**, both of which feed directly into the heuristic "
        f"scoring function in `services/ai_analyzer.py`."
    )
