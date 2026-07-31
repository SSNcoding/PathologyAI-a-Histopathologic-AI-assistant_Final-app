"""Generate downloadable pathology PDF reports with ReportLab."""
from __future__ import annotations

import hashlib
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _report_id(patient_id: str, slide_name: str, generated_at: datetime) -> str:
    """Short, deterministic-looking reference number for this report — not a
    database primary key, just something a physician can cite ('per report
    PA-3F9A21') the way a real pathology report has an accession number."""
    raw = f"{patient_id}|{slide_name}|{generated_at.isoformat()}".encode("utf-8")
    return "PA-" + hashlib.sha256(raw).hexdigest()[:8].upper()


def _header_footer(patient_id: str, report_id: str, institution: str):
    """Returns a ReportLab onPage callback drawing a running header/footer on
    every page — patient/specimen ID + institution at top, page number +
    report ID + confidentiality line at bottom. Real pathology reports are
    almost always identifiable on every page, not just the first."""

    def _draw(canvas, doc):
        canvas.saveState()
        width, height = letter
        # Header
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(0.75 * inch, height - 0.5 * inch, institution or "PathologyAI")
        canvas.drawRightString(width - 0.75 * inch, height - 0.5 * inch, f"Specimen: {patient_id}")
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(0.75 * inch, height - 0.55 * inch, width - 0.75 * inch, height - 0.55 * inch)
        # Footer
        canvas.line(0.75 * inch, 0.6 * inch, width - 0.75 * inch, 0.6 * inch)
        canvas.drawString(0.75 * inch, 0.45 * inch, f"Report ID: {report_id} — CONFIDENTIAL, research/education use only")
        canvas.drawRightString(width - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    return _draw


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Heading1"], fontSize=18,
            textColor=colors.HexColor("#0F172A"), spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontSize=10, leading=14,
            textColor=colors.HexColor("#334155"),
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"], fontSize=12,
            textColor=colors.HexColor("#0F172A"), spaceBefore=10, spaceAfter=6,
        ),
        "disclaimer": ParagraphStyle(
            "Disclaimer", parent=base["Normal"], fontSize=8, leading=11,
            textColor=colors.HexColor("#DC2626"),
        ),
    }


def _recommended_next_steps(risk_level: str) -> list[str]:
    """Generic, non-prescriptive next-step language — deliberately conservative.
    This is NOT a clinical decision-support recommendation engine."""
    base = [
        "Correlate findings with clinical history, prior pathology, and relevant imaging.",
        "Have a board-certified pathologist review the original slide before any decision.",
    ]
    if risk_level == "high":
        base.insert(0, "Findings flagged as higher risk by the model — prioritize expert pathologist review.")
    elif risk_level == "moderate":
        base.insert(0, "Findings show moderate-risk features — routine pathologist review recommended.")
    else:
        base.insert(0, "Findings appear low-risk under this heuristic; routine follow-up per institutional protocol.")
    return base


def build_pdf_report(
    *,
    patient_id: str,
    slide_name: str,
    physician: str,
    institution: str,
    summary: str,
    findings: list[dict],
    tissue_stats: dict,
    cell_stats: dict,
    thumbnail_path: Path | None = None,
    patient_name: str = "",
    patient_age: str = "",
    patient_sex: str = "",
    organ: str = "",
    architecture: str = "",
    model_mode: str = "",
    risk_level: str = "low",
    tumor_metrics: dict | None = None,
    quality: dict | None = None,
    heatmap_path: Path | None = None,
    processing_time_s: float | None = None,
    model_version: str | None = None,
) -> bytes:
    generated_at = datetime.now()
    report_id = _report_id(patient_id, slide_name, generated_at)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.95 * inch, bottomMargin=0.85 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )
    styles = _styles()
    story = []
    tumor_metrics = tumor_metrics or {}
    quality = quality or {}

    story.append(Paragraph("PathologyAI — Computational Pathology Report", styles["title"]))
    story.append(Paragraph(f"Report ID: {report_id}  ·  Generated: {generated_at:%Y-%m-%d %H:%M}", styles["body"]))
    story.append(Spacer(1, 0.2 * inch))

    meta = [
        ["Patient / Specimen ID", patient_id],
        ["Patient Name", patient_name or "—"],
        ["Age / Sex", f"{patient_age or '—'} / {patient_sex or '—'}"],
        ["Slide", slide_name],
        ["Organ / Disease Focus", organ or "—"],
        ["Reviewing Physician", physician],
        ["Institution", institution],
        ["Model Used", f"{architecture or '—'} ({model_mode or 'HEURISTIC_PLACEHOLDER'})"],
        ["Model Version", model_version or "—"],
        ["Processing Time", f"{processing_time_s:.2f} s" if processing_time_s else "—"],
    ]
    table = Table(meta, colWidths=[2.0 * inch, 4.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.25 * inch))

    thumb_ok = thumbnail_path and Path(thumbnail_path).exists()
    heatmap_ok = heatmap_path and Path(heatmap_path).exists()
    if thumb_ok or heatmap_ok:
        story.append(Paragraph("Slide & Explainability Heatmap", styles["section"]))
        img_cells = [
            RLImage(str(thumbnail_path), width=2.9 * inch, height=2.0 * inch) if thumb_ok else Paragraph("(no thumbnail)", styles["body"]),
            RLImage(str(heatmap_path), width=2.9 * inch, height=2.0 * inch) if heatmap_ok else Paragraph("(no heatmap)", styles["body"]),
        ]
        img_table = Table([img_cells], colWidths=[3.1 * inch, 3.1 * inch])
        img_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(img_table)
        story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Clinical Summary", styles["section"]))
    story.append(Paragraph(summary.replace("**", "").replace("_", ""), styles["body"]))

    story.append(Paragraph("Quantitative Findings", styles["section"]))
    quant = [
        ["Metric", "Value"],
        ["Tissue Coverage", f"{tissue_stats.get('tissue_coverage_pct', 0)}%"],
        ["Tissue Regions", str(tissue_stats.get("region_count", 0))],
        ["Nuclei Count", str(cell_stats.get("nuclei_count", 0))],
        ["Nuclei Density (per Mpx)", str(cell_stats.get("density_per_mpx", 0))],
        ["Mean Nuclei Area (px²)", str(cell_stats.get("mean_area", 0))],
        ["Tumor % (heuristic)", f"{tumor_metrics.get('tumor_pct', '—')}%"],
        ["Healthy Tissue % (heuristic)", f"{tumor_metrics.get('healthy_tissue_pct', '—')}%"],
        ["Inflammation Score (0-10)", str(tumor_metrics.get("inflammation_score", "—"))],
        ["Necrosis Score (0-10)", str(tumor_metrics.get("necrosis_score", "—"))],
        ["Mitotic-like Count (heuristic)", str(tumor_metrics.get("mitotic_count", "—"))],
        ["Slide Quality", f"{quality.get('label', '—')} ({quality.get('score', '—')}/100)"],
    ]
    qtable = Table(quant, colWidths=[2.7 * inch, 3.8 * inch])
    qtable.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#06B6D4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(qtable)

    story.append(Paragraph("Detected Abnormalities / Classification Confidence", styles["section"]))
    for item in findings:
        story.append(Paragraph(f"• {item['label']}: {item['confidence']:.1%}", styles["body"]))

    story.append(Paragraph("Recommended Next Steps", styles["section"]))
    for step in _recommended_next_steps(risk_level):
        story.append(Paragraph(f"• {step}", styles["body"]))

    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph("Pathologist Review & Sign-Off", styles["section"]))
    sig_table = Table(
        [["Reviewing Pathologist Signature:", "", "Date:", ""]],
        colWidths=[1.7 * inch, 2.6 * inch, 0.6 * inch, 1.6 * inch],
    )
    sig_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155")),
        ("LINEBELOW", (1, 0), (1, 0), 0.5, colors.HexColor("#94A3B8")),
        ("LINEBELOW", (3, 0), (3, 0), 0.5, colors.HexColor("#94A3B8")),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "DISCLAIMER: This report is generated by a research/educational computational pathology "
        "platform. Findings marked HEURISTIC_PLACEHOLDER come from classical computer-vision "
        "feature heuristics, not a trained diagnostic model, and every quantitative estimate here "
        "is unvalidated. This report is not intended for primary diagnosis or treatment decisions "
        "and must be reviewed by a qualified pathologist. Staging, survival, and biomarker "
        "predictions are not included because they require clinical data beyond a single image.",
        styles["disclaimer"],
    ))

    page_callback = _header_footer(patient_id, report_id, institution)
    doc.build(story, onFirstPage=page_callback, onLaterPages=page_callback)
    return buffer.getvalue()
