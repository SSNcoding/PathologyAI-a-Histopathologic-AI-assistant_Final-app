import streamlit as st

from core.constants import MASCOT_AVATAR, MASCOT_NAME, USER_AVATAR
from services.assistant import generate_assistant_reply, is_llm_enabled
from ui.assistant_widget import get_analysis_context
from ui.components import status_badge
from ui.theme import render_page_hero


def _avatar_for(role: str) -> str:
    return MASCOT_AVATAR if role == "assistant" else USER_AVATAR


def render() -> None:
    render_page_hero(f"{MASCOT_AVATAR} {MASCOT_NAME}", "Your pathology co-pilot for interpreting slide analysis results")

    if is_llm_enabled():
        status_badge("LIVE AI (Groq)", "success")
    else:
        status_badge("RULE-BASED FALLBACK — add GROQ_API_KEY for full AI", "warning")

    st.caption(
        f"{MASCOT_NAME} can also answer general questions, not just pathology ones — "
        "and follows you to every page via the sidebar, not just here."
    )

    if not st.session_state.chat_messages:
        with st.chat_message("assistant", avatar=MASCOT_AVATAR):
            st.markdown(
                f"Hi, I'm **{MASCOT_NAME}** \U0001F989 — ask me about tissue coverage, nuclei "
                "counts, risk levels, heatmaps, or a case you're describing. On pathology "
                "questions I'll give you a differential, flag artifacts/pitfalls, and state "
                "my confidence — always as decision support, never a final diagnosis."
            )

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"], avatar=_avatar_for(message["role"])):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about tissue, nuclei, risk, heatmaps — or anything else..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.spinner(f"{MASCOT_NAME} is thinking..."):
            reply = generate_assistant_reply(prompt, get_analysis_context())
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()
