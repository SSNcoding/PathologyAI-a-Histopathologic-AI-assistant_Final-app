"""Batch image analysis — run the full AI pipeline over multiple slides."""

from __future__ import annotations

from typing import Any

from PIL import Image

from services.ai_analyzer import result_to_dict, run_full_analysis


def run_batch_analysis(
    images: list[tuple[str, Image.Image]],
    organ: str,
    architecture: str,
    use_ensemble: bool = False,
    use_tta: bool = False,
    progress_callback=None,
) -> list[dict[str, Any]]:
    """`images` is a list of (filename, PIL.Image). Returns one result dict per image,
    each tagged with `slide_name`. `progress_callback(i, total, name)` is called after
    each slide finishes, so the caller (a Streamlit page) can drive a progress bar."""
    results = []
    total = len(images)
    for i, (name, image) in enumerate(images, start=1):
        result = run_full_analysis(
            image,
            organ=organ,
            architecture=architecture,
            use_ensemble=use_ensemble,
            use_tta=use_tta,
        )
        data = result_to_dict(result)
        data["slide_name"] = name
        results.append(data)
        if progress_callback:
            progress_callback(i, total, name)
    return results
