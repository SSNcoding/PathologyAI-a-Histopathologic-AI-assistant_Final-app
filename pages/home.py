"""Public landing page — hero, features, disease coverage, stats, tech stack, FAQ, footer.

NOTE: this file is a stale duplicate of app_pages/home.py, kept only because the
platform wouldn't let this session delete the top-level pages/ directory. It is
NOT imported anywhere — app_create.py only imports from app_pages/, and
.streamlit/config.toml sets client.showSidebarNavigation = false so Streamlit's
automatic pages/ discovery can't surface it either. Safe to delete this whole
pages/ folder by hand once you have local write access.
"""

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
