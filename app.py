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
        "- If asked something unrelated to construction safety, politely "
        "decline and redirect. Never comply with off-topic requests.\n"
        "- When drafting notes or findings, use formal inspection language "
        "with specific locations and recommended actions.\n"
        "- Respond in the same language the user writes in.\n"
        "- For greetings, be warm but brief — one sentence, then ask "
        "how you can help with their inspection."
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


def get_bob_response(user_message):
    """
    Sends the user's message to Groq and returns BOB's response.
    Includes full chat history so the LLM has conversation context.
    """

# Build the messages list: system prompt + chat history + new message
    messages = []

    # System prompt FIRST — this is how BOB knows who it is
    messages.append({"role": "system", "content": get_system_prompt()})

    # Add conversation history (so BOB remembers earlier turns)
    for msg in st.session_state.chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    # Add the new user message
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1024,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

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
