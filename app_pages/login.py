"""Login page."""

from __future__ import annotations

import streamlit as st

from core.session_state import log_in
from services.audit_service import log_action
from services.auth_service import authenticate_user
from services.oauth_service import PROVIDER_LABEL, build_authorize_url, is_oauth_enabled
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Sign In", "Access your PathologyAI workspace")

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if is_oauth_enabled():
            st.link_button(f"Continue with {PROVIDER_LABEL}", build_authorize_url(), use_container_width=True)
            st.caption("or sign in with a local account")

        with st.form("login_form"):
            identifier = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

        if submitted:
            user, message = authenticate_user(identifier, password)
            if user:
                log_in(user)
                log_action(user, "login", f"Signed in as {user.get('role', 'pathologist')}")
                st.success(message)
                st.rerun()
            else:
                st.session_state.auth_error = message
                log_action(None, "login_failed", f"Failed sign-in attempt for '{identifier}'")
                st.error(message)

        st.caption("Don't have an account?")
        if st.button("Create one", use_container_width=True):
            st.session_state.public_page = "Register"
            st.rerun()

        st.info("Demo tip: register a new account below — no email verification is required "
                "in this prototype.")
