"""Results Dashboard — the full quantitative results view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.session_state import current_user, is_authenticated
from services.analysis_store import save_analysis
from services.export_service import result_to_csv_bytes, result_to_json_bytes
from services.image_processor import color_histogram
from services.notification_service import create_notification
from ui.charts import (
    color_histogram_chart,
    confidence_bar,
    nuclei_size_histogram,
    tissue_composition_pie,
    tumor_healthy_donut,
)
from ui.components import disease_badge, image_preview, metric_card, status_badge
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Results Dashboard", "Full quantitative breakdown of the most recent analysis")
    data = st.session_state.ai_results
    if not data:
        st.warning("Run **AI Analysis** first to populate the results dashboard.")
        return

    tissue = data["tissue"]
    cells = data["cells"]
    tumor = data["tumor_metrics"]
    quality = data["quality"]
    top_finding = data["findings"][0]

    st.subheader("Prediction Summary")
    disease_badge(top_finding["label"], top_finding["confidence"])
    status_badge(data["model_mode"], "warning" if data["model_mode"] == "HEURISTIC_PLACEHOLDER" else "success")

    row1 = st.columns(4)
    with row1[0]:
        metric_card("Predicted Class", top_finding["label"])
    with row1[1]:
        metric_card("Confidence", f"{data['confidence']:.1%}")
    with row1[2]:
        metric_card("Risk Level", data["risk_level"].title())
    with row1[3]:
        metric_card("Processing Time", f"{data['processing_time_s']:.2f}s")

    row2 = st.columns(5)
    with row2[0]:
        metric_card("Nuclei Count", f"{cells['nuclei_count']:,}")
    with row2[1]:
        metric_card("Tumor %", f"{tumor['tumor_pct']}%")
    with row2[2]:
        metric_card("Healthy Tissue %", f"{tumor['healthy_tissue_pct']}%")
    with row2[3]:
        metric_card("Inflammation", f"{tumor['inflammation_score']}/10")
    with row2[4]:
        metric_card("Necrosis", f"{tumor['necrosis_score']}/10")

    row3 = st.columns(3)
    with row3[0]:
        metric_card("Mitotic-like Count", str(tumor["mitotic_count"]))
    with row3[1]:
        metric_card("Tissue Quality", f"{quality['label']} ({quality['score']}/100)")
    with row3[2]:
        metric_card("Tissue Regions", str(tissue["region_count"]))

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        image_preview(data["heatmap"], "Heatmap")
    with right:
        image_preview(st.session_state.cell_results["overlay_pil"], "Segmentation / nuclei overlay")

    st.markdown("---")
    st.subheader("Charts")
    ch1, ch2 = st.columns(2)
    with ch1:
        regions = tissue.get("regions", [])
        df = pd.DataFrame([{"region": r["label"], "area_pct": r["area_pct"]} for r in regions]) if regions else \
            pd.DataFrame({"region": ["Tissue"], "area_pct": [tissue["tissue_coverage_pct"]]})
        st.plotly_chart(tissue_composition_pie(df), use_container_width=True)
    with ch2:
        st.plotly_chart(tumor_healthy_donut(tumor["tumor_pct"], tumor["healthy_tissue_pct"]), use_container_width=True)

    ch3, ch4 = st.columns(2)
    with ch3:
        sizes = [n["area"] for n in cells.get("nuclei", [])]
        if sizes:
            st.plotly_chart(nuclei_size_histogram(sizes), use_container_width=True)
    with ch4:
        labels = [f["label"] for f in data["findings"]]
        scores = [f["confidence"] for f in data["findings"]]
        st.plotly_chart(confidence_bar(labels, scores), use_container_width=True)

    hist = color_histogram(st.session_state.current_image)
    st.plotly_chart(color_histogram_chart(hist), use_container_width=True)

    st.markdown("---")
    st.subheader("Export")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button("Download JSON", data=result_to_json_bytes(data), file_name="pathologyai_result.json",
                            mime="application/json", use_container_width=True)
    with e2:
        st.download_button("Download CSV", data=result_to_csv_bytes(data), file_name="pathologyai_result.csv",
                            mime="text/csv", use_container_width=True)
    with e3:
        if is_authenticated():
            if st.button("Save to Profile", type="primary", use_container_width=True):
                user = current_user()
                enriched = dict(data)
                enriched["slide_name"] = st.session_state.current_image_name
                save_analysis(user["id"], enriched)
                create_notification(user["id"], "Analysis saved",
                                     f"{st.session_state.current_image_name} saved to your profile.")
                st.success("Saved to your profile.")
        else:
            st.caption("Log in to save this analysis to your profile.")
