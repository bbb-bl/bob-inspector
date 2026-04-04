"""
utils/report.py
Aymen — Day 3: Report generation
Builds the LLM prompt from inspection session_state and generates a formal report.
"""

from utils.llm_utils import generate_text
from datetime import datetime
import re


def _clean_report(text: str) -> str:
    """Strip markdown formatting so the text area shows clean plain text."""
    # Remove **bold** markers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove *italic* markers
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove ### heading markers but keep the text
    text = re.sub(r'^#{1,3}\s+', '', text, flags=re.MULTILINE)
    # Replace any remaining [placeholder] text
    text = re.sub(r'\[date\]', datetime.now().strftime('%d %B %Y'), text, flags=re.IGNORECASE)
    text = re.sub(r'\[Insert Date\]', datetime.now().strftime('%d %B %Y'), text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()


def build_report_prompt(project: dict, checklist_items: list, photos: list, voice_notes: list) -> str:
    """Assembles all inspection data into a structured prompt for the LLM."""

    checked       = [i for i in checklist_items if i.get("checked")]
    unchecked     = [i for i in checklist_items if not i.get("checked")]
    hazard_photos = [p for p in photos if p.get("hazard_flag")]

    checked_lines = "\n".join(
        f"  - [{i.get('severity','—')}] {i.get('text','')}"
        + (f" — Note: {i['notes']}" if i.get("notes") else "")
        for i in checked
    ) or "  None."

    unchecked_lines = "\n".join(
        f"  - [{i.get('severity','—')}] {i.get('text','')}"
        for i in unchecked
    ) or "  None."

    photo_lines = "\n".join(
        f"  Photo {idx+1}: {p.get('ai_description','No description')}"
        for idx, p in enumerate(hazard_photos)
    ) or "  No hazards detected in photos."

    note_lines = "\n".join(
        f"  [{n.get('timestamp','')}] {n.get('text','')}"
        for n in voice_notes
    ) or "  None recorded."

    critical_outstanding = len([
        i for i in unchecked if i.get("severity") == "Critical"
    ])

    today = datetime.now().strftime('%d %B %Y')

    prompt = f"""You are a professional construction safety inspector writing a formal inspection report.
Generate a complete inspection report based on the data below.

PROJECT: {project.get('name', 'Unknown')}
ADDRESS: {project.get('address', 'Unknown')}
BUILDING TYPE: {project.get('building_type', 'Unknown')}
INSPECTOR: {project.get('inspector', 'Unknown')}
INSPECTION DATE: {today}

CHECKLIST SUMMARY:
- Items completed: {len(checked)} of {len(checklist_items)}
- Critical items outstanding: {critical_outstanding}

COMPLETED ITEMS:
{checked_lines}

OUTSTANDING ITEMS:
{unchecked_lines}

PHOTO FINDINGS ({len(hazard_photos)} hazards detected):
{photo_lines}

VOICE NOTES:
{note_lines}

Write a formal inspection report with these 6 sections:
1. Executive Summary (2-3 sentences)
2. Critical Findings (if any — each with location and recommended action)
3. Completed Checks (brief list)
4. Outstanding Items (with priority order)
5. Recommendations
6. Next Steps

STRICT FORMATTING RULES:
- Do NOT use markdown. No ** bold **, no * italic *, no # headings.
- Use plain text only. Use dashes (-) for bullet points.
- Use the actual inspection date provided above. Never write [date] or [Insert Date].
- Use numbered sections (1. 2. 3. etc.) as plain text headings.
- Keep language formal and professional.
"""
    return prompt


def generate_report(project: dict, checklist_items: list, photos: list, voice_notes: list) -> str:
    """Full pipeline: build prompt → call LLM → clean → prepend header → return report text."""
    prompt = build_report_prompt(project, checklist_items, photos, voice_notes)
    raw = generate_text(prompt)
    body = _clean_report(raw)

    today = datetime.now().strftime('%d %B %Y')
    header = (
        f"INSPECTION REPORT\n"
        f"{'=' * 40}\n"
        f"Project:    {project.get('name', '—')}\n"
        f"Address:    {project.get('address', '—')}\n"
        f"Type:       {project.get('building_type', '—')}\n"
        f"Inspector:  {project.get('inspector', '—')}\n"
        f"Date:       {today}\n"
        f"{'=' * 40}\n\n"
    )
    return header + body
