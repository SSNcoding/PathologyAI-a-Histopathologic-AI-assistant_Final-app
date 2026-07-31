"""CSV / JSON export of analysis results."""

from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any


def result_to_json_bytes(result: dict[str, Any]) -> bytes:
    exportable = {k: v for k, v in result.items() if k != "heatmap"}
    return json.dumps(exportable, indent=2, default=str).encode("utf-8")


def result_to_csv_bytes(result: dict[str, Any]) -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    writer.writerow(["organ", result.get("organ")])
    writer.writerow(["architecture", result.get("architecture")])
    writer.writerow(["model_mode", result.get("model_mode")])
    writer.writerow(["risk_level", result.get("risk_level")])
    writer.writerow(["confidence", result.get("confidence")])
    writer.writerow(["processing_time_s", result.get("processing_time_s")])
    tissue = result.get("tissue", {}) or {}
    cells = result.get("cells", {}) or {}
    tumor = result.get("tumor_metrics", {}) or {}
    quality = result.get("quality", {}) or {}
    for key in ("tissue_coverage_pct", "background_pct", "region_count"):
        writer.writerow([f"tissue.{key}", tissue.get(key)])
    for key in ("nuclei_count", "density_per_mpx", "mean_area"):
        writer.writerow([f"cells.{key}", cells.get(key)])
    for key in ("tumor_pct", "healthy_tissue_pct", "inflammation_score", "necrosis_score", "mitotic_count"):
        writer.writerow([f"tumor_metrics.{key}", tumor.get(key)])
    for key in ("score", "label"):
        writer.writerow([f"quality.{key}", quality.get(key)])
    writer.writerow([])
    writer.writerow(["finding_label", "finding_confidence"])
    for finding in result.get("findings", []) or []:
        writer.writerow([finding.get("label"), finding.get("confidence")])
    return buffer.getvalue().encode("utf-8")


def batch_results_to_csv_bytes(results: list[dict[str, Any]]) -> bytes:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "slide_name", "organ", "architecture", "model_mode", "top_finding",
        "confidence", "risk_level", "nuclei_count", "tissue_coverage_pct",
        "tumor_pct", "processing_time_s",
    ])
    for r in results:
        top = (r.get("findings") or [{}])[0]
        writer.writerow([
            r.get("slide_name"), r.get("organ"), r.get("architecture"), r.get("model_mode"),
            top.get("label"), top.get("confidence"), r.get("risk_level"),
            (r.get("cells") or {}).get("nuclei_count"),
            (r.get("tissue") or {}).get("tissue_coverage_pct"),
            (r.get("tumor_metrics") or {}).get("tumor_pct"),
            r.get("processing_time_s"),
        ])
    return buffer.getvalue().encode("utf-8")
