# PathologyAI

AI-powered computational pathology platform (Streamlit) for research and education. Analyzes
histopathology images with computer vision, tracks a modular 10-organ disease taxonomy, and
ships with real (but currently untrained) deep-learning architectures ready to activate the
moment you have trained weights.

## Honesty-first status

This section exists because it matters more than any feature list: **know exactly what's real.**

| Capability | Status |
|---|---|
| Tissue segmentation, nuclei detection, heatmaps | **Real** — classical OpenCV pipeline (`services/image_processor.py`) |
| Tumor %, healthy %, inflammation/necrosis/mitotic scores | **Real heuristic**, not clinically validated (`estimate_tumor_metrics`) |
| PDF / CSV / JSON reports | **Real**, generated from the above |
| OpenSeadragon whole-slide viewer | **Real** — live pan/zoom today; true Deep Zoom tiling implemented (`services/wsi_service.py`) for a production tile server |
| 10-organ / multi-class disease registry | **Real & modular** (`models/disease_registry.py`) — but predictions are heuristic until trained |
| EfficientNet / ViT / ResNet / DenseNet / ConvNeXt backbones | **Real PyTorch code** (`models/architectures.py`), **no trained weights ship with this repo** |
| Grad-CAM / Grad-CAM++ | **Real, working** hook-based implementation (`services/gradcam.py`) — only runnable once a real model is loaded; falls back to occlusion sensitivity otherwise |
| U-Net segmentation | **Real architecture** (`models/segmentation.py`), untrained |
| Ensemble models, Test-Time Augmentation | **Real code**, only meaningful once real weights exist |
| Login / registration / saved analyses / notifications | **Real**, SQLite-backed (prototype-grade auth, not HIPAA-compliant) |
| Cancer staging, survival prediction, biomarker prediction | **Not implemented** — these need clinical/molecular data beyond one image. Kept out of the live UI per design decision; see "Research-only features" below |

**Bottom line:** until you drop trained `.pt` checkpoints into `models/weights/`, every prediction
in the app is labeled `HEURISTIC_PLACEHOLDER` and is NOT a diagnostic claim.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
streamlit run app_create.py
```

First run creates a local SQLite database at `output/data/pathologyai.db` — register an account
from the Register page to explore the authenticated app (Dashboard, Upload, AI Analysis, etc.).

## Project layout

```
app_create.py           Entry point — nav, auth gate, page routing
config/settings.py      Paths, feature flags, env-driven secrets
core/                    constants, session state, security (password hashing)
db/database.py          SQLite schema + connection helper
models/
  disease_registry.py   10-organ class taxonomy — add an organ here, nothing else changes
  architectures.py      Real torchvision backbones + ensemble + TTA + calibration
  segmentation.py       U-Net (untrained)
  model_registry.py     Loads weights if present, else returns None (heuristic fallback)
services/
  image_processor.py    Classical CV: tissue/nuclei detection, edits, quantitative metrics
  ai_analyzer.py         Orchestrates analysis; switches heuristic <-> neural automatically
  gradcam.py             Grad-CAM/Grad-CAM++ + occlusion-sensitivity fallback
  wsi_service.py         OpenSeadragon data URIs + real DZI tile pyramid generator
  batch_service.py, export_service.py, auth_service.py, analysis_store.py, notification_service.py
  pdf_report.py          Full patient report generator (ReportLab)
ui/                      theme.py (light/dark), components.py, charts.py, landing.py
app_pages/               One module per page — see NAV_APP in core/constants.py
                         (named app_pages, not pages, so Streamlit doesn't auto-generate
                         its own native sidebar nav on top of the custom one)
output/                  Generated reports, uploads, DZI tiles, SQLite DB (gitignored contents)
```

## Adding a new disease/organ

Add one `DiseaseOrgan` entry to `DISEASE_REGISTRY` in `models/disease_registry.py`. Every page,
chart, and report reads from that registry — no other file needs to change.

## Training and wiring in a real model

1. Fine-tune a backbone from `models/architectures.py` (or your own) on a dataset from the table
   below, for the organ you care about.
2. Export weights as a plain `state_dict` to `models/weights/<organ>_<architecture>.pt`
   (e.g. `models/weights/breast_ResNet50.pt` — architecture name matches `ModelArchitecture` values
   with `/` replaced by `-`).
3. Restart the app. `services/ai_analyzer.py` detects the checkpoint via
   `models/model_registry.load_disease_classifier()` and automatically switches that organ from
   `HEURISTIC_PLACEHOLDER` to `PYTORCH` mode, including real Grad-CAM on the Explainable AI page.

### Recommended datasets (see `models/disease_registry.py` for per-organ mapping)

CAMELYON16 / CAMELYON17 (breast metastasis) · PANDA (prostate grading) · BreakHis (breast) ·
LC25000 (lung & colon) · PCam (PatchCamelyon) · TCGA (pan-cancer, per-organ cohorts) ·
The Cancer Imaging Archive (TCIA).

### Reference architectures

EfficientNet-B0–B7, Vision Transformer (ViT), Swin Transformer, ConvNeXt, DenseNet121, ResNet50,
U-Net / U-Net++ (segmentation), Mask R-CNN (instance segmentation), YOLOv11 (cell detection) —
the first five classification backbones and U-Net ship as real code today; Swin/U-Net++/Mask
R-CNN/YOLOv11 are documented integration points, not yet implemented, to keep this repo's
dependency footprint reasonable.

### Explainability

Grad-CAM and Grad-CAM++ are implemented in `services/gradcam.py`. SHAP and LIME are not added as
dependencies; `occlusion_sensitivity_map()` in the same module is a lightweight, dependency-free
perturbation-based alternative that works today against the heuristic score.

## Research-only features (intentionally not implemented)

Cancer staging, survival risk prediction, and biomarker prediction all require clinical or
molecular data beyond a single histopathology image (TNM staging data, longitudinal outcomes,
IHC/genomic ground truth). Faking these from image features alone would be misleading, so they
are surfaced in the UI (About page) as explicitly labeled research/future items rather than
working features.

## Deployment

- **Streamlit Community Cloud**: point it at `app_create.py`; SQLite persists to the app's
  ephemeral filesystem (fine for a demo, add a managed Postgres for real persistence — see below).
- **Docker**: `docker compose up --build` (see `Dockerfile` / `docker-compose.yml`).
- **CI**: `.github/workflows/ci.yml` runs a byte-compile check on every push/PR.
- **Upgrading auth/storage for production**: swap `db/database.py`'s SQLite connection for
  PostgreSQL (the function signatures are already dict-in/dict-out, so callers don't change),
  and consider Firebase Authentication or a proper OAuth provider instead of the built-in
  PBKDF2 login.

## Disclaimer

Research and education use only. Not a medical device. Not for primary diagnosis or treatment
decisions. All AI-derived findings must be reviewed by a qualified pathologist.
