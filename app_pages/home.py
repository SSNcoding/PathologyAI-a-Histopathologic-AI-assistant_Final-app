"""Public landing page — hero, features, disease coverage, stats, tech stack, FAQ, footer."""

from __future__ import annotations

import streamlit as st

from ui.landing import (
    render_disease_grid,
    render_faq,
    render_feature_cards,
    render_footer,
    render_hero,
    render_how_it_works,
    render_stats,
    render_tech_stack,
)


def render() -> None:
    def _go_upload():
        st.session_state.public_page = "Login"
        st.rerun()

    def _go_learn_more():
        st.session_state.public_page = "About"
        st.rerun()

    render_hero(_go_upload, _go_learn_more)
    st.markdown("---")
    render_feature_cards()
    st.markdown("---")
    render_disease_grid()
    st.markdown("---")
    render_stats()
    st.markdown("---")
    render_how_it_works()
    st.markdown("---")
    render_tech_stack()
    st.markdown("---")
    render_faq()
    render_footer()
