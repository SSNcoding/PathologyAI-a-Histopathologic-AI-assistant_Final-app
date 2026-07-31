"""Superseded by app_pages/scan_queue.py — kept in place (not deleted) since
app_create.py no longer imports or routes to this module. Scan Queue reuses
the same services/batch_service.run_batch_analysis() this page called, just
reframed around a simulated scanner-fleet dashboard instead of a bare
upload form. Safe to delete once you're sure nothing else references it."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from PIL import Image

from config.settings import SUPPORTED_FORMATS
from core.constants import ModelArchitecture
from core.permissions import can
from core.session_state import current_user
from models.disease_registry import organ_options
from services.batch_service import run_batch_analysis
from services.export_service import batch_results_to_csv_bytes
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Batch Analysis", "Analyze multiple slides in one pass")
    user = current_user()
    if not user or not can(user.get("role"), "run_batch_analysis"):
        st.error("Batch Analysis isn't available on the student role — run individual analyses instead.")
        return

    files = st.file_uploader(
        "Upload multiple slides", type=list(SUPPORTED_FORMATS), accept_multiple_files=True
    )

    organs = organ_options()
    labels = [name for _, name in organs]
    keys = [key for key, _ in organs]
    c1, c2 = st.columns(2)
    with c1:
        organ_label = st.selectbox("Disease / Organ Focus", labels, key="batch_organ")
        organ_key = keys[labels.index(organ_label)]
    with c2:
        architecture = st.selectbox(
            "Model Architecture",
            [a.value for a in ModelArchitecture if a != ModelArchitecture.ENSEMBLE],
            key="batch_arch",
        )

    if files and st.button("Run Batch Analysis", type="primary", use_container_width=True):
        images = [(f.name, Image.open(f).convert("RGB")) for f in files]
        progress = st.progress(0, text="Starting batch...")

        def _cb(i, total, name):
            progress.progress(i / total, text=f"Analyzed {i}/{total}: {name}")

        results = run_batch_analysis(images, organ=organ_key, architecture=architecture, progress_callback=_cb)
        st.session_state.batch_results = results
        progress.empty()
        st.success(f"Completed batch analysis on {len(results)} slides.")

    if st.session_state.batch_results:
        rows = []
        for r in st.session_state.batch_results:
            top = (r.get("findings") or [{}])[0]
            rows.append({
                "Slide": r.get("slide_name"),
                "Top Finding": top.get("label"),
                "Confidence": f"{top.get('confidence', 0):.1%}",
                "Risk": r.get("risk_level"),
                "Nuclei": r["cells"]["nuclei_count"],
                "Tumor %": r["tumor_metrics"]["tumor_pct"],
                "Time (s)": r["processing_time_s"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.download_button(
            "Download Batch CSV",
            data=batch_results_to_csv_bytes(st.session_state.batch_results),
            file_name="pathologyai_batch_results.csv",
            mime="text/csv",
            type="primary",
        )
