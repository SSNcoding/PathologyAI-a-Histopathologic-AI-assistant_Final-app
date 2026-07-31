"""Login page."""

from __future__ import annotations

import streamlit as st

from services.auth_service import authenticate_user
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Sign In", "Access your PathologyAI workspace")

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.form("login_form"):
            identifier = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            user, message = authenticate_user(identifier, password)
            if user:
                st.session_state.auth_user = user
                st.session_state.auth_error = None
                st.success(message)
                st.rerun()
            else:
                st.session_state.auth_error = message
                st.error(message)

        st.caption("Don't have an account?")
        if st.button("Create one", use_container_width=True):
            st.session_state.public_page = "Register"
            st.rerun()

        st.info("Demo tip: register a new account below — no email verification is required "
                "in this prototype.")
