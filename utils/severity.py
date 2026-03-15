CRITICAL_KEYWORDS = [
    "missing", "blocked", "exposed", "broken", "unsafe", "fallen",
    "no guardrail", "no barrier", "unguarded", "fire", "electrical",
    "fall risk", "collapse", "hazard", "danger", "emergency",
    "unsecured", "open junction", "excavation", "unprotected"
]

MINOR_KEYWORDS = [
    "damaged", "worn", "incomplete", "unclear", "faded",
    "partially", "needs repair", "outdated", "missing label",
    "unlabelled", "no sign", "no record"
]

def classify_severity(text: str) -> str:
    """
    Classify a checklist item or note as Critical, Minor or Recommendation.
    Used both for pre-seeding items from the CSV and for re-classifying
    when an architect adds a custom item or voice note.
    """
    text_lower = text.lower()
    for kw in CRITICAL_KEYWORDS:
        if kw in text_lower:
            return "Critical"
    for kw in MINOR_KEYWORDS:
        if kw in text_lower:
            return "Minor"
    return "Recommendation"


def load_checklist_from_csv(csv_path: str, building_type: str) -> list:
    """
    Load checklist.csv, filter by building_type, and return a list of
    dicts matching Botond's session_state schema exactly:
    id, text, zone, building_type, checked, notes, severity
    The detail, category and regulation_ref columns are kept as extras
    for the dashboard detail view.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)
    filtered = df[
        (df["building_type"] == building_type) |
        (df["building_type"] == "All")
    ].copy()

    items = []
    for _, row in filtered.iterrows():
        items.append({
            "id": row["id"],
            "text": row["text"],
            "zone": row["zone"],
            "building_type": row["building_type"],
            "checked": False,
            "notes": "",
            "severity": row["severity_default"],
            # Extra fields for dashboard detail view
            "detail": row["detail"],
            "category": row["category"],
            "regulation_ref": row["regulation_ref"],
        })
    return items