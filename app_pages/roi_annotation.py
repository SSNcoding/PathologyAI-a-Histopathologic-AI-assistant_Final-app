"""ROI Annotation — replaces the old Assistant page in the nav."""

from __future__ import annotations

import streamlit as st

from core.session_state import current_user
from services.audit_service import log_action
from services.roi_service import (
    LABEL_COLORS,
    annotations_to_csv_bytes,
    color_for_label,
    new_annotation,
    render_overlay,
)
from ui.components import no_image_warning
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("ROI Annotation", "Mark and label regions of interest on the current slide")

    if not st.session_state.current_image:
        no_image_warning("mark a region of interest")
        return

    slide_name = st.session_state.current_image_name
    st.session_state.setdefault("roi_annotations", [])
    all_annotations = st.session_state.roi_annotations
    annotations = [a for a in all_annotations if a.get("slide_name") == slide_name]

    st.caption(
        "Position a box with the sliders below, choose a label, and save. This is a box tool "
        "(not freehand drawing), which keeps it dependency-free."
    )

    col_preview, col_controls = st.columns([1.3, 1])

    with col_controls:
        st.subheader("New region")
        label = st.selectbox("Label", list(LABEL_COLORS.keys()))
        note = st.text_input("Note (optional)", "")
        x_range = st.slider("Horizontal extent (%)", 0, 100, (20, 60))
        y_range = st.slider("Vertical extent (%)", 0, 100, (20, 60))

        if st.button("Save Region", type="primary", use_container_width=True):
            ann = new_annotation(label, note, x_range[0], y_range[0], x_range[1], y_range[1])
            ann["slide_name"] = slide_name
            all_annotations.append(ann)
            user = current_user()
            if user:
                log_action(user, "save_roi_annotation", f"{label} on {slide_name}")
            st.rerun()

        st.markdown("---")
        if annotations:
            st.subheader(f"Saved regions ({len(annotations)})")
            for ann in annotations:
                with st.container(border=True):
                    cc1, cc2 = st.columns([4, 1])
                    with cc1:
                        st.markdown(f"**{ann['label']}**")
                        if ann.get("note"):
                            st.caption(ann["note"])
                        st.caption(f"x {ann['x1_pct']}\u2013{ann['x2_pct']}% \u00b7 y {ann['y1_pct']}\u2013{ann['y2_pct']}%")
                    with cc2:
                        if st.button("Delete", key=f"del_roi_{ann['id']}"):
                            all_annotations.remove(ann)
                            user = current_user()
                            if user:
                                log_action(user, "delete_roi_annotation", f"{ann['label']} on {slide_name}")
                            st.rerun()
            st.download_button(
                "Download Annotations CSV",
                data=annotations_to_csv_bytes(annotations),
                file_name=f"{slide_name}_roi_annotations.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.caption("No saved regions yet for this slide.")

    with col_preview:
        draft_color = color_for_label(label)
        preview = render_overlay(
            st.session_state.current_image,
            annotations,
            draft_box=(x_range[0], y_range[0], x_range[1], y_range[1]),
            draft_color=draft_color,
        )
        st.image(
            preview,
            use_container_width=True,
            caption=f"{slide_name} \u2014 draft region shown in {draft_color}, saved regions in their label color",
        )