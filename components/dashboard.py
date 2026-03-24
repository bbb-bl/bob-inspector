"""
components/dashboard.py
Aymen — Day 2: Dashboard tab
Aymen — Day 3: Report generation
Aymen — Day 4: Download button
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
            if not st.session_state.get("checklist_items"):
                st.session_state.checklist_items = sample.get("checklist_items", [])
            if not st.session_state.get("photos"):
                st.session_state.photos = sample.get("photos", [])
            if not st.session_state.get("voice_notes"):
                st.session_state.voice_notes = sample.get("voice_notes", [])
        except FileNotFoundError:
            pass
        st.session_state.sample_inspection_loaded = True


STATUS_COLORS = {
    "In progress": "🔵",
    "Pending review": "🟡",
    "Complete": "🟢",
    "On hold": "🔴",
}


def render_report_section():
    """Day 3 & 4 — Report generation and download."""
    from utils.report import generate_report

    st.divider()
    st.markdown("### 📄 Generate Inspection Report")

    project = st.session_state.get("current_project")
    checklist_items = st.session_state.get("checklist_items", [])
    photos = st.session_state.get("photos", [])
    voice_notes = st.session_state.get("voice_notes", [])

    if not project:
        st.info("👆 Click 'Start inspection →' on a project above to select it first.")
        return

    st.caption(f"Generating report for: **{project['name']}**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Checklist items", len(checklist_items))
    col2.metric("Photos", len(photos))
    col3.metric("Voice notes", len(voice_notes))

    if st.button("🤖 Generate report with AI", type="primary"):
        with st.spinner("BOB is writing your report..."):
            try:
                report = generate_report(project, checklist_items, photos, voice_notes)
                st.session_state.generated_report = report
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
                return

    if st.session_state.get("generated_report"):
        st.success("✅ Report generated!")

        edited_report = st.text_area(
            "Report (you can edit before downloading)",
            value=st.session_state.generated_report,
            height=400,
        )
        st.session_state.generated_report = edited_report

        project_name = project.get("name", "inspection").replace(" ", "_")
        st.download_button(
            label="⬇️ Download report (.md)",
            data=st.session_state.generated_report,
            file_name=f"inspection_{project_name}.md",
            mime="text/markdown",
        )


def render_dashboard():
    """Main entry point — call this inside the Dashboard tab."""
    load_projects()
    load_sample_inspection()

    projects = st.session_state.get("projects", [])

    st.markdown("## 📊 Project Overview")

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

    render_report_section()

    # ── Photo Gallery + Search (Day 4) ───────────────────────────────────────
    st.divider()
    st.subheader(f"📸 Photo Gallery ({len(st.session_state.photos)} photos)")

    if st.session_state.photos:
        f1, f2, f3 = st.columns(3)
        with f1:
            project_ids = ["All"] + list({p.get("project_id", "demo") for p in st.session_state.photos})
            selected_project = st.selectbox("Project", project_ids)
        with f2:
            hazards_only = st.checkbox("⚠️ Hazards only")
        with f3:
            search_query = st.text_input("🔍 Search descriptions")

        filtered = st.session_state.photos
        if selected_project != "All":
            filtered = [p for p in filtered if p.get("project_id", "N/A") == selected_project]
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
                        if photo.get("image_bytes"):
                            st.image(photo["image_bytes"], use_column_width=True)
                        else:
                            st.caption("🖼️ No preview available")
                        if photo["hazard_flag"]:
                            st.error(f"⚠️ {photo.get('hazard_details', '')}")
                        st.markdown(f"**Description:** {photo.get('ai_description', '_Not yet analysed_')}")
                        st.caption(f"🗂 Project: `{photo.get('project_id', 'N/A')}`")
                        st.caption(f"📍 {photo.get('location', 'N/A')}  |  🕐 {photo.get('timestamp', '')[:16]}")
    else:
        st.info("No photos yet — upload from the Inspection tab.")