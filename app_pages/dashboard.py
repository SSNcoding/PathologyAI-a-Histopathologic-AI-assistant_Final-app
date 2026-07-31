import pandas as pd
import streamlit as st
from core.session_state import current_user, has_image, is_authenticated
from ui.charts import daily_analysis_line, tissue_composition_pie
from ui.components import metric_card
from ui.theme import render_page_hero
def render() -> None:
    greeting_name = current_user()["username"] if is_authenticated() else "there"
    render_page_hero(f"Welcome back, {greeting_name}", "Real-time analytics for computational pathology workflows")
    history = st.session_state.analysis_history
    total_cases = len(history) + 1248  # demo baseline
    total_nuclei = sum(h.get("nuclei_count", 0) for h in history) + 84392
    avg_conf = (
        round(sum(h.get("confidence", 0) for h in history) / len(history), 3) if history else 0.964
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Cases Analyzed", f"{total_cases:,}", "+12 today")
    with c2:
        metric_card("Nuclei Detected", f"{total_nuclei:,}", "+2.4%")
    with c3:
        metric_card("Mean Confidence", f"{avg_conf:.1%}", "Heuristic")
    with c4:
        metric_card("Active Slide", "Loaded" if has_image() else "None", st.session_state.current_image_name or "")
    st.markdown("---")
    left, right = st.columns([1.2, 1])
    with left:
        df_line = pd.DataFrame(
            {
                "date": pd.date_range(end=pd.Timestamp.today(), periods=7),
                "cases": [42, 51, 47, 63, 58, 71, 68],
            }
        )
        st.plotly_chart(daily_analysis_line(df_line), use_container_width=True)
    with right:
        if st.session_state.ai_results:
            tissue = st.session_state.ai_results["tissue"]
            rows = tissue.get("regions", [])
            if rows:
                df = pd.DataFrame([{"region": r["label"], "area_pct": r["area_pct"]} for r in rows])
            else:
                df = pd.DataFrame({"region": ["Background", "Tissue"], "area_pct": [30, 70]})
        else:
            df = pd.DataFrame(
                {"region": ["Normal Tissue", "Stroma", "Inflammation"], "area_pct": [65, 25, 10]}
            )
        st.plotly_chart(tissue_composition_pie(df), use_container_width=True)