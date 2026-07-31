"""Registration page."""

from __future__ import annotations

import streamlit as st

from services.auth_service import register_user
from ui.theme import render_page_hero


def render() -> None:
    render_page_hero("Create Account", "Join PathologyAI to save analyses and generate reports")

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.form("register_form"):
            full_name = st.text_input("Full Name")
            username = st.text_input("Username*")
            email = st.text_input("Email*")
            institution = st.text_input("Institution")
            role = st.selectbox("Role", ["pathologist", "researcher", "student", "administrator"])
            password = st.text_input("Password* (min 6 characters)", type="password")
            confirm = st.text_input("Confirm Password*", type="password")
            submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, message = register_user(username, email, password, full_name, institution, role)
                if ok:
                    st.success(message)
                    st.session_state.public_page = "Login"
                else:
                    st.error(message)

        st.caption("Already have an account?")
        if st.button("Sign in instead", use_container_width=True):
            st.session_state.public_page = "Login"
            st.rerun()
