import streamlit as st
from core.session_state import has_image
from services.image_processor import detect_tissue_regions
from ui.components import image_preview, no_image_warning, placeholder_notice, status_badge
from ui.theme import render_page_hero
def render() -> None:
    render_page_hero("Tissue Detection", "Segment tissue from background using classical computer vision")
    if not has_image():
        no_image_warning("run tissue detection")
        return
    placeholder_notice(
        "Model Status",
        "Using OpenCV HSV + Otsu segmentation. Drop weights in `models/weights/tissue_classifier.pt` for DL inference.",
    )
    if st.button("Run Tissue Segmentation", type="primary", use_container_width=True):
        with st.spinner("Segmenting tissue regions..."):
            results = detect_tissue_regions(st.session_state.current_image)
            st.session_state.tissue_results = results
    results = st.session_state.tissue_results
    if not results:
        image_preview(st.session_state.current_image, "Original slide")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Tissue Coverage", f"{results['tissue_coverage_pct']}%")
    c2.metric("Regions Detected", results["region_count"])
    c3.metric("Method", "OpenCV")
    left, right = st.columns(2)
    with left:
        image_preview(st.session_state.current_image, "Original")
    with right:
        image_preview(results["overlay_pil"], "Tissue overlay")
    st.dataframe(results["regions"], use_container_width=True, hide_index=True)
    status_badge("CV Pipeline Active", "success")
