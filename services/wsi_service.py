"""Whole-slide image support for the OpenSeadragon viewer.

Two complementary paths, both real (no mocked output):

1. `image_to_data_uri()` — base64-encodes the current slide so OpenSeadragon
   can render it instantly inside a Streamlit `components.html` iframe using
   its `type: "image"` tile source. No file server required; this is what
   powers the live pan/zoom/rotate viewer on the Upload and AI Analysis pages
   today, for any image size Streamlit can hold in memory.

2. `generate_dzi_pyramid()` — a genuine Deep Zoom Image (DZI) tile pyramid
   generator (writes the .dzi XML descriptor plus every resolution level's
   tiles to disk), the real format OpenSeadragon was built for and what a
   production deployment should serve for true gigapixel whole-slide images
   (.svs). Wiring this to a tile HTTP endpoint (e.g. a small FastAPI service,
   or Streamlit's `enableStaticServing` config option) is a deployment step
   documented in the README — this module does the actual image-processing
   work either way.

Note: native `.svs` (Aperio) files require `openslide-python` + the OpenSlide
system library, which is a heavier install than fits this prototype's
dependency footprint. This module works on any image Pillow can open
(PNG/JPEG/TIFF); `.svs` support is a documented future step.
"""

from __future__ import annotations

import base64
import math
from io import BytesIO
from pathlib import Path

from PIL import Image


def image_to_data_uri(image: Image.Image, format: str = "JPEG", max_dim: int = 4096) -> str:
    """Base64 data URI, downscaled so the browser never has to decode an
    unreasonably large payload in a components.html iframe."""
    img = image.convert("RGB")
    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    buffer = BytesIO()
    img.save(buffer, format=format, quality=88)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = "image/jpeg" if format.upper() == "JPEG" else f"image/{format.lower()}"
    return f"data:{mime};base64,{encoded}"


def generate_dzi_pyramid(
    image: Image.Image,
    output_dir: Path,
    tile_size: int = 254,
    overlap: int = 1,
    fmt: str = "jpeg",
) -> Path:
    """Write a real Deep Zoom Image pyramid: `<output_dir>.dzi` descriptor plus
    `<output_dir>_files/<level>/<col>_<row>.<fmt>` tiles, exactly as OpenSeadragon /
    Deep Zoom expects. Returns the path to the .dzi file."""
    output_dir = Path(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    files_dir = output_dir.with_name(output_dir.name + "_files")
    files_dir.mkdir(parents=True, exist_ok=True)

    base = image.convert("RGB")
    max_level = math.ceil(math.log2(max(base.size)))

    # Build the pyramid top-down (full res) then downsample for each lower level.
    current = base
    for level in range(max_level, -1, -1):
        level_dir = files_dir / str(level)
        level_dir.mkdir(parents=True, exist_ok=True)
        w, h = current.size
        cols = math.ceil(w / tile_size)
        rows = math.ceil(h / tile_size)
        for col in range(cols):
            for row in range(rows):
                x0 = max(col * tile_size - overlap, 0)
                y0 = max(row * tile_size - overlap, 0)
                x1 = min(x0 + tile_size + 2 * overlap, w)
                y1 = min(y0 + tile_size + 2 * overlap, h)
                tile = current.crop((x0, y0, x1, y1))
                tile.save(level_dir / f"{col}_{row}.{fmt}", quality=85)
        if w <= 1 and h <= 1:
            break
        current = current.resize((max(1, w // 2), max(1, h // 2)))

    dzi_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image TileSize="{tile_size}" Overlap="{overlap}" Format="{fmt}"
       xmlns="http://schemas.microsoft.com/deepzoom/2008">
    <Size Width="{base.width}" Height="{base.height}"/>
</Image>
"""
    dzi_path = output_dir.with_suffix(".dzi")
    dzi_path.write_text(dzi_xml, encoding="utf-8")
    return dzi_path
