import streamlit as st
from services.assistant import generate_assistant_reply
from ui.theme import render_page_hero
def render() -> None:
    render_page_hero("Pathology Assistant", "AI copilot for interpreting slide analysis results")
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if prompt := st.chat_input("Ask about tissue, nuclei, risk, or heatmaps..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        ctx = {}
        if st.session_state.ai_results:
            ai = st.session_state.ai_results
            ctx = {
                "nuclei_count": ai["cells"]["nuclei_count"],
                "density_per_mpx": ai["cells"]["density_per_mpx"],
                "tissue_coverage_pct": ai["tissue"]["tissue_coverage_pct"],
                "risk_level": ai["risk_level"],
            }
        reply = generate_assistant_reply(prompt, ctx)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()