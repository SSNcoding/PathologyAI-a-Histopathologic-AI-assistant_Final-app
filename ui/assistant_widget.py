"""Shared assistant context builder + a compact chat widget for the sidebar,
so the AI assistant is reachable from every page — not just the dedicated
Assistant page (which still exists for the full conversation view). Both
share the same st.session_state.chat_messages history, so a conversation
started in the sidebar continues seamlessly on the Assistant page."""

from __future__ import annotations

import streamlit as st

from core.constants import MASCOT_AVATAR, MASCOT_NAME, USER_AVATAR
from services.assistant import generate_assistant_reply, is_llm_enabled


def get_analysis_context() -> dict:
    if not st.session_state.get("ai_results"):
        return {}
    ai = st.session_state.ai_results
    return {
        "organ": ai.get("organ"),
        "architecture": ai.get("architecture"),
        "model_mode": ai.get("model_mode"),
        "summary": ai.get("summary"),
        "risk_level": ai.get("risk_level"),
        "confidence": ai.get("confidence"),
        "nuclei_count": ai["cells"]["nuclei_count"],
        "density_per_mpx": ai["cells"]["density_per_mpx"],
        "tissue_coverage_pct": ai["tissue"]["tissue_coverage_pct"],
        "tumor_metrics": ai.get("tumor_metrics"),
        "quality": ai.get("quality"),
        "findings": ai.get("findings"),
    }


def render_sidebar_assistant() -> None:
    """Compact ask-anything box, available in the sidebar on every page — this
    is what makes the mascot ('Hoot') feel like a companion that follows the
    user around the app rather than something confined to one tab."""
    badge = "\U0001F7E2 Live AI" if is_llm_enabled() else "\U0001F7E1 Basic mode"
    with st.expander(f"{MASCOT_AVATAR} Ask {MASCOT_NAME}  ·  {badge}", expanded=False):
        history = st.session_state.get("chat_messages", [])
        if not history:
            st.caption(f"{MASCOT_AVATAR} Hi, I'm {MASCOT_NAME} — ask me anything about this slide, or anything at all.")
        for message in history[-3:]:
            avatar = MASCOT_AVATAR if message["role"] == "assistant" else USER_AVATAR
            role_label = "You" if message["role"] == "user" else MASCOT_NAME
            st.markdown(f"{avatar} **{role_label}:** {message['content']}")

        with st.form("sidebar_assistant_form", clear_on_submit=True):
            quick_q = st.text_input(
                "Ask anything", label_visibility="collapsed", placeholder="Ask anything..."
            )
            sent = st.form_submit_button("Send", use_container_width=True)

        if sent and quick_q.strip():
            st.session_state.chat_messages.append({"role": "user", "content": quick_q})
            with st.spinner(f"{MASCOT_NAME} is thinking..."):
                reply = generate_assistant_reply(quick_q, get_analysis_context())
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            st.rerun()

        st.caption("Full conversation history: see the Assistant page.")


def render_floating_mascot() -> None:
    """A floating chat bubble pinned to the bottom-right corner of the
    viewport — present on every authenticated page because app_create.py
    calls this once, after the selected page renders, rather than each page
    calling it individually. Unlike the sidebar box above (which needs the
    sidebar open and a scroll past every nav item to find), this is always
    visible regardless of what tab you're on or whether the sidebar is
    collapsed, which is the actual "follows you everywhere" behavior.

    Uses st.container(key=...) rather than a hand-rolled div/CSS-sibling
    hack: Streamlit (>=1.37, see requirements.txt) stamps a stable
    `st-key-<key>` class on any element given a `key`, so assets/styles.css
    can target `.st-key-hoot-fab` directly and reliably instead of guessing
    at Streamlit's internal DOM structure — the kind of fragile CSS/JS
    coupling that caused the earlier theme-toggle bug.
    """
    if "hoot_fab_open" not in st.session_state:
        st.session_state.hoot_fab_open = False

    with st.container(key="hoot-fab"):
        if not st.session_state.hoot_fab_open:
            if st.button(MASCOT_AVATAR, key="hoot-fab-toggle", help=f"Ask {MASCOT_NAME}"):
                st.session_state.hoot_fab_open = True
                st.rerun()
        else:
            with st.container(key="hoot-fab-panel"):
                top_l, top_r = st.columns([5, 1])
                top_l.markdown(f"**{MASCOT_AVATAR} {MASCOT_NAME}**")
                if top_r.button("✕", key="hoot-fab-close", help="Close"):
                    st.session_state.hoot_fab_open = False
                    st.rerun()

                history = st.session_state.get("chat_messages", [])
                if not history:
                    st.caption(f"Ask me about this slide, or anything else — I'm with you on every page.")
                for message in history[-4:]:
                    avatar = MASCOT_AVATAR if message["role"] == "assistant" else USER_AVATAR
                    st.markdown(f"{avatar} {message['content']}")

                with st.form("hoot_fab_form", clear_on_submit=True):
                    quick_q = st.text_input(
                        "Ask", label_visibility="collapsed", placeholder=f"Ask {MASCOT_NAME}..."
                    )
                    sent = st.form_submit_button("Send", use_container_width=True)

                if sent and quick_q.strip():
                    st.session_state.chat_messages.append({"role": "user", "content": quick_q})
                    with st.spinner(f"{MASCOT_NAME} is thinking..."):
                        reply = generate_assistant_reply(quick_q, get_analysis_context())
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                    st.rerun()
