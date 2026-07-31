"""Real (untrained-by-default) classification backbones + ensembling + TTA.

Every constructor here returns a genuine `torch.nn.Module` from torchvision
with its classifier head replaced for the requested number of classes. With
`pretrained_backbone=False` (the default) no network download is required and
the app boots offline — flip it to True to start from ImageNet weights.

None of these backbones are trained on histopathology data yet (no weights
ship with this repo — see `models/weights/`). Until you fine-tune and drop a
checkpoint in `models/weights/`, predictions from `predict_single` /
`predict_ensemble` are effectively random and MUST NOT be treated as real
diagnostic output. The classical CV heuristic pipeline in
`services/ai_analyzer.py` is the only pathway wired to the live UI by
default; this module exists so the moment you have trained weights, wiring
them in is a one-line change to `models/model_registry.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms

ARCHITECTURE_BUILDERS = {}


def register(name: str):
    def _wrap(fn):
        ARCHITECTURE_BUILDERS[name] = fn
        return fn
    return _wrap


@register("ResNet50")
def build_resnet50(num_classes: int, pretrained_backbone: bool = False) -> nn.Module:
    weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained_backbone else None
    model = models.resnet50(weights=weights)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


@register("DenseNet121")
def build_densenet121(num_classes: int, pretrained_backbone: bool = False) -> nn.Module:
    weights = models.DenseNet121_Weights.IMAGENET1K_V1 if pretrained_backbone else None
    model = models.densenet121(weights=weights)
    model.classifier = nn.Linear(model.classifier.in_features, num_classes)
    return model


@register("EfficientNet-B0")
def build_efficientnet_b0(num_classes: int, pretrained_backbone: bool = False) -> nn.Module:
    weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained_backbone else None
    model = models.efficientnet_b0(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


@register("ConvNeXt-Tiny")
def build_convnext_tiny(num_classes: int, pretrained_backbone: bool = False) -> nn.Module:
    weights = models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1 if pretrained_backbone else None
    model = models.convnext_tiny(weights=weights)
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, num_classes)
    return model


@register("ViT-B/16")
def build_vit_b16(num_classes: int, pretrained_backbone: bool = False) -> nn.Module:
    weights = models.ViT_B_16_Weights.IMAGENET1K_V1 if pretrained_backbone else None
    model = models.vit_b_16(weights=weights)
    model.heads.head = nn.Linear(model.heads.head.in_features, num_classes)
    return model


def build_backbone(name: str, num_classes: int, pretrained_backbone: bool = False) -> nn.Module:
    if name not in ARCHITECTURE_BUILDERS:
        raise ValueError(f"Unknown architecture '{name}'. Options: {list(ARCHITECTURE_BUILDERS)}")
    return ARCHITECTURE_BUILDERS[name](num_classes, pretrained_backbone=pretrained_backbone)


# ---------------------------------------------------------------------------
# Inference transforms (standard ImageNet normalization, 224x224 crop)
# ---------------------------------------------------------------------------
INFERENCE_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

# Test-time augmentation views: identity + horizontal flip + vertical flip + 90-degree rotation.
TTA_TRANSFORMS = [
    transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()]),
    transforms.Compose([transforms.Resize((224, 224)), transforms.RandomHorizontalFlip(p=1.0), transforms.ToTensor()]),
    transforms.Compose([transforms.Resize((224, 224)), transforms.RandomVerticalFlip(p=1.0), transforms.ToTensor()]),
    transforms.Compose([transforms.Resize((224, 224)), lambda im: im.rotate(90), transforms.ToTensor()]),
]
_NORMALIZE = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])


@dataclass
class Prediction:
    class_probs: dict[str, float]
    top_class: str
    top_confidence: float
    architecture: str
    # Per-TTA-view probabilities for the winning class, when available — lets the
    # UI show real uncertainty (spread across augmented views) instead of a bare
    # single confidence number. None for predict_single()/predict_ensemble().
    calibration_samples: list[float] | None = None


@torch.no_grad()
def predict_single(model: nn.Module, image, class_names: list[str], architecture: str = "") -> Prediction:
    model.eval()
    tensor = _NORMALIZE(INFERENCE_TRANSFORM.transforms[1](INFERENCE_TRANSFORM.transforms[0](image))).unsqueeze(0)
    logits = model(tensor)
    probs = F.softmax(logits, dim=1).squeeze(0).tolist()
    class_probs = {name: float(p) for name, p in zip(class_names, probs)}
    top_class = max(class_probs, key=class_probs.get)
    return Prediction(class_probs, top_class, class_probs[top_class], architecture)


@torch.no_grad()
def predict_with_tta(model: nn.Module, image, class_names: list[str], architecture: str = "") -> Prediction:
    """Average softmax probabilities across TTA_TRANSFORMS views. Also keeps each
    view's probability for the winning class as `calibration_samples`, so the UI
    can show real spread (min/max/std across augmented views) instead of just
    the mean — a cheap, honest uncertainty signal that doesn't require a
    separate calibration dataset."""
    model.eval()
    all_probs = []
    for tfm in TTA_TRANSFORMS:
        tensor = _NORMALIZE(tfm(image)).unsqueeze(0)
        logits = model(tensor)
        all_probs.append(F.softmax(logits, dim=1).squeeze(0))
    stacked = torch.stack(all_probs)
    mean_probs = stacked.mean(dim=0).tolist()
    class_probs = {name: float(p) for name, p in zip(class_names, mean_probs)}
    top_class = max(class_probs, key=class_probs.get)
    top_idx = class_names.index(top_class)
    calibration_samples = stacked[:, top_idx].tolist()
    return Prediction(
        class_probs, top_class, class_probs[top_class], f"{architecture} + TTA",
        calibration_samples=calibration_samples,
    )


@torch.no_grad()
def predict_ensemble(models_list: list[nn.Module], image, class_names: list[str], names: list[str] | None = None) -> Prediction:
    """Average softmax probabilities across multiple architectures (soft-voting ensemble)."""
    all_probs = []
    for model in models_list:
        model.eval()
        tensor = _NORMALIZE(INFERENCE_TRANSFORM.transforms[1](INFERENCE_TRANSFORM.transforms[0](image))).unsqueeze(0)
        logits = model(tensor)
        all_probs.append(F.softmax(logits, dim=1).squeeze(0))
    mean_probs = torch.stack(all_probs).mean(dim=0).tolist()
    class_probs = {name: float(p) for name, p in zip(class_names, mean_probs)}
    top_class = max(class_probs, key=class_probs.get)
    label = "Ensemble(" + "+".join(names or [f"model{i}" for i in range(len(models_list))]) + ")"
    return Prediction(class_probs, top_class, class_probs[top_class], label)


def temperature_scale(logits: torch.Tensor, temperature: float = 1.5) -> torch.Tensor:
    """Simple confidence calibration: divide logits by a learned/fixed temperature > 1
    before softmax to soften overconfident predictions. Fit `temperature` on a held-out
    validation set with `scripts/fit_temperature.py` (see README) once real weights exist.
    """
    return logits / max(temperature, 1e-6)
