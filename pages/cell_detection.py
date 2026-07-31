import streamlit as st
from core.session_state import has_image
from services.image_processor import detect_nuclei
from ui.charts import nuclei_size_histogram
from ui.components import image_preview, no_image_warning, placeholder_notice
from ui.theme import render_page_hero
def render() -> None:
    render_page_hero("Cell & Nuclei Detection", "Detect nuclear structures via hematoxylin-channel enhancement")
    if not has_image():
        no_image_warning("run nuclei detection")
        return
    placeholder_notice(
        "Model Status",
        "Classical CV nuclei pipeline active. Integrate StarDist / HoVer-Net weights at `models/weights/nuclei_detector.pt`.",
    )
    min_area = st.slider("Min nuclei area (px²)", 10, 200, 30)
    min_circ = st.slider("Min circularity", 0.1, 0.9, 0.35)
    if st.button("Detect Nuclei", type="primary", use_container_width=True):
        with st.spinner("Detecting nuclei..."):
            results = detect_nuclei(
                st.session_state.current_image,
                min_area=min_area,
                min_circularity=min_circ,
            )
            st.session_state.cell_results = results
    results = st.session_state.cell_results
    if not results:
        image_preview(st.session_state.current_image)
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Nuclei Count", results["nuclei_count"])
    c2.metric("Density (/Mpx)", results["density_per_mpx"])
    c3.metric("Mean Area (px²)", results["mean_area"])
    left, right = st.columns(2)
    with left:
        image_preview(results["overlay_pil"], "Nuclei overlay")
    with right:
        sizes = [n["area"] for n in results["nuclei"]]
        if sizes:
            st.plotly_chart(nuclei_size_histogram(sizes), use_container_width=True)
    st.caption(results["method"])