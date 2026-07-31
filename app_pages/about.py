"""About page — mission, technology, and honesty-first disclosure of what's real."""

from __future__ import annotations

import streamlit as st

from config.settings import APP_NAME, APP_VERSION, ORGANIZATION
from ui.components import feature_card, research_only_notice
from ui.landing import render_footer
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("About PathologyAI", "A research & education platform for computational pathology")

    st.markdown(
        f"""
        {APP_NAME} (v{APP_VERSION}) is built by **{ORGANIZATION}** as a research and
        educational prototype demonstrating how computer vision and deep learning can
        assist — never replace — pathologist review of histopathology slides.
        """
    )

    st.subheader("What's real vs. in-progress")
    c1, c2 = st.columns(2)
    with c1:
        feature_card("✅", "Working today",
                      "Classical CV tissue segmentation, nuclei detection, heatmaps, PDF/CSV/JSON "
                      "reports, whole-slide pan/zoom viewer, and a modular 10-organ disease registry.")
    with c2:
        feature_card("\U0001F6E0️", "Real code, needs your weights",
                      "ResNet50/DenseNet121/EfficientNet-B0/ConvNeXt/ViT backbones, a U-Net "
                      "segmentation architecture, Grad-CAM/Grad-CAM++, ensembling, and TTA are all "
                      "implemented — they activate automatically once you drop trained checkpoints "
                      "into models/weights/.")

    research_only_notice(
        "Cancer Staging, Survival Risk, Biomarker Prediction",
        "These require clinical/molecular data beyond a single image and are intentionally "
        "not implemented as live features — see Explainable AI and Statistics pages for what "
        "image-only analysis can responsibly support today.",
    )

    st.subheader("Recommended datasets & literature")
    st.markdown(
        "CAMELYON16/17 · PANDA · BreakHis · LC25000 · PCam · TCGA · The Cancer Imaging Archive (TCIA) "
        "— referenced per-organ in `models/disease_registry.py`."
    )
    render_footer()
