"""Contact page — a real (locally-persisted) contact form, no external email service."""

from __future__ import annotations

import streamlit as st

from db.database import get_connection, init_db
from ui.landing import render_footer
from ui.theme import render_page_hero

init_db()


def _save_message(name: str, email: str, subject: str, message: str) -> None:
    from datetime import datetime, timezone
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO contact_messages (name, email, subject, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, subject, message, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def render() -> None:
    render_page_hero("Contact Us", "Questions about research collaboration, datasets, or deployment?")

    with st.form("contact_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name*")
        with c2:
            email = st.text_input("Email*")
        subject = st.text_input("Subject", value="General inquiry")
        message = st.text_area("Message*", height=140)
        submitted = st.form_submit_button("Send Message", type="primary", use_container_width=True)

    if submitted:
        if not name or not email or not message:
            st.error("Please fill in name, email, and message.")
        else:
            _save_message(name, email, subject, message)
            st.success("Thanks — your message has been recorded. We'll get back to you soon.")

    st.caption(
        "Messages are stored locally in this app's database (no external email service is "
        "wired up in this prototype)."
    )
    render_footer()
