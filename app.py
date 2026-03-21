"""
BOB — The Lily of Construction 🌸
AI Construction Safety Inspector
ESADE PDAI 2025

Entry point: streamlit run app.py
"""

import streamlit as st
import json
import os

# ── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="BOB",
    page_icon="🌸",
    layout="wide"
)

# ── Session State Schema ─────────────────────────────────────
# This is the shared data contract — everyone builds against these exact keys.
# Samreen's checklist, Eng's photos, and Aymen's report all read/write from here.
# DO NOT rename these keys without telling the whole team.

if "current_project" not in st.session_state:
    st.session_state.current_project = None  # dict of active project

if "projects" not in st.session_state:
    # Load from Aymen's fixtures if available, else empty list
    projects_path = os.path.join("data", "projects.json")
    if os.path.exists(projects_path):
        with open(projects_path, "r") as f:
            st.session_state.projects = json.load(f)
    else:
        st.session_state.projects = []

if "checklist_items" not in st.session_state:
    st.session_state.checklist_items = []
    # List of dicts with keys:
    # id, text, zone, building_type, checked, notes, severity

if "photos" not in st.session_state:
    st.session_state.photos = []
    # List of dicts with keys:
    # id, project_id, filename, timestamp, location, ai_description, hazard_flag

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    # List of {role, content} dicts for BOB

if "voice_notes" not in st.session_state:
    st.session_state.voice_notes = []

# Always reset recording state on startup
if "recording" not in st.session_state:
    st.session_state.recording = False
if "voice_transcription_index" not in st.session_state:
    st.session_state.voice_transcription_index = 0

# ── BOB Chat Logic ───────────────────────────────────────────
from openai import OpenAI

# Groq uses the OpenAI-compatible API, just with a different base URL
client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1",
)

def get_system_prompt():
    """
    Builds BOB's system prompt with live inspection data.
    This runs EVERY message because LLMs are stateless —
    it's the only way BOB knows what's happening right now.
    """

    # ── Static part: BOB's personality (same every time) ──
    static = (
        "You are BOB, a friendly and professional AI construction safety "
        "inspection assistant. You help architects document findings, "
        "track checklist progress, and generate inspection reports.\n\n"
        "RULES:\n"
        "- Be concise: 2-3 sentences for simple questions. Longer only "
        "for reports and summaries.\n"
        "- If asked something unrelated to construction safety (e.g. poems, "
        "recipes, sports), politely decline. Fire safety, electrical safety, "
        "PPE, scaffolding, hazardous materials — these are ALL part of your "
        "domain. Never refuse safety-related questions.\n"
        "- ALWAYS use the lookup_regulation tool when asked about regulations, "
        "rules, laws, or requirements. Never answer regulation questions from "
        "general knowledge — always look them up.\n"
        "- When drafting notes or findings, use formal inspection language "
        "with specific locations and recommended actions.\n"
        "- Respond in the same language the user writes in.\n"
        "- For greetings, be warm but brief — one sentence, then ask "
        "how you can help with their inspection.\n\n"
        "EXAMPLE INSPECTION NOTES (follow this format when drafting notes):\n\n"
        "User: Draft a note about a missing guardrail on floor 3\n"
        "BOB: **Safety Observation — Missing Guardrail**\n"
        "- Location: Floor 3, east wing\n"
        "- Finding: Guardrail absent on open edge above 2m drop. "
        "Non-compliant with RD 1627/1997 Annex IV Part C §3a.\n"
        "- Severity: Critical\n"
        "- Recommendation: Install temporary barrier immediately. "
        "Restrict access until permanent guardrail is fitted.\n"
        "- Action required: Site manager to confirm corrective action within 24 hours.\n\n"
        "User: Draft a note about expired fire extinguisher in basement\n"
        "BOB: **Safety Observation — Expired Fire Extinguisher**\n"
        "- Location: Basement, corridor B\n"
        "- Finding: Fire extinguisher inspection tag shows last service "
        "date 14 months ago. Non-compliant with CTE DB-SI.\n"
        "- Severity: Minor\n"
        "- Recommendation: Replace or re-service extinguisher before next "
        "inspection. Verify all other extinguishers on site.\n"
        "- Action required: Site safety officer to schedule service within 7 days."
    )

    # ── Dynamic part: rebuilt from session_state every message ──
    # Current project info
    project = st.session_state.current_project
    if project:
        project_info = (
            f"\n\nCurrent project: {project['name']}"
            f"\nAddress: {project['address']}"
            f"\nBuilding type: {project['building_type']}"
        )
    else:
        project_info = "\n\nNo project currently selected."

    # Checklist summary (not the full list — keep tokens low)
    items = st.session_state.checklist_items
    if items:
        checked = sum(1 for i in items if i.get("checked"))
        total = len(items)
        critical = [i for i in items if i.get("severity") == "Critical" and not i.get("checked")]
        checklist_info = (
            f"\n\nChecklist: {checked}/{total} items completed."
        )
        if critical:
            checklist_info += f"\nCritical items outstanding: {len(critical)}"
            for c in critical[:5]:  # Max 5 to save tokens
                checklist_info += f"\n  - {c.get('text', 'Unknown item')}"
    else:
        checklist_info = "\n\nNo checklist loaded yet."

    # Photo summary
    photos = st.session_state.photos
    if photos:
        hazards = [p for p in photos if p.get("hazard_flag")]
        photo_info = (
            f"\n\nPhotos uploaded: {len(photos)}."
            f"\nHazards detected: {len(hazards)}."
        )
        for h in hazards[:3]:  # Max 3 to save tokens
            photo_info += f"\n  - {h.get('ai_description', 'No description')}"
    else:
        photo_info = "\n\nNo photos uploaded yet."

    return static + project_info + checklist_info + photo_info

# ── BOB Tools (Category C: LLM decides which to call) ────────
def get_checklist_summary():
    """Returns checklist progress grouped by zone."""
    items = st.session_state.checklist_items
    if not items:
        return "No checklist loaded yet."

    checked = sum(1 for i in items if i.get("checked"))
    total = len(items)

    # Group by zone
    zones = {}
    for item in items:
        zone = item.get("zone", "Unknown")
        zones.setdefault(zone, {"checked": 0, "total": 0})
        zones[zone]["total"] += 1
        if item.get("checked"):
            zones[zone]["checked"] += 1

    result = f"Checklist: {checked}/{total} items completed.\n\nBy zone:\n"
    for zone, counts in zones.items():
        result += f"  {zone}: {counts['checked']}/{counts['total']}\n"

    # List unchecked items
    unchecked = [i for i in items if not i.get("checked")]
    if unchecked:
        result += f"\nUnchecked items ({len(unchecked)}):\n"
        for i in unchecked:
            result += f"  - [{i.get('severity', '?')}] {i.get('text', 'Unknown')}\n"

    return result


def get_photo_hazards():
    """Returns list of photos where hazards were detected."""
    photos = st.session_state.photos
    if not photos:
        return "No photos uploaded yet."

    hazards = [p for p in photos if p.get("hazard_flag")]
    if not hazards:
        return f"{len(photos)} photos uploaded. No hazards detected."

    result = f"{len(photos)} photos uploaded. {len(hazards)} hazard(s) detected:\n\n"
    for h in hazards:
        result += (
            f"  - {h.get('filename', 'Unknown')}: "
            f"{h.get('ai_description', 'No description')} "
            f"({h.get('hazard_details', '')})\n"
        )
    return result


def get_critical_findings():
    """Returns all critical unchecked items + hazard photos."""
    items = st.session_state.checklist_items
    photos = st.session_state.photos

    critical_items = [
        i for i in items
        if i.get("severity") == "Critical" and not i.get("checked")
    ]
    hazard_photos = [p for p in photos if p.get("hazard_flag")]

    if not critical_items and not hazard_photos:
        return "No critical findings at this time."

    result = ""
    if critical_items:
        result += f"Critical checklist items outstanding ({len(critical_items)}):\n"
        for i in critical_items:
            result += f"  - {i.get('text', 'Unknown')} (Zone: {i.get('zone', '?')})\n"

    if hazard_photos:
        result += f"\nPhoto hazards ({len(hazard_photos)}):\n"
        for p in hazard_photos:
            result += f"  - {p.get('filename', '?')}: {p.get('hazard_details', 'No details')}\n"

    return result

def lookup_regulation(query: str):
    """Mini-RAG: searches checklist data for regulation references matching the query."""
    import pandas as pd

    try:
        df = pd.read_csv("data/checklist.csv")
    except FileNotFoundError:
        return "No regulation data available."

# Search across text, category, and regulation_ref columns
# Split query into individual words and search for ANY match
    words = query.lower().split()
    mask = pd.Series([False] * len(df))
    for word in words:
        if len(word) < 3:  # Skip tiny words like "the", "is", "a"
            continue
        mask = mask | (
            df["text"].str.lower().str.contains(word, na=False) |
            df["category"].str.lower().str.contains(word, na=False) |
            df["regulation_ref"].str.lower().str.contains(word, na=False) |
            df["detail"].str.lower().str.contains(word, na=False)
        )
    matches = df[mask]

    if matches.empty:
        return f"No regulations found matching '{query}'."

    result = f"Found {len(matches)} regulation(s) matching '{query}':\n\n"
    for _, row in matches.iterrows():
        result += (
            f"  - {row['text']}\n"
            f"    Category: {row['category']}\n"
            f"    Regulation: {row['regulation_ref']}\n"
            f"    Severity: {row['severity_default']}\n"
            f"    Detail: {row['detail'][:100]}...\n\n"
        )
    return result

# ── Tool Definitions (sent to the LLM so it knows what's available) ──
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_checklist_summary",
            "description": "Get the current checklist progress including completion counts by zone and list of unchecked items. Use when the user asks about checklist status, progress, what's done, or what's remaining.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_photo_hazards",
            "description": "Get a list of all uploaded photos and any detected safety hazards. Use when the user asks about photos, hazards found in images, or site conditions captured on camera.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_critical_findings",
            "description": "Get all critical severity items that are still unchecked plus any hazard photos. Use when the user asks about critical issues, urgent problems, what needs immediate attention, or wants a summary of the most important findings.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_regulation",
            "description": "Search the safety regulation database for rules about a specific topic. Use when the user asks about regulations, rules, legal requirements, compliance, or what the law says about a specific safety topic like scaffolding, electrical, fire safety, PPE, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The safety topic to search for, e.g. 'scaffolding', 'electrical', 'fire safety', 'PPE'"
                    }
                },
                "required": ["query"],
            },
        },
    },
]

# Map tool names to actual functions
TOOL_FUNCTIONS = {
    "get_checklist_summary": get_checklist_summary,
    "get_photo_hazards": get_photo_hazards,
    "get_critical_findings": get_critical_findings,
    "lookup_regulation": lookup_regulation,
}

def get_bob_response(user_message):
    """
    Category C: Multi-call tool_use pattern.
    1. Send message + tool definitions to LLM
    2. If LLM wants to call a tool -> run the function -> send result back
    3. LLM responds with real data
    """

    # Build messages: system prompt + history + new message
    messages = []
    messages.append({"role": "system", "content": get_system_prompt()})

    for msg in st.session_state.chat_history:
        # Only include simple text messages (skip tool calls in history)
        if msg.get("role") in ["user", "assistant"] and isinstance(msg.get("content"), str):
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        # ── LLM Call #1: Send message WITH tool definitions ──
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1024,
            messages=messages,
            tools=TOOLS,           # <-- This is new: tells LLM what tools exist
            tool_choice="auto",    # <-- LLM decides whether to use a tool
            temperature=0.7,
        )

        assistant_message = response.choices[0].message

        # ── Check: did the LLM want to call a tool? ──
        if assistant_message.tool_calls:
            # LLM chose to call one or more tools
            # Add the assistant's tool call message to the conversation
            messages.append(assistant_message)

            # Execute each tool the LLM requested
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name

                # Look up and run the matching Python function
                if function_name in TOOL_FUNCTIONS:
                    import json as _json
                    try:
                        args = _json.loads(tool_call.function.arguments)
                    except (ValueError, TypeError):
                        args = {}
                    tool_result = TOOL_FUNCTIONS[function_name](**args)
                else:
                    tool_result = f"Unknown tool: {function_name}"


                # Add the tool result to the conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            # ── LLM Call #2: Now answer WITH the real data ──
            final_response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                max_tokens=1024,
                messages=messages,
                temperature=0.7,
            )
            return final_response.choices[0].message.content

        else:
            # LLM answered directly without needing a tool
            return assistant_message.content

    except Exception as e:
        return f"Sorry, BOB encountered an error: {str(e)}"
    
# ── App Header ───────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center; margin-bottom:0;'>🌸 BOB</h1>"
    "<p style='text-align:center; color:gray; margin-top:0;'>"
    "The Lily of Construction — AI Safety Inspector</p>",
    unsafe_allow_html=True,
)
st.divider()


# ── Tabs ─────────────────────────────────────────────────────
tab_inspection, tab_dashboard, tab_bob = st.tabs([
    "📋 Inspection",
    "📊 Dashboard",
    "🤖 BOB",
])

# ── Tab 1: Inspection ────────────────────────────────────────
with tab_inspection:
    from components.inspection import render
    render()
             
# ── Tab 2: Dashboard ─────────────────────────────────────────
with tab_dashboard:
    from components.dashboard import render_dashboard
    render_dashboard()

# ── Tab 3: BOB Chatbot ───────────────────────────────────────
with tab_bob:
    st.subheader("🤖 Ask BOB")
    st.caption("Your AI construction safety assistant")
    
    # Welcome message when chat is empty
    if not st.session_state.chat_history:
        st.info(
            "👋 I'm **BOB**, your construction safety assistant.\n\n"
            "Try asking me:\n"
            '- *"What\'s the status of my checklist?"*\n'
            '- *"Draft a note about a missing guardrail on floor 3"*\n'
            '- *"Summarize today\'s findings"*'
        )
    # Display all previous messages from chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input box at the bottom
    user_input = st.chat_input("Ask BOB about your inspection...")

    if user_input:
        # 1. Add user message to history
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        # 2. Get BOB's response
        with st.spinner("BOB is thinking..."):
            response = get_bob_response(user_input)

        # 3. Add BOB's response to history
        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )

        # 4. Rerun so the history loop above displays everything correctly
        st.rerun()


# ── Footer ───────────────────────────────────────────────────
st.divider()
st.caption("🌸 BOB v0.1 — PDAI Final Project | ESADE 2025")
