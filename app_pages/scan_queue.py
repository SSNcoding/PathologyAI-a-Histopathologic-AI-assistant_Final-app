"""Scan Queue — replaces the old Batch Analysis page.

Real WSI scanner platforms (Aperio eSlide Manager, Philips IMS, Sectra,
Proscia Concentriq) center the operator's view on a fleet dashboard: which
scanners are online, what each has loaded, and a queue of jobs waiting to
run — rather than a bare upload form. This page borrows that framing for
submitting slides into the same batch pipeline (services/batch_service.py)
Batch Analysis used, so the underlying analysis capability isn't lost —
just reframed around how a scanner-equipped lab actually queues work — and
adds a simulated fleet status panel alongside it. See
services/scanner_fleet.py's docstring for exactly what's simulated
(everything scanner-status-related) vs. real (the actual analysis
pipeline underneath).
"""

from __future__ import annotations

import time

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
from services.scanner_fleet import fleet_status
from ui.components import status_badge
from ui.theme import render_page_hero

_STATUS_BADGE_KIND = {"Scanning": "info", "Idle": "success", "Offline": "muted"}


def _render_fleet() -> None:
    st.subheader("Scanner Fleet")
    st.caption(
        "Simulated status for common WSI scanner models — no physical scanner is connected here. "
        "Swap services/scanner_fleet.py for a real device/DICOM/LIS integration when hardware is available."
    )
    fleet = fleet_status(seed=int(time.time()) // 20)
    cols = st.columns(len(fleet))
    for col, unit in zip(cols, fleet):
        with col:
            with st.container(border=True):
                st.markdown(f"**{unit['name']}**")
                st.caption(unit["vendor"])
                status_badge(unit["status"].upper(), _STATUS_BADGE_KIND.get(unit["status"], "info"))
                st.caption(f"{unit['loaded_slides']}/{unit['capacity']} slides loaded · {unit['max_mag']}")
                if unit["status"] == "Scanning":
                    st.progress(unit["progress_pct"] / 100, text=f"Scanning {unit['current_slide']}")


def render() -> None:
    render_page_hero("Scan Queue", "Submit slides to the batch pipeline and watch the simulated scanner fleet")
    user = current_user()
    if not user or not can(user.get("role"), "run_batch_analysis"):
        st.error("Scan Queue isn't available on this role — run individual analyses instead.")
        return

    _render_fleet()
    st.markdown("---")
    st.subheader("Submit to Queue")

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

    if files and st.button("Run Scan Queue", type="primary", use_container_width=True):
        images = [(f.name, Image.open(f).convert("RGB")) for f in files]
        progress = st.progress(0, text="Starting queue...")

        def _cb(i, total, name):
            progress.progress(i / total, text=f"Scanned & analyzed {i}/{total}: {name}")

        results = run_batch_analysis(images, organ=organ_key, architecture=architecture, progress_callback=_cb)
        st.session_state.batch_results = results
        progress.empty()
        st.success(f"Completed scan + analysis on {len(results)} slides.")

    if st.session_state.get("batch_results"):
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
            "Download Scan Queue Results CSV",
            data=batch_results_to_csv_bytes(st.session_state.batch_results),
            file_name="pathologyai_scan_queue_results.csv",
            mime="text/csv",
            type="primary",
        )
