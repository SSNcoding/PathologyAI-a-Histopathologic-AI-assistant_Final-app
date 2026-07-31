"""Explainable AI: Grad-CAM, Grad-CAM++, and an occlusion-sensitivity map.

Grad-CAM / Grad-CAM++ here are real, working implementations (forward +
backward hooks on a convolutional layer) — they will produce genuine
gradient-based saliency maps the moment a real trained CNN is loaded via
`models/model_registry.py`. They are not runnable in HEURISTIC_PLACEHOLDER
mode because there is no network to differentiate through.

`occlusion_sensitivity_map` is a model-agnostic, gradient-free alternative
(slide a gray patch over the image, measure how much the top-class score
drops) — it's a legitimate lightweight stand-in for SHAP/LIME-style
perturbation explanations without adding the `shap`/`lime` dependencies.
It works today, even in placeholder mode, using the classical-CV confidence
score as the function being explained.
"""

from __future__ import annotations

from typing import Callable

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


class GradCAM:
    """Standard Grad-CAM (Selvaraju et al., 2017) via forward/backward hooks."""

    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations: torch.Tensor | None = None
        self.gradients: torch.Tensor | None = None
        self._fwd_handle = target_layer.register_forward_hook(self._save_activation)
        self._bwd_handle = target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, inp, out):
        self.activations = out.detach()

    def _save_gradient(self, module, grad_in, grad_out):
        self.gradients = grad_out[0].detach()

    def __call__(self, input_tensor: torch.Tensor, class_idx: int | None = None, plus_plus: bool = False) -> np.ndarray:
        self.model.zero_grad()
        output = self.model(input_tensor)
        if class_idx is None:
            class_idx = int(output.argmax(dim=1).item())
        score = output[:, class_idx].sum()
        score.backward()

        activations = self.activations[0]  # (C, H, W)
        gradients = self.gradients[0]  # (C, H, W)

        if plus_plus:
            # Grad-CAM++ weighting (Chattopadhyay et al., 2018).
            grads_power_2 = gradients ** 2
            grads_power_3 = grads_power_2 * gradients
            sum_acts = activations.sum(dim=(1, 2), keepdim=True)
            eps = 1e-8
            alpha = grads_power_2 / (2 * grads_power_2 + sum_acts * grads_power_3 + eps)
            weights = (alpha * F.relu(gradients)).sum(dim=(1, 2))
        else:
            weights = gradients.mean(dim=(1, 2))

        cam = F.relu((weights[:, None, None] * activations).sum(dim=0))
        cam = cam.cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()
        return cam

    def close(self):
        self._fwd_handle.remove()
        self._bwd_handle.remove()


def overlay_cam_on_image(image: Image.Image, cam: np.ndarray, alpha: float = 0.45) -> Image.Image:
    rgb = np.array(image.convert("RGB"))
    h, w = rgb.shape[:2]
    cam_resized = cv2.resize(cam, (w, h))
    heat_color = cv2.applyColorMap((cam_resized * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heat_rgb = cv2.cvtColor(heat_color, cv2.COLOR_BGR2RGB)
    blended = cv2.addWeighted(rgb, 1 - alpha, heat_rgb, alpha, 0)
    return Image.fromarray(blended)


def occlusion_sensitivity_map(
    image: Image.Image,
    score_fn: Callable[[Image.Image], float],
    patch_size: int = 32,
    stride: int = 16,
    baseline_color: tuple[int, int, int] = (127, 127, 127),
) -> np.ndarray:
    """Model-agnostic saliency: for each patch location, occlude it and measure the
    drop in `score_fn(image)`. Larger drop => that region mattered more for the score.
    Returns a normalized (H, W) float32 array. This is intentionally simple (no external
    `shap`/`lime` dependency) but is a real, working perturbation-based explanation
    technique, applicable to the classical-CV heuristic score or a real model alike.
    """
    rgb = np.array(image.convert("RGB"))
    h, w = rgb.shape[:2]
    heat = np.zeros((h, w), dtype=np.float32)
    counts = np.zeros((h, w), dtype=np.float32)

    base_score = score_fn(image)

    for y in range(0, h, stride):
        for x in range(0, w, stride):
            patch = rgb.copy()
            y2, x2 = min(y + patch_size, h), min(x + patch_size, w)
            patch[y:y2, x:x2] = baseline_color
            occluded_score = score_fn(Image.fromarray(patch))
            drop = max(0.0, base_score - occluded_score)
            heat[y:y2, x:x2] += drop
            counts[y:y2, x:x2] += 1

    counts[counts == 0] = 1
    heat = heat / counts
    if heat.max() > 0:
        heat = heat / heat.max()
    return heat


def explain_with_best_available(
    image: Image.Image,
    model: torch.nn.Module | None,
    target_layer: torch.nn.Module | None,
    input_tensor: torch.Tensor | None,
    fallback_score_fn: Callable[[Image.Image], float],
) -> dict:
    """Pick real Grad-CAM if a torch model + target layer are available, otherwise
    fall back to occlusion sensitivity over the heuristic score. Always returns a
    dict with a `method` field so the UI can label the explanation honestly."""
    if model is not None and target_layer is not None and input_tensor is not None:
        cam_engine = GradCAM(model, target_layer)
        try:
            cam = cam_engine(input_tensor)
        finally:
            cam_engine.close()
        overlay = overlay_cam_on_image(image, cam)
        return {"method": "Grad-CAM (neural)", "overlay": overlay, "raw": cam}

    heat = occlusion_sensitivity_map(image, fallback_score_fn)
    overlay = overlay_cam_on_image(image, heat)
    return {"method": "Occlusion Sensitivity (model-agnostic, SHAP/LIME-lite)", "overlay": overlay, "raw": heat}
