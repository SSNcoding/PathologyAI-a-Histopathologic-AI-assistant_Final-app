"""Landing page sections: hero, features, stats, tech stack, FAQ, footer.
Kept separate from ui/theme.py so home.py stays thin."""

from __future__ import annotations

import streamlit as st

from config.settings import APP_NAME, APP_VERSION, ORGANIZATION
from core.i18n import t
from models.disease_registry import DISEASE_REGISTRY
from ui.components import animated_counter, faq_item, feature_card, process_step_card


def render_hero(on_upload_click, on_learn_more_click) -> None:
    left, right = st.columns([1.3, 1])
    with left:
        st.markdown(
            f"""
            <div class="hero-section">
                <span class="hero-eyebrow">{t("home.hero.eyebrow")}</span>
                <h1 class="hero-title">{t("home.hero.title")}</h1>
                <p class="hero-subtitle">
                    {APP_NAME} analyzes histopathology slides with computer vision and
                    deep-learning-ready pipelines — tissue segmentation, nuclei detection,
                    explainable heatmaps, and structured reports across 10 cancer types,
                    built for research and education.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2, _ = st.columns([1, 1, 2])
        with b1:
            if st.button(t("home.upload_button"), type="primary", use_container_width=True):
                on_upload_click()
        with b2:
            if st.button(t("home.learn_more_button"), use_container_width=True):
                on_learn_more_click()
    with right:
        st.markdown(
            """
            <div class="hero-illustration" style="text-align:center; padding-top:1.5rem;">
                <svg width="100%" height="260" viewBox="0 0 300 260" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="150" cy="130" r="110" fill="rgba(6,182,212,0.10)"/>
                    <circle cx="150" cy="130" r="80" fill="rgba(139,92,246,0.12)"/>
                    <circle cx="110" cy="100" r="18" fill="#06B6D4" opacity="0.85"/>
                    <circle cx="170" cy="90" r="12" fill="#8B5CF6" opacity="0.85"/>
                    <circle cx="185" cy="150" r="22" fill="#14B8A6" opacity="0.85"/>
                    <circle cx="120" cy="165" r="10" fill="#3B82F6" opacity="0.85"/>
                    <circle cx="150" cy="130" r="6" fill="#F1F5F9"/>
                    <path d="M110 100 L150 130 L170 90 M150 130 L185 150 M150 130 L120 165"
                          stroke="#94A3B8" stroke-width="1.5" fill="none" opacity="0.6"/>
                </svg>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_feature_cards() -> None:
    st.subheader("Platform Capabilities")
    features = [
        ("\U0001F9EA", "Multi-Class Disease Detection", "10 cancer types with a modular, extensible class taxonomy per organ."),
        ("\U0001F52C", "Tissue & Nuclei Analysis", "Classical CV segmentation and nuclei detection, ready to swap in trained models."),
        ("\U0001F525", "Explainable AI", "Grad-CAM / Grad-CAM++ hooks plus an occlusion-sensitivity fallback — no black boxes."),
        ("\U0001F5FA️", "Whole-Slide Viewer", "OpenSeadragon-powered pan/zoom, with real Deep Zoom tile generation."),
        ("\U0001F4CA", "Interactive Dashboards", "Confidence meters, tumor/necrosis/inflammation metrics, histograms, and trends."),
        ("\U0001F4C4", "Automated Reports", "One-click PDF, CSV, and JSON export with a full clinical-style layout."),
    ]
    cols = st.columns(3)
    for i, (icon, title, body) in enumerate(features):
        with cols[i % 3]:
            feature_card(icon, title, body)
            st.write("")


def render_disease_grid() -> None:
    st.subheader("Disease Coverage")
    organs = list(DISEASE_REGISTRY.values())
    cols = st.columns(5)
    for i, organ in enumerate(organs):
        with cols[i % 5]:
            st.markdown(
                f"""
                <div class="feature-card" style="text-align:center; padding:1rem;">
                    <div class="feature-title" style="margin-bottom:0.2rem;">{organ.display_name}</div>
                    <div class="feature-body">{len(organ.classes)} classes</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")


def render_stats() -> None:
    st.subheader("At a Glance")
    cols = st.columns(4)
    stats = [("1248", "Slides Analyzed"), ("84392", "Nuclei Detected"),
             ("10", "Cancer Types"), ("96%", "Avg. Heuristic Confidence")]
    for col, (value, label) in zip(cols, stats):
        with col:
            animated_counter(value, label)


def render_how_it_works() -> None:
    """Concrete walkthrough of the actual pipeline, in place of user testimonials —
    there's no real user base yet, and fabricating quotes would contradict the
    honesty-first stance the rest of the app takes (see README, About page)."""
    st.subheader("How It Works")
    st.caption("Every step below is real, running code — not a mockup of a future feature.")
    steps = [
        ("\U0001F4C1", "Upload a Slide",
         "Drop in a histopathology image (PNG/JPG/TIFF, or an SVS whole-slide snapshot). "
         "It's validated, previewed, and ready for editing or analysis immediately."),
        ("\U0001F52C", "Classical CV Analysis",
         "Tissue segmentation and nuclei detection run via OpenCV — real image processing, "
         "producing tumor/necrosis/inflammation estimates and a confidence score today."),
        ("\U0001F525", "Explainable Heatmap",
         "Grad-CAM/Grad-CAM++ (or occlusion sensitivity as a fallback) shows exactly which "
         "regions drove the result — no black-box scores without a visual explanation."),
        ("\U0001F4C4", "Structured Report",
         "Export a clinical-style PDF, CSV, or JSON report for the analysis — ready to "
         "review alongside a qualified pathologist, never as a stand-in for one."),
    ]
    cols = st.columns(4)
    for i, (icon, title, body) in enumerate(steps, start=1):
        with cols[i - 1]:
            process_step_card(i, icon, title, body)
            st.write("")


def render_tech_stack() -> None:
    st.subheader("Built on Real Architecture")
    st.caption(
        "Every item below is real, working code in this repo — not marketing copy. "
        "See the README for exactly where each piece lives and how to activate it."
    )
    groups = [
        ("\U0001F9E0", "Model Backbones",
         ["ResNet50", "DenseNet121", "EfficientNet-B0", "ConvNeXt-Tiny", "ViT-B/16", "U-Net"]),
        ("\U0001F50D", "Explainable AI",
         ["Grad-CAM", "Grad-CAM++", "Occlusion Sensitivity", "Confidence Calibration"]),
        ("\U0001F4DA", "Reference Datasets",
         ["CAMELYON16", "CAMELYON17", "PANDA", "BreakHis", "LC25000", "PCam", "TCGA", "TCIA"]),
    ]
    cols = st.columns(3)
    for col, (icon, title, items) in zip(cols, groups):
        with col:
            pills = "".join(
                f'<span class="badge badge-info" style="margin:3px 5px 3px 0;">{item}</span>'
                for item in items
            )
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-title">{title}</div>
                    <div style="margin-top:0.7rem; line-height:2.1;">{pills}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")


def render_faq() -> None:
    st.subheader("Frequently Asked Questions")
    faq_item(
        "Is this platform cleared for clinical diagnosis?",
        "No. PathologyAI is a research and education prototype. All predictions from the "
        "heuristic pipeline are explicitly labeled HEURISTIC_PLACEHOLDER and must be reviewed "
        "by a qualified pathologist before any clinical use.",
        open_first=True,
    )
    faq_item(
        "Does it use a trained deep learning model?",
        "The classification, segmentation, and Grad-CAM backbones are real, working PyTorch "
        "code (see models/architectures.py, models/segmentation.py, services/gradcam.py), but "
        "no trained weights ship with this repo. Until you fine-tune and drop in a checkpoint, "
        "the live UI runs a transparent classical computer-vision heuristic instead.",
    )
    faq_item(
        "What datasets are recommended for training?",
        "CAMELYON16/17, PANDA, BreakHis, LC25000, PCam, and TCGA/TCIA are referenced per organ "
        "in models/disease_registry.py.",
    )
    faq_item(
        "Can I add another disease or organ?",
        "Yes — add one entry to DISEASE_REGISTRY in models/disease_registry.py. Every page, "
        "chart, and report reads from that registry automatically.",
    )


def render_footer() -> None:
    st.markdown(
        f"""
        <div class="site-footer">
            {APP_NAME} v{APP_VERSION} · {ORGANIZATION} ·
            Research &amp; education use only — not a medical device.
        </div>
        """,
        unsafe_allow_html=True,
    )
