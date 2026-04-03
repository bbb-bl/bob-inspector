"""
components/dashboard.py
Aymen — Day 2: Dashboard tab
Aymen — Day 3: Report generation
Aymen — Day 4: Download button
"""

import json
import os
import uuid
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
            # Always load sample checklist — inspection.py loads from CSV first (Tab 1),
            # which would otherwise block the sample data from ever appearing.
            st.session_state.checklist_items = sample.get("checklist_items", [])
            if not st.session_state.get("photos"):
                st.session_state.photos = sample.get("photos", [])
            if not st.session_state.get("voice_notes"):
                st.session_state.voice_notes = sample.get("voice_notes", [])
        except FileNotFoundError:
            pass
        st.session_state.sample_inspection_loaded = True


def save_report_to_disk(project: dict, report_text: str) -> str:
    """Saves a generated report to data/projects_data/{id}/reports/ with a timestamp."""
    from datetime import datetime
    project_id = project.get("id", "unknown")
    reports_dir = os.path.join("data", "projects_data", project_id, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(reports_dir, f"report_{timestamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return path


def load_saved_reports(project: dict) -> list[tuple[str, str]]:
    """Returns [(filename, content), ...] sorted oldest→newest for a project."""
    project_id = project.get("id", "unknown")
    reports_dir = os.path.join("data", "projects_data", project_id, "reports")
    if not os.path.exists(reports_dir):
        return []
    result = []
    for fname in sorted(os.listdir(reports_dir)):
        if fname.endswith(".md"):
            with open(os.path.join(reports_dir, fname), "r", encoding="utf-8") as f:
                result.append((fname, f.read()))
    return result


def compare_reports_with_ai(current_report: str, previous_report: str, project: dict) -> str:
    """Generates a Weekly Progress Summary comparing two reports using the LLM."""
    from utils.llm_utils import generate_text
    prompt = (
        f"You are a construction safety inspector reviewing weekly progress "
        f"for project: {project.get('name', 'Unknown')}.\n\n"
        "Compare the two inspection reports below and write a concise "
        "**Weekly Progress Summary** (under 300 words) covering:\n"
        "1. Issues resolved since the previous report\n"
        "2. New findings that appeared\n"
        "3. Critical items still outstanding\n"
        "4. Overall progress assessment (Improving / Stable / Declining)\n\n"
        "--- PREVIOUS REPORT ---\n"
        f"{previous_report[:3000]}\n\n"
        "--- CURRENT REPORT ---\n"
        f"{current_report[:3000]}\n\n"
        "Weekly Progress Summary:\n"
    )
    return generate_text(prompt)


STATUS_COLORS = {
    "In progress": "🔵",
    "Pending review": "🟡",
    "Complete": "🟢",
    "On hold": "🔴",
}


def render_report_section():
    """Day 3, 4 & 5 — Report generation, markdown download, and PDF download."""
    from utils.report import generate_report
    from utils.report_pdf import build_pdf

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
                # Auto-save to project folder
                saved_path = save_report_to_disk(project, report)
                st.toast(f"Report saved to {saved_path}", icon="💾")
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

        dl_col1, dl_col2 = st.columns(2)

        with dl_col1:
            st.download_button(
                label="⬇️ Download PDF",
                data=build_pdf(st.session_state.generated_report, project),
                file_name=f"inspection_{project_name}.pdf",
                mime="application/pdf",
                type="primary",
            )

        with dl_col2:
            st.download_button(
                label="⬇️ Download Markdown",
                data=st.session_state.generated_report,
                file_name=f"inspection_{project_name}.md",
                mime="text/markdown",
            )

        # ── Weekly report comparison ─────────────────────────
        st.divider()
        st.markdown("#### 📅 Compare with previous report")
        saved_reports = load_saved_reports(project)
        # Need at least 2 saved reports to compare (current was just saved)
        if len(saved_reports) >= 2:
            report_names = [r[0] for r in saved_reports]
            selected_prev = st.selectbox(
                "Compare current report against:",
                options=report_names[:-1],          # All except the latest
                index=len(report_names) - 2,        # Default to the most recent previous
                format_func=lambda n: n.replace("report_", "").replace(".md", "").replace("_", " "),
            )
            if st.button("🔍 Generate Weekly Progress Summary", type="primary"):
                prev_content = next(c for n, c in saved_reports if n == selected_prev)
                with st.spinner("BOB is comparing reports..."):
                    try:
                        comparison = compare_reports_with_ai(
                            st.session_state.generated_report,
                            prev_content,
                            project,
                        )
                        st.session_state["weekly_comparison"] = comparison
                    except Exception as e:
                        st.error(f"Error generating comparison: {str(e)}")

            if st.session_state.get("weekly_comparison"):
                st.markdown("**Weekly Progress Summary**")
                st.markdown(st.session_state["weekly_comparison"])
                st.download_button(
                    "⬇️ Download summary",
                    data=st.session_state["weekly_comparison"],
                    file_name=f"weekly_summary_{project_name}.md",
                    mime="text/markdown",
                )
        else:
            st.caption("Generate at least two reports to enable comparison.")


def render_dashboard():
    """Main entry point — call this inside the Dashboard tab."""
    load_projects()
    load_sample_inspection()

    projects = st.session_state.get("projects", [])

    # ── Active project banner ────────────────────────────────
    active = st.session_state.get("current_project")
    if active:
        st.markdown(
            f"<div style='text-align:center; padding:10px 0 4px 0;'>"
            f"<span style='font-size:0.85rem; color:#aaa;'>Active project</span><br>"
            f"<span style='font-size:1.6rem; font-weight:700;'>{active['name']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

    st.markdown("## 📊 Project Overview")

    total_projects = len(projects)
    total_inspections = sum(p.get("total_inspections", 0) for p in projects)

    # Compute live from session_state so metrics update as the inspector works
    live_items = st.session_state.get("checklist_items", [])
    total_open = sum(1 for i in live_items if not i.get("checked"))
    total_critical = sum(1 for i in live_items if not i.get("checked") and i.get("severity") == "Critical")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Projects", total_projects)
    m2.metric("Open Findings", total_open)
    m3.metric("Critical", total_critical, delta=None if total_critical == 0 else f"{total_critical} urgent", delta_color="inverse")
    m4.metric("Total Inspections", total_inspections)

    st.divider()

    st.markdown(
        "<h3 style='text-align:center; font-size:1.5rem; margin-bottom:12px;'>🏗️ Projects</h3>",
        unsafe_allow_html=True,
    )
    # Add new project form
    with st.expander("➕ Add new project"):
        with st.form("new_project_form"):
            name = st.text_input("Project name *")
            address = st.text_input("Address *")
            building_type = st.selectbox("Building type *", ["Commercial", "Residential", "Educational"])
            inspector = st.text_input("Inspector name *")
            status = st.selectbox("Status *", ["In progress", "Pending review", "Complete"])

            submitted = st.form_submit_button("Create project")
            if submitted:
                if name and address and inspector:
                    new_project = {
                        "id": f"proj-{str(uuid.uuid4())[:6]}",
                        "name": name,
                        "address": address,
                        "building_type": building_type,
                        "status": status,
                        "inspector": inspector,
                        "last_inspection": "Not yet inspected",
                        "total_inspections": 0,
                        "open_findings": 0,
                        "critical_findings": 0,
                        "notes": ""
                    }
                    st.session_state.projects.append(new_project)

                    # Save to projects.json so it persists after restart
                    data_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "..", "data", "projects.json"
                    )
                    try:
                        with open(data_path, "w", encoding="utf-8") as f:
                            json.dump(st.session_state.projects, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        st.warning(f"Project created but could not save to disk: {e}")

                    # Auto-select new project and go to Inspection tab
                    st.session_state.current_project = new_project
                    st.session_state.active_tab = "Inspection"
                    st.success(f"✅ Project '{name}' created! Redirecting to inspection...")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")

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

            info_col1, info_col2, info_col3 = st.columns(3)
            info_col1.markdown(f"**Last inspection**  \n{project.get('last_inspection', '—')}")
            info_col2.markdown(f"**Open findings**  \n{project.get('open_findings', 0)}")
            info_col3.markdown(f"**Inspections**  \n{project.get('total_inspections', 0)}")

            is_active = bool(active and active.get("id") == project["id"])
            btn_label = "✅ Active project" if is_active else "Start inspection →"
            if st.button(
                btn_label,
                key=f"start_{project['id']}",
                type="primary" if not is_active else "secondary",
                use_container_width=True,
                disabled=is_active,
            ):
                st.session_state.current_project = project
                st.session_state.active_tab = "Inspection"
                st.rerun()

            if project.get("notes"):
                st.caption(f"💬 {project['notes']}")

            # Show checklist progress for this project
            if st.session_state.get("current_project") and st.session_state.get("current_project", {}).get("id") == project["id"]:
                items = st.session_state.get("checklist_items", [])
                if items:
                    checked = sum(1 for i in items if i.get("checked"))
                    total = len(items)
                    critical = sum(1 for i in items if i.get("severity") == "Critical" and not i.get("checked"))
                    st.progress(checked / total if total > 0 else 0)
                    st.caption(f"✅ {checked}/{total} items completed")
                    if critical > 0:
                        st.error(f"⚠ {critical} critical item(s) outstanding")
                    else:
                        st.success("No critical items outstanding")
                else:
                    st.caption("No checklist started yet")
    render_report_section()

    # ── Photo Gallery + Search (Day 4) ───────────────────────────────────────
    st.divider()

    # Load photos from ALL projects into session_state (once per project per session)
    from utils.storage import load_photos_from_supabase
    from PIL import Image
    import io as _io
    for proj in st.session_state.get("projects", []):
        gallery_key = f"gallery_loaded_{proj['id']}"
        if not st.session_state.get(gallery_key):
            saved = load_photos_from_supabase(proj["name"])
            existing_ids = [p["id"] for p in st.session_state.photos]
            for p in saved:
                if p["id"] not in existing_ids:
                    if p.get("image_bytes") and "image_pil" not in p:
                        try:
                            pil_img = Image.open(_io.BytesIO(p["image_bytes"]))
                            pil_img.load()
                            p["image_pil"] = pil_img
                        except Exception:
                            p["image_pil"] = None
                    st.session_state.photos.append(p)
            st.session_state[gallery_key] = True

    if st.session_state.photos:
        # Build lookup: project_id -> project name
        id_to_name = {p["id"]: p["name"] for p in st.session_state.get("projects", [])}

        f1, f2, f3 = st.columns(3)
        with f1:
            all_project_names = ["All"] + [p["name"] for p in st.session_state.get("projects", [])]
            active_project = st.session_state.get("current_project")
            active_name = active_project.get("name") if active_project else None
            default_idx = all_project_names.index(active_name) if active_name in all_project_names else 0
            selected_project = st.selectbox("Project", all_project_names, index=default_idx)
        with f2:
            hazards_only = st.checkbox("⚠️ Hazards only")
        with f3:
            search_query = st.text_input("🔍 Search descriptions")

        filtered = list(st.session_state.photos)
        if selected_project != "All":
            def matches_project(photo):
                pid = photo.get("project_id", "")
                if id_to_name.get(pid) == selected_project:
                    return True
                if pid == selected_project:
                    return True
                slug = selected_project.lower().replace(" ", "-").replace("/", "-")
                if pid == slug:
                    return True
                return False
            filtered = [p for p in filtered if matches_project(p)]
        if hazards_only:
            filtered = [p for p in filtered if p.get("hazard_flag")]
        if search_query:
            q = search_query.lower()
            filtered = [p for p in filtered if q in p.get("ai_description", "").lower()]

        # Update header count after filtering
        st.subheader(f"📸 Photo Gallery ({len(filtered)} photos)")

        if not filtered:
            st.info("No photos match the current filters.")
        else:
            grid = st.columns(3)
            for i, photo in enumerate(filtered):
                with grid[i % 3]:
                    with st.expander(photo["filename"], expanded=False):
                        if photo.get("image_pil") is not None:
                            st.image(photo["image_pil"], width=400)
                        elif photo.get("image_bytes"):
                            st.image(photo["image_bytes"], width=400)
                        else:
                            st.caption("🖼️ No preview available")
                        if photo.get("hazard_flag"):
                            st.error(f"⚠️ {photo.get('hazard_details', '')}")
                        st.markdown(f"**Description:** {photo.get('ai_description', '_Not yet analysed_')}")
                        _pname = id_to_name.get(photo.get("project_id", ""), photo.get("project_id", "N/A"))
                        st.caption(f"🗂 Project: `{_pname}`")
                        st.caption(f"📍 {photo.get('location', 'N/A')}  |  🕐 {photo.get('timestamp', '')[:16]}")
    else:
        st.info("No photos yet — upload from the Inspection tab.")