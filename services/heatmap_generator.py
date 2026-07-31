"""Generate saliency-style heatmaps from detection density (CV-based, not neural)."""
from __future__ import annotations
import cv2
import numpy as np
from PIL import Image

def generate_attention_heatmap(image: Image.Image, points: list[tuple[int, int]], sigma: int = 25) -> Image.Image:
    """
    Build a heatmap from nuclei centroids using Gaussian splatting.
    Replace with Grad-CAM / model attention when PyTorch model is integrated.
    """
    rgb = np.array(image.convert("RGB"))
    h, w = rgb.shape[:2]
    heat = np.zeros((h, w), dtype=np.float32)
    for x, y in points:
        cv2.circle(heat, (x, y), 8, 1.0, -1)
    heat = cv2.GaussianBlur(heat, (0, 0), sigmaX=sigma, sigmaY=sigma)
    if heat.max() > 0:
        heat = heat / heat.max()
    heat_color = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heat_rgb = cv2.cvtColor(heat_color, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(rgb, 0.55, heat_rgb, 0.45, 0)
    return Image.fromarray(overlay)
