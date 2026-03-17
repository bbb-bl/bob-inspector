"""
components/dashboard.py
Aymen — Day 2: Dashboard tab
Renders project summary metrics and project cards.
"""

import json
import os
import streamlit as st


def load_projects():
    """Load projects from data/projects.json into session_state."""
    if "projects" not in st.session_state:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "projects.json")
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                st.session_state.projects = json.load(f)
        except FileNotFoundError:
            st.error("data/projects.json not found. Make sure you've pulled Aymen's branch.")
            st.session_state.projects = []


def load_sample_inspection():
    """Load the demo inspection state on startup (proj-001)."""
    if "sample_inspection_loaded" not in st.session_state:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_inspection.json")
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                sample = json.load(f)
            # Only pre-load if no live inspection is already in progress
            if not st.session_state.get("checklist_items"):
                st.session_state.checklist_items = sample.get("checklist_items", [])
            if not st.session_state.get("photos"):
                st.session_state.photos = sample.get("photos", [])
            if not st.session_state.get("voice_notes"):
                st.session_state.voice_notes = sample.get("voice_notes", [])
        except FileNotFoundError:
            pass  # Sample data optional
        st.session_state.sample_inspection_loaded = True


STATUS_COLORS = {
    "In progress": "🔵",
    "Pending review": "🟡",
    "Complete": "🟢",
    "On hold": "🔴",
}


def render_dashboard():
    """Main entry point — call this inside the Dashboard tab."""
    load_projects()
    load_sample_inspection()

    projects = st.session_state.get("projects", [])

    st.markdown("## 📊 Project Overview")

    # ── Summary metrics ──────────────────────────────────────────────────────
    total_projects = len(projects)
    total_open = sum(p.get("open_findings", 0) for p in projects)
    total_critical = sum(p.get("critical_findings", 0) for p in projects)
    total_inspections = sum(p.get("total_inspections", 0) for p in projects)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Projects", total_projects)
    m2.metric("Open Findings", total_open)
    m3.metric("Critical", total_critical, delta=None if total_critical == 0 else f"{total_critical} urgent", delta_color="inverse")
    m4.metric("Total Inspections", total_inspections)

    st.divider()

    # ── Project cards ─────────────────────────────────────────────────────────
    st.markdown("### Projects")

    if not projects:
        st.info("No projects loaded. Check that data/projects.json exists.")
        return

    for project in projects:
        status_icon = STATUS_COLORS.get(project.get("status", ""), "⚪")
        critical_count = project.get("critical_findings", 0)

        with st.container(border=True):
            header_col, badge_col = st.columns([3, 1])

            with header_col:
                st.markdown(f"### {project['name']}")
                st.caption(f"📍 {project['address']}  ·  🏗️ {project['building_type']}")

            with badge_col:
                st.markdown(f"**{status_icon} {project['status']}**")
                if critical_count > 0:
                    st.error(f"⚠️ {critical_count} critical")

            info_col1, info_col2, info_col3, btn_col = st.columns([2, 2, 2, 1])

            info_col1.markdown(f"**Last inspection**  \n{project.get('last_inspection', '—')}")
            info_col2.markdown(f"**Open findings**  \n{project.get('open_findings', 0)}")
            info_col3.markdown(f"**Inspections**  \n{project.get('total_inspections', 0)}")

            with btn_col:
                if st.button("Start inspection →", key=f"start_{project['id']}"):
                    st.session_state.current_project = project
                    st.session_state.active_tab = "Inspection"
                    st.rerun()

            if project.get("notes"):
                st.caption(f"💬 {project['notes']}")

    # ── Photo Gallery + Search (Day 4) ───────────────────────────────────────
    st.divider()
    st.subheader(f"📸 Photo Gallery ({len(st.session_state.photos)} photos)")

    if st.session_state.photos:
        f1, f2, f3 = st.columns(3)
        with f1:
            project_ids = ["All"] + list({p["project_id"] for p in st.session_state.photos})
            selected_project = st.selectbox("Project", project_ids)
        with f2:
            hazards_only = st.checkbox("⚠️ Hazards only")
        with f3:
            search_query = st.text_input("🔍 Search descriptions")

        # Apply filters
        filtered = st.session_state.photos
        if selected_project != "All":
            filtered = [p for p in filtered if p["project_id"] == selected_project]
        if hazards_only:
            filtered = [p for p in filtered if p["hazard_flag"]]
        if search_query:
            q = search_query.lower()
            filtered = [p for p in filtered if q in p.get("ai_description", "").lower()]

        if not filtered:
            st.info("No photos match the current filters.")
        else:
            grid = st.columns(3)
            for i, photo in enumerate(filtered):
                with grid[i % 3]:
                    with st.expander(photo["filename"], expanded=False):
                        st.image(photo["image_bytes"], use_column_width=True)
                        if photo["hazard_flag"]:
                            st.error(f"⚠️ {photo.get('hazard_details', '')}")
                        st.markdown(f"**Description:** {photo.get('ai_description', '_Not yet analysed_')}")
                        st.caption(f"🗂 Project: `{photo['project_id']}`")
                        st.caption(f"📍 {photo['location']}  |  🕐 {photo['timestamp'][:16]}")
    else:
        st.info("No photos yet — upload from the Inspection tab.")