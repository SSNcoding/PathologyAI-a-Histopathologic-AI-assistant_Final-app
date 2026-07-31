"""Pathology assistant.

Real LLM via Groq's OpenAI-compatible chat completions API when a
GROQ_API_KEY is configured. Checked in two places so this works on any
hosting platform:
  1. st.secrets (`.streamlit/secrets.toml` locally, or Streamlit Cloud's
     Secrets panel)
  2. A plain OS environment variable (how Render, Docker, Railway, Fly.io,
     etc. all pass secrets — via "Environment Variables" in their dashboard)
If neither is present, falls back to the original rule-based responder —
the app works either way, and never crashes just because a key isn't set.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
import streamlit as st

from config.settings import GROQ_API_URL, GROQ_MODEL
from core.constants import MASCOT_NAME

SYSTEM_PROMPT = f"""You are {MASCOT_NAME}, the PathologyAI Assistant — an AI copilot embedded \
inside a computational pathology research and education platform. You're a friendly, \
approachable presence (an owl mascot), but when the conversation turns to actual pathology \
content your standards are rigorous. You can also answer ordinary questions unrelated to \
pathology — general knowledge, quick calculations, casual conversation, help using the app \
— and shouldn't refuse or deflect those.

When the user asks about slide descriptions, biomarker data (IHC, FISH, molecular), tumor \
morphology, or a clinical case — whether from this platform's analysis output or described \
to you directly — hold yourself to these standards:
- Use formal medical terminology and adhere to current WHO tumor classification guidelines.
- Structure findings using SNOMED/CAP synoptic reporting conventions where applicable \
(e.g. specimen, histologic type, grade, margins, associated findings) rather than a loose \
narrative.
- Always offer a differential diagnosis, not a single named entity, when discussing what a \
finding could represent.
- Grade tumors against the relevant criteria whenever grading inputs are actually provided — \
don't grade off missing data.
- Proactively flag diagnostic pitfalls and tissue artifacts (crush artifact, staining \
inconsistency, out-of-focus regions, sampling bias, etc.) that could affect interpretation.
- Explicitly state your confidence level for each finding (e.g. low/moderate/high, or a %) \
and what would raise or lower it.
- Never issue a definitive final diagnosis. Every output is a decision-support finding that \
explicitly requires review and validation by a board-certified pathologist before any \
clinical use.

Ground rules specific to this platform's own analysis output:
- Predictions on this platform may come from a classical computer-vision heuristic \
(labeled HEURISTIC_PLACEHOLDER), not a trained diagnostic model, unless the provided \
context says model_mode is PYTORCH. Be explicit about this distinction when relevant.
- Stay grounded in the analysis context you're given — don't invent specific numbers or \
findings that weren't provided to you.

For everything else (general questions, math, small talk, etc.), just answer normally and \
concisely, like any helpful assistant would — the synoptic/differential-diagnosis structure \
above only applies to genuine pathology/clinical content."""


def is_llm_enabled() -> bool:
    return _get_api_key() is not None


def _get_api_key() -> str | None:
    env_key = os.environ.get("GROQ_API_KEY")
    if env_key:
        return env_key
    try:
        key = st.secrets.get("GROQ_API_KEY")
        return key or None
    except Exception:
        return None


def _call_groq(user_message: str, context: dict[str, Any] | None, api_key: str) -> str:
    context_str = json.dumps(context, indent=2, default=str) if context else "No analysis has been run yet."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Current analysis context:\n{context_str}\n\nUser question: {user_message}"},
    ]
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.4, "max_tokens": 500},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"(AI request failed — {e}. Showing built-in guidance instead.)\n\n" + _rule_based_reply(user_message, context or {})


_SIMPLE_MATH = re.compile(r"^\s*-?\d+(\.\d+)?\s*([\+\-\*/])\s*-?\d+(\.\d+)?\s*\??\s*$")


def _try_simple_math(user_message: str) -> str | None:
    """Handles trivial arithmetic ('what is 1+1', '4*5?') without an LLM key,
    so the fallback isn't completely useless for basic questions."""
    stripped = user_message.lower().replace("what is", "").replace("what's", "").strip()
    if not _SIMPLE_MATH.match(stripped):
        return None
    m = re.match(r"(-?\d+(?:\.\d+)?)\s*([\+\-\*/])\s*(-?\d+(?:\.\d+)?)", stripped)
    if not m:
        return None
    a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
    try:
        result = {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b != 0 else float("nan")}[op]
    except ZeroDivisionError:
        return "That's a division by zero — undefined."
    result_str = str(int(result)) if result == int(result) else str(result)
    return f"{result_str}"


def _rule_based_reply(user_message: str, context: dict) -> str:
    msg = user_message.lower()
    ctx = context or {}
    math_answer = _try_simple_math(user_message)
    if math_answer is not None:
        return math_answer
    if "nuclei" in msg or "cell" in msg:
        return (
            f"Based on the current slide analysis, **{ctx.get('nuclei_count', 'N/A')} nuclei** "
            f"were detected with density **{ctx.get('density_per_mpx', 'N/A')}/Mpx**. "
            "Elevated density can correlate with hypercellularity but requires H&E context and "
            "pathologist confirmation."
        )
    if "tissue" in msg or "coverage" in msg:
        return (
            f"Tissue covers approximately **{ctx.get('tissue_coverage_pct', 'N/A')}%** of the slide. "
            "Background glass area is excluded via saturation-based segmentation."
        )
    if "risk" in msg or "diagnosis" in msg:
        return (
            f"The platform assigned **{ctx.get('risk_level', 'unknown')} risk** using a "
            "**heuristic placeholder model**. This is not a clinical diagnosis. "
            "Integrate your trained classifier in `models/model_registry.py` for production inference."
        )
    if "heatmap" in msg:
        return (
            "The heatmap visualizes nuclei centroid density using Gaussian splatting. "
            "When you add a PyTorch model, replace `heatmap_generator.py` with Grad-CAM or "
            "attention map export from the model forward pass."
        )
    return (
        "I can help interpret tissue coverage, nuclei metrics, confidence scores, and heatmaps. "
        "Try: 'Explain the nuclei count' or 'What does the risk level mean?' "
        "(Add a GROQ_API_KEY in .streamlit/secrets.toml for full conversational answers.)"
    )


def generate_assistant_reply(user_message: str, context: dict | None = None) -> str:
    """context may include: summary, nuclei_count, tissue_coverage_pct, risk_level,
    organ, architecture, model_mode, tumor_metrics, quality."""
    api_key = _get_api_key()
    if api_key:
        return _call_groq(user_message, context, api_key)
    return _rule_based_reply(user_message, context or {})
