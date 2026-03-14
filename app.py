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
    # List of {timestamp, text} dicts


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
    st.subheader("📋 On-Site Inspection")
    st.write("Coming soon — Samreen's checklist + Eng's photo upload go here.")

# ── Tab 2: Dashboard ─────────────────────────────────────────
with tab_dashboard:
    st.subheader("📊 Dashboard")
    st.write("Coming soon — Aymen's project cards + report generation go here.")

# ── Tab 3: BOB Chatbot ───────────────────────────────────────
with tab_bob:
    st.subheader("🤖 Ask BOB")
    st.write("Coming soon — Botond's chatbot goes here.")


# ── Footer ───────────────────────────────────────────────────
st.divider()
st.caption("🌸 BOB v0.1 — PDAI Final Project | ESADE 2025")
