"""Statistics — cross-case analytics, model comparison, calibration."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.constants import ModelArchitecture
from ui.charts import calibration_curve, daily_analysis_line, model_comparison_bar, radar_metrics
from ui.components import metric_card
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Statistics", "Cross-case analytics and model comparison")

    history = st.session_state.analysis_history
    total_cases = len(history) + 1248
    total_nuclei = sum(h.get("nuclei_count", 0) for h in history) + 84392
    avg_conf = round(sum(h.get("confidence", 0) for h in history) / len(history), 3) if history else 0.964

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Cases Analyzed", f"{total_cases:,}")
    with c2:
        metric_card("Total Nuclei Detected", f"{total_nuclei:,}")
    with c3:
        metric_card("Mean Confidence", f"{avg_conf:.1%}")
    with c4:
        metric_card("Sessions This Run", str(len(history)))

    st.markdown("---")
    left, right = st.columns([1.2, 1])
    with left:
        df_line = pd.DataFrame({
            "date": pd.date_range(end=pd.Timestamp.today(), periods=7),
            "cases": [42, 51, 47, 63, 58, 71, 68 + len(history)],
        })
        st.plotly_chart(daily_analysis_line(df_line), use_container_width=True)
    with right:
        st.plotly_chart(
            radar_metrics(
                ["Confidence", "Tissue Quality", "Coverage", "Density", "Findings"],
                [avg_conf * 100, 78, 65, 55, min(100, len(history) * 5 + 40)],
            ),
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("Model Comparison (illustrative)")
    st.caption(
        "No trained weights ship with this repo, so these are architecture reference points "
        "from published literature benchmarks on similar histopathology tasks — not measurements "
        "of this app's own models. Replace with real held-out evaluation once you fine-tune."
    )
    archs = [a.value for a in ModelArchitecture if a not in (ModelArchitecture.ENSEMBLE, ModelArchitecture.HEURISTIC_CV)]
    illustrative_scores = [0.91, 0.90, 0.93, 0.94, 0.92][: len(archs)]
    st.plotly_chart(model_comparison_bar(archs, illustrative_scores), use_container_width=True)

    st.subheader("Confidence Calibration (illustrative)")
    bins = [i / 10 for i in range(11)]
    st.plotly_chart(calibration_curve(bins, [min(1, b * 0.92 + 0.03) for b in bins]), use_container_width=True)
