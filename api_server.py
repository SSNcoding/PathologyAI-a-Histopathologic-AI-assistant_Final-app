"""FastAPI layer over the same analysis pipeline the Streamlit app uses.

Not started automatically — app_create.py (Streamlit) remains the primary
entry point. This gives programmatic/HTTP access to services/ai_analyzer.py
for integrations, scripts, or a future non-Streamlit frontend, without
duplicating any analysis logic.

Setup:
    pip install fastapi uvicorn   # see requirements.txt (commented out there)
    uvicorn api_server:app --reload --port 8000

Then either open http://localhost:8000/docs for interactive API docs, or:
    curl -F "file=@slide.png" -F "organ=breast" http://localhost:8000/analyze

Auth: unauthenticated by default (fine for localhost/dev). Set
PATHOLOGYAI_API_KEY and every request must include a matching `X-API-Key`
header, or it's rejected with 401. This is a shared-secret check, not real
auth (OAuth/JWT) — don't expose this beyond a trusted network without adding
something stronger in front of it (e.g. a reverse proxy with real auth).
"""

from __future__ import annotations

import base64
import io
import os

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

from db.database import dumps
from models.disease_registry import organ_options
from services.ai_analyzer import result_to_dict, run_full_analysis

app = FastAPI(
    title="PathologyAI API",
    description=(
        "Programmatic access to the tissue/nuclei analysis pipeline. "
        "Research/education use only — predictions are HEURISTIC_PLACEHOLDER "
        "unless trained weights are loaded (see models/weights/). Not a "
        "diagnostic tool; not for clinical use."
    ),
    version="1.0.0",
)

API_KEY = os.environ.get("PATHOLOGYAI_API_KEY", "").strip()


def _check_api_key(x_api_key: str | None) -> None:
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header.")


def _json_response(payload: dict) -> Response:
    """Uses db.database.dumps() (same JSON encoder the DB layer uses to persist
    analysis payloads) instead of FastAPI's default encoder, because analysis
    results contain numpy arrays and PIL Images (segmentation masks, overlay
    previews) that jsonable_encoder can't serialize. Non-serializable fields
    become null rather than raising a 500 — see include_heatmap for the one
    field callers can actually get back as an image."""
    return Response(content=dumps(payload), media_type="application/json")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/organs")
def list_organs() -> list[dict]:
    return [{"key": key, "display_name": name} for key, name in organ_options()]


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(..., description="Histopathology image (PNG/JPG/TIFF/BMP)."),
    organ: str = Form("breast"),
    architecture: str = Form("Classical CV Heuristic (no trained weights)"),
    use_tta: bool = Form(False),
    include_heatmap: bool = Form(False, description="Include the heatmap as base64 PNG in the response."),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Response:
    _check_api_key(x_api_key)

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read image: {e}")

    result = run_full_analysis(image, organ=organ, architecture=architecture, use_tta=use_tta)
    data = result_to_dict(result)

    heatmap = data.pop("heatmap", None)
    if include_heatmap and heatmap is not None:
        buf = io.BytesIO()
        heatmap.save(buf, format="PNG")
        data["heatmap_png_base64"] = base64.b64encode(buf.getvalue()).decode("ascii")

    # Drop the largest non-serializable intermediates explicitly (masks/overlays
    # as numpy arrays / PIL Images) rather than relying only on dumps()'s
    # null-fallback, so the response stays small and predictable.
    for section in ("tissue", "cells"):
        if isinstance(data.get(section), dict):
            for key in ("overlay_bgr", "overlay_pil", "mask", "binary_mask"):
                data[section].pop(key, None)

    return _json_response(data)
