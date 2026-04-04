"""
utils/report_pdf.py
Aymen — Day 5: PDF report export
Converts the generated markdown report text into a styled PDF using reportlab.
No extra dependencies beyond reportlab (already in requirements.txt after Day 5).
"""

import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ── Colour palette (matches BOB's pink/dark theme loosely) ──────────────────
BRAND_DARK  = colors.HexColor("#1a1a2e")   # near-black for headings
BRAND_RED   = colors.HexColor("#e63946")   # critical / alert red
BRAND_BLUE  = colors.HexColor("#2855C8")   # section heading blue
BRAND_GREY  = colors.HexColor("#6c757d")   # caption / meta text
PAGE_BG     = colors.white


def _build_styles():
    """Return a dict of named ParagraphStyles for the report."""
    base = getSampleStyleSheet()

    styles = {}

    styles["title"] = ParagraphStyle(
        "ReportTitle",
        parent=base["Title"],
        fontSize=22,
        textColor=BRAND_DARK,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    styles["subtitle"] = ParagraphStyle(
        "ReportSubtitle",
        parent=base["Normal"],
        fontSize=10,
        textColor=BRAND_GREY,
        spaceAfter=2,
    )
    styles["h1"] = ParagraphStyle(
        "H1",
        parent=base["Heading1"],
        fontSize=13,
        textColor=BRAND_BLUE,
        spaceBefore=14,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        borderPad=2,
    )
    styles["body"] = ParagraphStyle(
        "Body",
        parent=base["Normal"],
        fontSize=10,
        textColor=BRAND_DARK,
        spaceAfter=4,
        leading=15,
    )
    styles["bullet"] = ParagraphStyle(
        "Bullet",
        parent=base["Normal"],
        fontSize=10,
        textColor=BRAND_DARK,
        leftIndent=16,
        spaceAfter=3,
        leading=14,
        bulletIndent=6,
    )
    styles["critical"] = ParagraphStyle(
        "Critical",
        parent=base["Normal"],
        fontSize=10,
        textColor=BRAND_RED,
        leftIndent=16,
        spaceAfter=3,
        leading=14,
        fontName="Helvetica-Bold",
    )
    styles["footer"] = ParagraphStyle(
        "Footer",
        parent=base["Normal"],
        fontSize=8,
        textColor=BRAND_GREY,
        alignment=1,  # centre
    )

    return styles


def _header_table(project: dict) -> Table:
    """Top meta block: project name, address, inspector, date."""
    date_str = datetime.now().strftime("%d %B %Y")
    data = [
        ["Project",   project.get("name", "—")],
        ["Address",   project.get("address", "—")],
        ["Type",      project.get("building_type", "—")],
        ["Inspector", project.get("inspector", "—")],
        ["Date",      date_str],
    ]
    t = Table(data, colWidths=[3.5 * cm, 13 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",  (0, 0), (0, -1), BRAND_GREY),
        ("TEXTCOLOR",  (1, 0), (1, -1), BRAND_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW",  (0, -1), (-1, -1), 0.5, BRAND_GREY),
    ]))
    return t


def _parse_markdown_report(report_text: str, styles: dict) -> list:
    """
    Convert the LLM-generated markdown report into reportlab Flowables.
    Handles: # headings, ## headings, - bullet lines, plain paragraphs.
    Lines containing 'critical' get red styling.
    """
    flowables = []

    for line in report_text.splitlines():
        stripped = line.strip()

        if not stripped:
            flowables.append(Spacer(1, 6))
            continue

        # H1 / H2 headings
        if stripped.startswith("## "):
            flowables.append(Paragraph(stripped[3:], styles["h1"]))
            continue
        if stripped.startswith("# "):
            flowables.append(Paragraph(stripped[2:], styles["h1"]))
            continue

        # Numbered section headings like "1. Executive Summary"
        if re.match(r"^\d+\.\s+[A-Z]", stripped):
            flowables.append(Paragraph(stripped, styles["h1"]))
            continue

        # Bullet points
        if stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            # Critical items get red
            if "critical" in text.lower() or "urgent" in text.lower():
                flowables.append(Paragraph(f"• {text}", styles["critical"]))
            else:
                flowables.append(Paragraph(f"• {text}", styles["bullet"]))
            continue

        # Checkmark / cross lines from the prompt
        if stripped.startswith("✓") or stripped.startswith("✗"):
            is_critical = "critical" in stripped.lower()
            s = styles["critical"] if is_critical else styles["bullet"]
            flowables.append(Paragraph(stripped, s))
            continue

        # Plain paragraph — red if it mentions critical
        if "critical" in stripped.lower() and len(stripped) < 200:
            flowables.append(Paragraph(stripped, styles["critical"]))
        else:
            flowables.append(Paragraph(stripped, styles["body"]))

    return flowables


def build_pdf(report_text: str, project: dict, photos: list = None, signature: str = None, signed_at: str = None) -> bytes:
    """
    Full pipeline: markdown report text + project dict → PDF bytes.
    Returns raw bytes ready to pass to st.download_button().

    Usage:
        from utils.report_pdf import build_pdf
        pdf_bytes = build_pdf(report_text, project)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        title=f"Inspection Report — {project.get('name', '')}",
        author=project.get("inspector", "BOB Inspector"),
    )

    styles = _build_styles()
    story  = []

    # ── Cover block ──────────────────────────────────────────
    story.append(Paragraph("Inspection Report", styles["title"]))
    story.append(Paragraph("Construction Safety — BOB AI Inspector", styles["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(_header_table(project))
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_BLUE))
    story.append(Spacer(1, 10))

    # ── Report body (parsed from markdown) ───────────────────
    story.extend(_parse_markdown_report(report_text, styles))

    # ── Hazard photo section ──────────────────────────────────
    hazard_photos = [p for p in (photos or []) if p.get("hazard_flag") and p.get("image_bytes")]
    if hazard_photos:
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Photo Evidence — Hazard Findings", styles["h1"]))
        story.append(Spacer(1, 8))
        for photo in hazard_photos:
            try:
                img_buf = io.BytesIO(photo["image_bytes"])
                img = Image(img_buf, width=12 * cm, height=8 * cm, kind="bound")
                caption_text = (
                    f"{photo.get('filename', 'Photo')}  ·  "
                    f"{photo.get('location', '')}  ·  "
                    f"{photo.get('timestamp', '')[:16]}"
                )
                hazard_text = photo.get("hazard_details", "Hazard detected")
                story.append(img)
                story.append(Spacer(1, 4))
                story.append(Paragraph(caption_text, styles["subtitle"]))
                story.append(Paragraph(f"Finding: {hazard_text}", styles["critical"]))
                story.append(Spacer(1, 14))
            except Exception:
                story.append(Paragraph(
                    f"[Photo: {photo.get('filename', 'unknown')} — could not embed]",
                    styles["bullet"],
                ))

    # ── Signature block ───────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_GREY))
    story.append(Spacer(1, 12))
    date_str = datetime.now().strftime("%d %B %Y")
    sig_name = signature or project.get("inspector", "—")
    sig_date = signed_at or date_str
    sig_data = [
        ["Inspector", sig_name],
        ["Signed",    sig_date],
        ["Project",   project.get("name", "—")],
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * cm, 13 * cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (0, -1), BRAND_GREY),
        ("TEXTCOLOR",     (1, 0), (1, -1), BRAND_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE",     (0, 0), (-1, 0), 0.5, BRAND_BLUE),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This report was digitally signed via BOB Inspector. "
        "The typed name above constitutes the inspector's confirmation of findings.",
        styles["footer"],
    ))

    # ── Footer note ──────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_GREY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Generated by BOB v0.1 — PDAI Final Project | ESADE 2025 | "
        f"{datetime.now().strftime('%d %b %Y %H:%M')}",
        styles["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
