"""Plotly chart builders with theme-aware styling (dark or light)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.constants import THEME_DARK, THEME_LIGHT

# Backwards-compat alias used by a few call sites.
COLORS = THEME_DARK


def _palette() -> dict:
    try:
        return THEME_LIGHT if st.session_state.get("theme") == "light" else THEME_DARK
    except Exception:
        return THEME_DARK


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Kept name for backwards compatibility; actually theme-aware now."""
    palette = _palette()
    grid = palette["border"] if palette is THEME_LIGHT else "#334155"
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=palette["text_primary"], family="Inter, sans-serif"),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid)
    return fig


def tissue_composition_pie(df: pd.DataFrame) -> go.Figure:
    palette = _palette()
    fig = px.pie(
        df, names="region", values="area_pct", hole=0.55,
        color_discrete_sequence=[
            palette["accent_cyan"], palette["accent_blue"], palette["accent_purple"],
            palette["warning"], palette["success"], palette["danger"],
        ],
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(title="Tissue Composition", showlegend=False)
    return apply_dark_theme(fig)


def daily_analysis_line(df: pd.DataFrame) -> go.Figure:
    palette = _palette()
    fig = px.line(df, x="date", y="cases", markers=True, color_discrete_sequence=[palette["accent_cyan"]])
    fig.update_layout(title="Cases Analyzed (7 Days)", xaxis_title="", yaxis_title="Cases")
    return apply_dark_theme(fig)


def confidence_bar(labels: list[str], scores: list[float]) -> go.Figure:
    palette = _palette()
    fig = go.Figure(data=[go.Bar(
        x=scores, y=labels, orientation="h",
        marker=dict(
            color=scores,
            colorscale=[[0, palette["danger"]], [0.5, palette["warning"]], [1, palette["success"]]],
            cmin=0, cmax=1,
        ),
    )])
    fig.update_layout(title="Model Confidence by Finding", xaxis_title="Confidence", xaxis_range=[0, 1])
    return apply_dark_theme(fig)


def nuclei_size_histogram(sizes: list[float]) -> go.Figure:
    palette = _palette()
    fig = px.histogram(x=sizes, nbins=30, color_discrete_sequence=[palette["accent_blue"]])
    fig.update_layout(title="Nuclei Area Distribution (px²)", xaxis_title="Area", yaxis_title="Count")
    return apply_dark_theme(fig)


def tumor_healthy_donut(tumor_pct: float, healthy_pct: float) -> go.Figure:
    palette = _palette()
    other = max(0.0, 100 - tumor_pct - healthy_pct)
    df = pd.DataFrame({
        "label": ["Tumor (heuristic)", "Healthy Tissue", "Other/Stroma"],
        "value": [tumor_pct, healthy_pct, other],
    })
    fig = px.pie(
        df, names="label", values="value", hole=0.6,
        color_discrete_sequence=[palette["danger"], palette["success"], palette["accent_blue"]],
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(title="Tumor vs. Healthy Tissue (heuristic)", showlegend=False)
    return apply_dark_theme(fig)


def gauge_chart(value: float, title: str, max_value: float = 1.0, suffix: str = "") -> go.Figure:
    palette = _palette()
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix},
        title={"text": title, "font": {"size": 14}},
        gauge={
            "axis": {"range": [0, max_value]},
            "bar": {"color": palette["accent_cyan"]},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 1,
            "bordercolor": palette["border"],
            "steps": [
                {"range": [0, max_value * 0.5], "color": "rgba(16,185,129,0.18)"},
                {"range": [max_value * 0.5, max_value * 0.75], "color": "rgba(245,158,11,0.18)"},
                {"range": [max_value * 0.75, max_value], "color": "rgba(239,68,68,0.18)"},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=10))
    return apply_dark_theme(fig)


def color_histogram_chart(histogram: dict[str, list[float]]) -> go.Figure:
    fig = go.Figure()
    colors = {"red": "#EF4444", "green": "#10B981", "blue": "#3B82F6"}
    for channel, values in histogram.items():
        fig.add_trace(go.Scatter(y=values, mode="lines", name=channel.capitalize(),
                                  line=dict(color=colors.get(channel, "#94A3B8"))))
    fig.update_layout(title="Color Channel Histogram", xaxis_title="Bin", yaxis_title="% Pixels")
    return apply_dark_theme(fig)


def model_comparison_bar(model_names: list[str], accuracies: list[float]) -> go.Figure:
    palette = _palette()
    fig = px.bar(
        x=model_names, y=accuracies,
        color=accuracies,
        color_continuous_scale=[palette["accent_purple"], palette["accent_cyan"]],
    )
    fig.update_layout(title="Model Comparison (illustrative — no trained weights yet)",
                       xaxis_title="", yaxis_title="Relative Score", coloraxis_showscale=False)
    return apply_dark_theme(fig)


def calibration_curve(bin_confidences: list[float], bin_accuracies: list[float]) -> go.Figure:
    palette = _palette()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfectly calibrated",
                              line=dict(color=palette["text_muted"], dash="dash")))
    fig.add_trace(go.Scatter(x=bin_confidences, y=bin_accuracies, mode="lines+markers",
                              name="Model", line=dict(color=palette["accent_cyan"])))
    fig.update_layout(title="Confidence Calibration Curve", xaxis_title="Predicted Confidence",
                       yaxis_title="Observed Accuracy", xaxis_range=[0, 1], yaxis_range=[0, 1])
    return apply_dark_theme(fig)


def radar_metrics(categories: list[str], values: list[float]) -> go.Figure:
    palette = _palette()
    fig = go.Figure(data=go.Scatterpolar(
        r=values + values[:1], theta=categories + categories[:1], fill="toself",
        line=dict(color=palette["accent_teal"]),
    ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values + [1])])),
                       title="Multi-Metric Summary", showlegend=False)
    return apply_dark_theme(fig)
