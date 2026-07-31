"""Synthetic 'demo slide' generator — lets a new visitor try the app without
needing a real histopathology image on hand.

This is procedurally generated at runtime with PIL/numpy (already hard
dependencies) rather than a bundled static image file. That's a deliberate
choice, not a shortcut: bundling a real slide would need either a
license-cleared public-domain histopathology image or a way to fetch one,
and building this while the sandbox this was developed in had no working
shell meant "generate it in pure Python at call time" was both the more
robust option and the one actually available.

What's generated below approximates the visual structure the classical CV
pipeline actually looks at — irregular purple/blue "nuclei" clustered on a
pink "tissue" field with a few pale "background glass" gaps — well enough
to exercise tissue segmentation, nuclei detection, and the heuristic
classifier meaningfully. It is NOT real tissue and must never be presented
to a user as a real slide; callers should label it clearly (see
app_pages/upload.py's "Try a Demo Slide" button).
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DEMO_SLIDE_NAME = "synthetic_demo_slide.png"


def generate_demo_slide(size: tuple[int, int] = (512, 512), seed: int = 7) -> Image.Image:
    rng = np.random.default_rng(seed)
    width, height = size

    # Base: pale pink "tissue" field, roughly evoking an H&E eosin stain.
    base = np.full((height, width, 3), (235, 200, 215), dtype=np.uint8)
    image = Image.fromarray(base, mode="RGB")
    draw = ImageDraw.Draw(image)

    # A few irregular pale gaps, like unstained/background glass regions.
    for _ in range(4):
        cx, cy = int(rng.integers(0, width)), int(rng.integers(0, height))
        r = int(rng.integers(30, 90))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 248, 250))

    # Darker pink "stroma" streaks for texture variation.
    for _ in range(6):
        x1, y1 = int(rng.integers(0, width)), int(rng.integers(0, height))
        x2, y2 = x1 + int(rng.integers(-120, 120)), y1 + int(rng.integers(-120, 120))
        draw.line([x1, y1, x2, y2], fill=(215, 165, 185), width=int(rng.integers(15, 35)))

    image = image.filter(ImageFilter.GaussianBlur(2))
    draw = ImageDraw.Draw(image)

    # Purple/blue "nuclei" — small irregular dark blobs, clustered rather
    # than uniformly scattered, since real nuclei distribute in clusters.
    # Margins scale with image size (capped at 40px) so this doesn't break
    # on small sizes, e.g. in tests that use tiny images.
    margin_x = max(1, min(40, width // 4))
    margin_y = max(1, min(40, height // 4))
    for _ in range(10):
        cx = int(rng.integers(margin_x, max(margin_x + 1, width - margin_x)))
        cy = int(rng.integers(margin_y, max(margin_y + 1, height - margin_y)))
        n_nuclei = int(rng.integers(15, 35))
        for _ in range(n_nuclei):
            nx = int(np.clip(cx + rng.normal(0, 18), 5, max(6, width - 6)))
            ny = int(np.clip(cy + rng.normal(0, 18), 5, max(6, height - 6)))
            r = int(rng.integers(3, 7))
            purple = (
                int(np.clip(60 + rng.integers(-15, 15), 0, 255)),
                int(np.clip(30 + rng.integers(-10, 10), 0, 255)),
                int(np.clip(90 + rng.integers(-15, 15), 0, 255)),
            )
            draw.ellipse([nx - r, ny - r, nx + r, ny + r], fill=purple)

    return image
