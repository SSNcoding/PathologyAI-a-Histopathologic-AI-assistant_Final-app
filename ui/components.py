"""Reusable UI components."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image


def metric_card(label: str, value: str, delta: str | None = None) -> None:
    delta_html = f'<div class="metric-delta">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-card-title">{title}</div>
            <div class="info-card-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(text: str, kind: str = "info") -> None:
    st.markdown(f'<span class="badge badge-{kind}">{text}</span>', unsafe_allow_html=True)


def no_image_warning(action: str = "continue") -> None:
    st.warning(f"No image uploaded. Go to **Upload** to add a histopathology slide before you {action}.")


def image_preview(image: Image.Image, caption: str = "Current slide", width: int = 700) -> None:
    st.image(image, caption=caption, use_container_width=True)


def placeholder_notice(title: str, detail: str) -> None:
    st.info(f"**{title}** — {detail}")


def analysis_progress_bar(progress: float, label: str) -> None:
    st.progress(min(max(progress, 0.0), 1.0), text=label)


def disclaimer_banner(text: str) -> None:
    st.markdown(f'<div class="disclaimer-banner">⚠️ {text}</div>', unsafe_allow_html=True)


def feature_card(icon: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="feature-card">
            <div class="feature-icon">{icon}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def process_step_card(number: int, icon: str, title: str, body: str) -> None:
    """One step in the 'How it works' walkthrough on the landing page. Shows what
    the pipeline actually does at each stage — used instead of testimonials/quotes,
    since there's no real user base yet and fabricating endorsements would work
    against the project's honesty-first stance (see README)."""
    st.markdown(
        f"""
        <div class="step-card">
            <div class="step-number">{number:02d}</div>
            <div class="step-icon">{icon}</div>
            <div class="step-title">{title}</div>
            <div class="step-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def faq_item(question: str, answer: str, open_first: bool = False) -> None:
    open_attr = "open" if open_first else ""
    st.markdown(
        f"""
        <details class="faq-item" {open_attr}>
            <summary>{question}</summary>
            <div class="faq-answer">{answer}</div>
        </details>
        """,
        unsafe_allow_html=True,
    )


def animated_counter(value: str, label: str, duration_ms: int = 1400) -> None:
    """Count-up number using a tiny embedded script (safe inside an iframe, doesn't
    interfere with Streamlit's own rerun cycle)."""
    numeric = "".join(ch for ch in value if ch.isdigit())
    suffix = value[len(numeric):] if numeric else ""
    target = int(numeric) if numeric else 0
    html = f"""
    <div style="text-align:center; font-family:Inter,sans-serif;">
        <div id="counter" style="font-size:2.1rem; font-weight:800;
            background:linear-gradient(135deg,#06B6D4,#8B5CF6);
            -webkit-background-clip:text; background-clip:text; color:transparent;">0{suffix}</div>
        <div style="font-size:0.8rem; color:#94A3B8; text-transform:uppercase; letter-spacing:0.06em; margin-top:4px;">{label}</div>
    </div>
    <script>
        const target = {target};
        const el = document.getElementById("counter");
        const duration = {duration_ms};
        const start = performance.now();
        function tick(now) {{
            const progress = Math.min((now - start) / duration, 1);
            const current = Math.floor(progress * target);
            el.textContent = current.toLocaleString() + "{suffix}";
            if (progress < 1) requestAnimationFrame(tick);
        }}
        requestAnimationFrame(tick);
    </script>
    """
    components.html(html, height=90)


def skeleton_loader(rows: int = 3) -> None:
    for _ in range(rows):
        st.markdown('<div class="skeleton skeleton-block"></div>', unsafe_allow_html=True)


def notification_bell(unread_count: int) -> None:
    badge = f'<span class="badge badge-danger" style="margin-left:6px;">{unread_count}</span>' if unread_count else ""
    st.markdown(f"### \U0001F514 Notifications {badge}", unsafe_allow_html=True)


def disease_badge(label: str, confidence: float) -> None:
    kind = "danger" if confidence > 0.55 else ("warning" if confidence > 0.3 else "success")
    status_badge(f"{label} · {confidence:.0%}", kind)


def research_only_notice(feature_name: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="info-card" style="border-left: 3px solid var(--accent-purple);">
            <div class="info-card-title">\U0001F52C {feature_name} — Research Preview</div>
            <div class="info-card-body">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
