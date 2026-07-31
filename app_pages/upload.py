"""Slide upload — drag & drop, live preview, rotate/crop/brightness/contrast editing,
OpenSeadragon deep-zoom preview, and a batch-upload path for Scan Queue."""

from __future__ import annotations

import time

import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from config.settings import MAX_UPLOAD_MB, SUPPORTED_FORMATS
from core.session_state import reset_analysis, reset_image_edits
from services.demo_slide import DEMO_SLIDE_NAME, generate_demo_slide
from services.image_processor import apply_edits, slide_quality_precheck
from services.wsi_service import image_to_data_uri
from ui.components import image_preview, info_card, status_badge
from ui.theme import render_page_hero


def _openseadragon_viewer(image: Image.Image, height: int = 480) -> None:
    data_uri = image_to_data_uri(image)
    html = f"""
    <div id="osd-viewer" style="width:100%; height:{height}px; border-radius:14px; overflow:hidden;
         border:1px solid rgba(148,163,184,0.25);"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/openseadragon.min.js"></script>
    <script>
        OpenSeadragon({{
            id: "osd-viewer",
            prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
            tileSources: {{ type: "image", url: "{data_uri}" }},
            showNavigator: true,
            navigatorPosition: "BOTTOM_RIGHT",
            gestureSettingsMouse: {{ scrollToZoom: true }},
        }});
    </script>
    """
    components.html(html, height=height + 10)


def render() -> None:
    render_page_hero("Slide Upload", "Import histopathology images for computational analysis")
    info_card(
        "Supported Formats",
        f"{', '.join(SUPPORTED_FORMATS).upper()} — max {MAX_UPLOAD_MB} MB per slide. "
        "Native .svs pyramidal files require OpenSlide (see README); this uploader accepts "
        "standard image formats and any .svs export flattened to TIFF/PNG.",
    )

    uc1, uc2 = st.columns([3, 1])
    with uc1:
        uploaded = st.file_uploader(
            "Drag and drop a histopathology slide here, or click to browse",
            type=list(SUPPORTED_FORMATS),
            help="Whole-slide snapshots or ROI crops at typical H&E magnification.",
        )
    with uc2:
        st.write("")
        st.write("")
        if st.button("\U0001F9EA Try a Demo Slide", use_container_width=True,
                     help="Loads a procedurally generated synthetic image — not a real slide — "
                          "so you can try the pipeline without your own image."):
            demo_image = generate_demo_slide()
            st.session_state.original_image = demo_image
            st.session_state.current_image = demo_image
            st.session_state.current_image_name = DEMO_SLIDE_NAME
            st.session_state.current_image_array = np.array(demo_image)
            reset_analysis()
            reset_image_edits()
            st.session_state.upload_quality_precheck = slide_quality_precheck(demo_image)
            st.rerun()

    if st.session_state.current_image_name == DEMO_SLIDE_NAME:
        st.warning(
            "This is a **synthetic, procedurally generated** demo image, not a real "
            "histopathology slide — it exists only to exercise the pipeline end-to-end. "
            "Upload a real slide above for anything meaningful."
        )

    if uploaded:
        size_mb = len(uploaded.getvalue()) / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            st.error(f"File exceeds {MAX_UPLOAD_MB} MB limit.")
            return

        if st.session_state.current_image_name != uploaded.name:
            progress = st.progress(0, text="Reading file...")
            for pct, label in [(30, "Decoding image..."), (65, "Preparing preview..."), (100, "Done")]:
                time.sleep(0.12)
                progress.progress(pct, text=label)
            image = Image.open(uploaded).convert("RGB")
            st.session_state.original_image = image
            st.session_state.current_image = image
            st.session_state.current_image_name = uploaded.name
            st.session_state.current_image_array = np.array(image)
            reset_analysis()
            reset_image_edits()
            st.session_state.upload_quality_precheck = slide_quality_precheck(image)
            st.success(f"Loaded **{uploaded.name}** ({image.size[0]}×{image.size[1]} px, {size_mb:.2f} MB)")

    if not st.session_state.current_image:
        st.markdown('<div class="upload-hint">No slide loaded yet — drop a file above to begin.</div>', unsafe_allow_html=True)
        return

    precheck = st.session_state.get("upload_quality_precheck")
    if precheck:
        verdict_kind = {"pass": "success", "warn": "warning", "fail": "danger"}[precheck["verdict"]]
        c1, c2 = st.columns([1, 3])
        with c1:
            status_badge(f"Quality check: {precheck['verdict'].upper()}", verdict_kind)
        with c2:
            if precheck["verdict"] == "pass":
                st.caption(f"Sharpness and exposure look fine for analysis (blur variance {precheck['laplacian_variance']}).")
            elif precheck["verdict"] == "warn":
                st.caption(
                    f"Borderline sharpness/exposure (blur variance {precheck['laplacian_variance']}, "
                    f"mean intensity {precheck['mean_intensity']}) — results may be less reliable."
                )
            else:
                st.caption(
                    f"This slide looks blurry or poorly exposed (blur variance {precheck['laplacian_variance']}, "
                    f"mean intensity {precheck['mean_intensity']}). Consider re-scanning before analysis."
                )

    st.markdown("---")
    tab_edit, tab_zoom = st.tabs(["\U0001F527 Edit & Preview", "\U0001F5FA️ Deep Zoom Viewer"])

    with tab_edit:
        c1, c2 = st.columns([1.3, 1])
        with c2:
            st.subheader("Adjust")
            rotation = st.select_slider("Rotate", options=[0, 90, 180, 270], value=st.session_state.edit_rotation)
            brightness = st.slider("Brightness", 0.3, 2.0, st.session_state.edit_brightness, 0.05)
            contrast = st.slider("Contrast", 0.3, 2.0, st.session_state.edit_contrast, 0.05)
            st.caption("Crop (% from each edge)")
            cc1, cc2 = st.columns(2)
            with cc1:
                crop_left = st.slider("Left", 0, 45, 0)
                crop_top = st.slider("Top", 0, 45, 0)
            with cc2:
                crop_right = st.slider("Right", 0, 45, 0)
                crop_bottom = st.slider("Bottom", 0, 45, 0)

            st.session_state.edit_rotation = rotation
            st.session_state.edit_brightness = brightness
            st.session_state.edit_contrast = contrast
            st.session_state.edit_crop = (crop_left, crop_top, crop_right, crop_bottom)

            if st.button("Reset Edits", use_container_width=True):
                reset_image_edits()
                st.rerun()

        edited = apply_edits(
            st.session_state.original_image,
            rotation=st.session_state.edit_rotation,
            brightness=st.session_state.edit_brightness,
            contrast=st.session_state.edit_contrast,
            crop_box_pct=st.session_state.edit_crop,
        )
        st.session_state.current_image = edited
        st.session_state.current_image_array = np.array(edited)

        with c1:
            image_preview(edited, caption=st.session_state.current_image_name)
            w, h = edited.size
            m1, m2 = st.columns(2)
            m1.metric("Width", f"{w} px")
            m2.metric("Height", f"{h} px")

    with tab_zoom:
        st.caption("Pan and scroll to zoom — powered by OpenSeadragon.")
        _openseadragon_viewer(st.session_state.current_image)
