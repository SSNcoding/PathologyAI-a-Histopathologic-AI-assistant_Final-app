"""AI Analysis Dashboard — organ + architecture selection, progress animation,
confidence meter, probability graph, tissue quality, segmentation preview,
processing time, and model used."""

from __future__ import annotations

import time

import streamlit as st

from core.constants import DIAGNOSIS_SEVERITY, ModelArchitecture
from core.session_state import has_image
from models.disease_registry import get_organ, organ_options
from services.ai_analyzer import result_to_dict, run_full_analysis
from ui.charts import confidence_bar, gauge_chart
from ui.components import disclaimer_banner, image_preview, no_image_warning, status_badge
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("AI Analysis", "End-to-end slide analysis with confidence scoring and heatmaps")
    if not has_image():
        no_image_warning("run AI analysis")
        return

    organs = organ_options()
    labels = [name for _, name in organs]
    keys = [key for key, _ in organs]
    default_idx = keys.index(st.session_state.selected_organ) if st.session_state.selected_organ in keys else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        organ_label = st.selectbox("Disease / Organ Focus", labels, index=default_idx)
        organ_key = keys[labels.index(organ_label)]
    with c2:
        architecture = st.selectbox("Model Architecture", [a.value for a in ModelArchitecture if a != ModelArchitecture.ENSEMBLE])
    with c3:
        use_tta = st.toggle("Test-Time Augmentation", value=st.session_state.use_tta)

    st.session_state.selected_organ = organ_key
    st.session_state.selected_architecture = architecture
    st.session_state.use_tta = use_tta

    disease_organ = get_organ(organ_key)
    st.caption(f"Class taxonomy: {', '.join(disease_organ.classes)}")

    if st.button("Run Full AI Analysis", type="primary", use_container_width=True):
        progress = st.progress(0, text="Segmenting tissue...")
        steps = [
            (20, "Segmenting tissue regions..."),
            (45, "Detecting nuclei..."),
            (65, "Scoring classification..."),
            (85, "Generating heatmap..."),
            (100, "Finalizing report data..."),
        ]
        for pct, label in steps:
            time.sleep(0.15)
            progress.progress(pct, text=label)

        result = run_full_analysis(
            st.session_state.current_image,
            organ=organ_key,
            architecture=architecture,
            use_tta=use_tta,
        )
        st.session_state.ai_results = result_to_dict(result)
        st.session_state.tissue_results = result.tissue
        st.session_state.cell_results = result.cells
        st.session_state.heatmap_image = result.heatmap
        st.session_state.last_processing_time_s = result.processing_time_s
        st.session_state.analysis_history.append({
            "slide": st.session_state.current_image_name,
            "organ": organ_key,
            "nuclei_count": result.cells["nuclei_count"],
            "confidence": result.confidence,
            "risk_level": result.risk_level,
        })
        progress.empty()

    data = st.session_state.ai_results
    if not data:
        image_preview(st.session_state.current_image)
        return

    risk = DIAGNOSIS_SEVERITY.get(data["risk_level"], DIAGNOSIS_SEVERITY["low"])
    badge_kind = {"low": "success", "moderate": "warning", "high": "danger"}[data["risk_level"]]

    if data["model_mode"] == "HEURISTIC_PLACEHOLDER":
        disclaimer_banner(
            "Running in HEURISTIC_PLACEHOLDER mode — this prediction comes from classical "
            "computer-vision features, not a trained neural network. Not for clinical use."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall Confidence", f"{data['confidence']:.1%}")
    c2.metric("Risk Level", risk["label"])
    c3.metric("Processing Time", f"{data['processing_time_s']:.2f}s")
    c4.metric("Model Used", data["architecture"])
    status_badge(f"{data['model_mode']} — NOT FOR CLINICAL USE", badge_kind if data["model_mode"] == "PYTORCH" else "warning")

    st.markdown(data["summary"])

    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(gauge_chart(data["confidence"], "Confidence Meter", max_value=1.0, suffix=""), use_container_width=True)
    with g2:
        st.plotly_chart(gauge_chart(data["quality"]["score"], "Tissue Quality", max_value=100), use_container_width=True)
    with g3:
        st.plotly_chart(gauge_chart(data["tumor_metrics"]["tumor_pct"], "Tumor % (heuristic)", max_value=100), use_container_width=True)

    finding_labels = [f["label"] for f in data["findings"]]
    scores = [f["confidence"] for f in data["findings"]]
    st.plotly_chart(confidence_bar(finding_labels, scores), use_container_width=True)

    calibration = data.get("calibration_samples")
    if calibration:
        import statistics as _stats
        spread = max(calibration) - min(calibration)
        stdev = _stats.pstdev(calibration) if len(calibration) > 1 else 0.0
        st.subheader("Confidence Calibration")
        st.caption(
            "Test-Time Augmentation ran the winning class's probability across "
            f"{len(calibration)} augmented views (identity, flips, rotation) instead of "
            "just once. A tight spread means the model agrees with itself across views; "
            "a wide spread means the single confidence number above is less trustworthy "
            "than it looks."
        )
        cc1, cc2, cc3 = st.columns(3)
        cc1.metric("View-to-view spread", f"{spread:.1%}")
        cc2.metric("Std. deviation", f"{stdev:.1%}")
        cc3.metric("Views agreeing (±5%)", f"{sum(1 for v in calibration if abs(v - data['confidence']) <= 0.05)}/{len(calibration)}")
    elif data["model_mode"] == "PYTORCH":
        st.caption("Enable Test-Time Augmentation above to see confidence calibration across augmented views.")

    precheck = data.get("quality_precheck")
    if precheck and precheck["verdict"] != "pass":
        kind = "danger" if precheck["verdict"] == "fail" else "warning"
        status_badge(f"Slide quality: {precheck['verdict'].upper()} — see Upload page for details", kind)

    left, right = st.columns(2)
    with left:
        image_preview(st.session_state.heatmap_image, "Attention / saliency heatmap")
    with right:
        image_preview(st.session_state.cell_results["overlay_pil"], "Nuclei / segmentation preview")
