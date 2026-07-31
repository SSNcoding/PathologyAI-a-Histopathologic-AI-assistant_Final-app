"""Application configuration.

Values that vary between local dev / Streamlit Community Cloud / a real
deployment are read from environment variables first, with safe defaults
for local development. See `.env.example`.
"""

from __future__ import annotations

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
MODELS_DIR = PROJECT_ROOT / "models" / "weights"
REPORTS_DIR = PROJECT_ROOT / "output" / "reports"
UPLOADS_DIR = PROJECT_ROOT / "output" / "uploads"
DATA_DIR = PROJECT_ROOT / "output" / "data"
DB_PATH = os.environ.get("PATHOLOGYAI_DB_PATH", str(DATA_DIR / "pathologyai.db"))

for directory in (MODELS_DIR, REPORTS_DIR, UPLOADS_DIR, DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# App metadata
APP_NAME = "PathologyAI"
APP_VERSION = "2.0.0"
APP_TAGLINE = "AI-Powered Computational Pathology Platform"
ORGANIZATION = "PathologyAI Labs"

# Analysis defaults
MAX_UPLOAD_MB = 200  # raised to accommodate large WSI snapshots
SUPPORTED_FORMATS = ("png", "jpg", "jpeg", "tif", "tiff", "bmp", "svs")
WSI_FORMATS = ("svs", "tif", "tiff")
DEFAULT_CONFIDENCE_THRESHOLD = 0.65

# Model integration points (set paths when weights are available)
TISSUE_CLASSIFIER_PATH = MODELS_DIR / "tissue_classifier.pt"
NUCLEI_DETECTOR_PATH = MODELS_DIR / "nuclei_detector.pt"
DISEASE_CLASSIFIER_PATH_TEMPLATE = str(MODELS_DIR / "{organ}_{architecture}.pt")
PATHOLOGY_LLM_ENDPOINT = os.environ.get("PATHOLOGY_LLM_ENDPOINT") or None  # e.g. "http://localhost:8000/v1/chat"

# Assistant — real LLM via Groq's OpenAI-compatible API. Key is read from
# st.secrets (.streamlit/secrets.toml locally, or the app's Secrets panel on
# Streamlit Cloud) so it never needs to be committed to git. If no key is
# configured, services/assistant.py falls back to a built-in rule-based
# responder — the app works either way.
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Auth / security
# APP_ENV gates the insecure-default-key check below. It intentionally does
# NOT default to "production" — that would break every existing local/dev
# setup that hasn't set PATHOLOGYAI_SECRET_KEY yet. Set PATHOLOGYAI_ENV=production
# explicitly (e.g. in render.yaml, Docker env, or Streamlit Cloud secrets)
# once you're running this somewhere real.
APP_ENV = os.environ.get("PATHOLOGYAI_ENV", "development").strip().lower()
_DEFAULT_SECRET_KEY = "dev-only-insecure-key-change-me"
SECRET_KEY = os.environ.get("PATHOLOGYAI_SECRET_KEY", _DEFAULT_SECRET_KEY)
if APP_ENV == "production" and SECRET_KEY == _DEFAULT_SECRET_KEY:
    raise RuntimeError(
        "PATHOLOGYAI_ENV=production but PATHOLOGYAI_SECRET_KEY is still the insecure "
        "default. Set a long random PATHOLOGYAI_SECRET_KEY (env var or Streamlit "
        "secrets) before deploying — see .env.example."
    )
SESSION_COOKIE_NAME = "pathologyai_session"
SESSION_TIMEOUT_MINUTES = int(os.environ.get("PATHOLOGYAI_SESSION_TIMEOUT_MINUTES", "60"))

# UI
SIDEBAR_WIDTH = 300
DEFAULT_THEME = "dark"  # "dark" | "light"

# Feature flags — flip these on once real trained weights are wired in.
FEATURE_FLAGS = {
    "real_dl_inference": False,   # True once model_registry loads actual weights
    "gradcam_neural": False,      # True once a real torch classifier backs Grad-CAM
    "wsi_deep_zoom": True,        # DZI tiling of uploaded images works today (classical)
}
