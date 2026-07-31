"""Model registry — integrate trained weights here.

`get_model_status()` powers the Settings page's honest "what's really
running" panel. `load_disease_classifier()` is the single integration point
for real deep-learning inference: the moment a checkpoint exists at
`models/weights/<organ>_<architecture>.pt`, this function returns a loaded
model and `services/ai_analyzer.py` automatically switches from the
classical-CV heuristic to real neural inference (see FEATURE_FLAGS in
config/settings.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st
import torch

from config.settings import DISEASE_CLASSIFIER_PATH_TEMPLATE, NUCLEI_DETECTOR_PATH, TISSUE_CLASSIFIER_PATH
from core.constants import ModelStatus
from models.architectures import ARCHITECTURE_BUILDERS, build_backbone
from models.disease_registry import get_organ


@dataclass
class ModelInfo:
    name: str
    status: ModelStatus
    path: str
    message: str


@st.cache_resource(show_spinner=False)
def load_tissue_classifier():
    if not TISSUE_CLASSIFIER_PATH.exists():
        return None
    return torch.jit.load(str(TISSUE_CLASSIFIER_PATH), map_location="cpu")


@st.cache_resource(show_spinner=False)
def load_nuclei_detector():
    if not NUCLEI_DETECTOR_PATH.exists():
        return None
    return torch.jit.load(str(NUCLEI_DETECTOR_PATH), map_location="cpu")


@st.cache_resource(show_spinner=False)
def load_disease_classifier(organ: str, architecture: str):
    """Return (model, class_names) if a checkpoint exists for this organ+architecture,
    else (None, class_names) so the caller can fall back to the heuristic pipeline."""
    disease_organ = get_organ(organ)
    class_names = disease_organ.classes
    if architecture not in ARCHITECTURE_BUILDERS:
        return None, class_names
    weight_path = Path(DISEASE_CLASSIFIER_PATH_TEMPLATE.format(organ=organ, architecture=architecture.replace("/", "-")))
    model = build_backbone(architecture, num_classes=len(class_names), pretrained_backbone=False)
    if weight_path.exists():
        state = torch.load(str(weight_path), map_location="cpu")
        model.load_state_dict(state)
        model.eval()
        return model, class_names
    return None, class_names


def get_checkpoint_version(organ: str, architecture: str) -> str | None:
    """A short, stable fingerprint for whichever checkpoint file is currently
    backing `organ`+`architecture`, so every analysis result and report can
    say exactly which weights produced it (task: model-version tagging).
    Cheap by design — stats the file (size + mtime) instead of hashing the
    full tensor contents, so it's safe to call on every analysis run even for
    large checkpoints. Returns None when running in heuristic mode."""
    if architecture not in ARCHITECTURE_BUILDERS:
        return None
    weight_path = Path(DISEASE_CLASSIFIER_PATH_TEMPLATE.format(organ=organ, architecture=architecture.replace("/", "-")))
    if not weight_path.exists():
        return None
    stat = weight_path.stat()
    return f"{weight_path.name}#{int(stat.st_mtime)}-{stat.st_size}"


def get_model_status() -> list[ModelInfo]:
    tissue = load_tissue_classifier()
    nuclei = load_nuclei_detector()
    gpu = torch.cuda.is_available()
    return [
        ModelInfo(
            name="Tissue Classifier",
            status=ModelStatus.LOADED if tissue else ModelStatus.PLACEHOLDER,
            path=str(TISSUE_CLASSIFIER_PATH),
            message="Weights not found — using OpenCV segmentation + heuristic labels."
            if not tissue else "Custom TorchScript tissue classifier loaded.",
        ),
        ModelInfo(
            name="Nuclei Detector",
            status=ModelStatus.LOADED if nuclei else ModelStatus.PLACEHOLDER,
            path=str(NUCLEI_DETECTOR_PATH),
            message="Weights not found — using classical CV nuclei pipeline."
            if not nuclei else "Custom TorchScript nuclei detector loaded.",
        ),
        ModelInfo(
            name="Disease Classifiers (10 organs x 5 architectures)",
            status=ModelStatus.PLACEHOLDER,
            path=str(Path(DISEASE_CLASSIFIER_PATH_TEMPLATE).parent),
            message=(
                "Backbone constructors (ResNet50, DenseNet121, EfficientNet-B0, "
                "ConvNeXt-Tiny, ViT-B/16) are implemented in models/architectures.py "
                "and ready to load a checkpoint per organ. No trained weights ship "
                "with this repo — drop a `.pt` in models/weights/ named "
                "`<organ>_<architecture>.pt` (e.g. `breast_ResNet50.pt`) to activate."
            ),
        ),
        ModelInfo(
            name="Compute Device",
            status=ModelStatus.LOADED if gpu else ModelStatus.UNAVAILABLE,
            path="cuda" if gpu else "cpu",
            message="CUDA available." if gpu else "Running on CPU.",
        ),
    ]
