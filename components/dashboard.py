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


def save_flagged_items(project: dict, checklist_items: list):
    """Saves outstanding items as a JSON snapshot alongside the report for history tracking."""
    from datetime import datetime
    project_id = project.get("id", "unknown")
    reports_dir = os.path.join("data", "projects_data", project_id, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outstanding = [
        {"text": i["text"], "severity": i.get("severity", ""), "zone": i.get("zone", "")}
        for i in checklist_items if not i.get("checked")
    ]
    path = os.path.join(reports_dir, f"flagged_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(outstanding, f, indent=2, ensure_ascii=False)


def load_historical_flags(project: dict) -> dict:
    """Returns {item_text: times_flagged} across all previous flagged snapshots."""
    project_id = project.get("id", "unknown")
    reports_dir = os.path.join("data", "projects_data", project_id, "reports")
    if not os.path.exists(reports_dir):
        return {}
    counts = {}
    for fname in sorted(os.listdir(reports_dir)):
        if fname.startswith("flagged_") and fname.endswith(".json"):
            try:
                with open(os.path.join(reports_dir, fname), "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items:
                    text = item.get("text", "")
                    counts[text] = counts.get(text, 0) + 1
            except Exception:
                pass
    return counts


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


STATUS_PILLS = {
    "In progress":    ('<span style="background:rgba(59,130,246,0.12);color:#93c5fd;padding:3px 11px;'
                       'border-radius:20px;font-size:0.7rem;font-weight:700;letter-spacing:0.09em;'
                       'border:1px solid rgba(59,130,246,0.3);white-space:nowrap;">IN PROGRESS</span>'),
    "Pending review": ('<span style="background:rgba(245,158,11,0.12);color:#fbbf24;padding:3px 11px;'
                       'border-radius:20px;font-size:0.7rem;font-weight:700;letter-spacing:0.09em;'
                       'border:1px solid rgba(245,158,11,0.3);white-space:nowrap;">PENDING REVIEW</span>'),
    "Complete":       ('<span style="background:rgba(34,197,94,0.12);color:#4ade80;padding:3px 11px;'
                       'border-radius:20px;font-size:0.7rem;font-weight:700;letter-spacing:0.09em;'
                       'border:1px solid rgba(34,197,94,0.3);white-space:nowrap;">COMPLETE</span>'),
    "On hold":        ('<span style="background:rgba(239,68,68,0.12);color:#f87171;padding:3px 11px;'
                       'border-radius:20px;font-size:0.7rem;font-weight:700;letter-spacing:0.09em;'
                       'border:1px solid rgba(239,68,68,0.3);white-space:nowrap;">ON HOLD</span>'),
}
STATUS_ACCENT = {
    "In progress": "#3B82F6",
    "Pending review": "#F59E0B",
    "Complete": "#22C55E",
    "On hold": "#EF4444",
}


def render_report_section():
    """Day 3, 4 & 5 — Report generation, markdown download, and PDF download."""
    from utils.report import generate_report
    from utils.report_pdf import build_pdf

    st.divider()
    st.markdown(
        '<div style="margin-bottom:16px;">'
        '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">AI-Powered</div>'
        '<div style="font-size:1.3rem;font-weight:800;letter-spacing:0.02em;">Inspection Report</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    project = st.session_state.get("current_project")
    checklist_items = st.session_state.get("checklist_items", [])
    photos = st.session_state.get("photos", [])
    voice_notes = st.session_state.get("voice_notes", [])

    if not project:
        st.info("→ Click 'Start inspection →' on a project above to select it first.")
        return

    st.caption(f"Generating report for: **{project['name']}**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Checklist items", len(checklist_items))
    col2.metric("Photos", len(photos))
    col3.metric("Voice notes", len(voice_notes))

    btn_col, status_col = st.columns([2, 3])
    with btn_col:
        if st.button("Generate report with AI", type="primary", use_container_width=True):
            with st.spinner("BOB is writing your report..."):
                try:
                    from datetime import datetime as _dt
                    report = generate_report(project, checklist_items, photos, voice_notes)
                    st.session_state.generated_report = report
                    saved_path = save_report_to_disk(project, report)
                    save_flagged_items(project, checklist_items)
                    st.session_state["report_last_saved"] = _dt.now().strftime("%H:%M")
                    st.session_state["report_saved_path"] = saved_path
                    st.session_state["historical_flags"] = load_historical_flags(project)
                    st.toast(f"Report saved to {saved_path}")
                except Exception as e:
                    st.error(f"Error generating report: {str(e)}")
                    return
    with status_col:
        if st.session_state.get("report_last_saved"):
            st.markdown(
                f'<div style="padding-top:8px;font-size:0.8rem;color:#4ade80;">'
                f'● Last saved at {st.session_state["report_last_saved"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

    if st.session_state.get("generated_report"):
        st.success("Report generated!")

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
                data=build_pdf(
                    st.session_state.generated_report,
                    project,
                    photos=st.session_state.get("photos", []),
                    signature=st.session_state.get("inspection_signature"),
                    signed_at=st.session_state.get("inspection_signed_at"),
                ),
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
        st.markdown("#### Compare with previous report")
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
            if st.button("Generate Weekly Progress Summary", type="primary"):
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

    active = st.session_state.get("current_project")

    st.markdown(
        '<div style="text-align:center;margin-bottom:16px;">'
        '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">Overview</div>'
        '<div style="font-size:1.4rem;font-weight:800;letter-spacing:0.04em;">Projects</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    # Add new project form
    if "project_created" not in st.session_state:
        st.session_state.project_created = False
    if "show_project_form" not in st.session_state:
        st.session_state.show_project_form = False

    if st.session_state.project_created:
        st.success("Project created successfully! Scroll down to find it in the Projects list.")
        st.session_state.project_created = False

    with st.expander("+ Add New Project — Click to expand", expanded=st.session_state.show_project_form):
        with st.form("new_project_form", clear_on_submit=True):
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
                    st.session_state.project_created = True
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")

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
                    st.success(f"Project '{name}' created! Redirecting to inspection...")
                    st.rerun()

        if not projects:
            st.info("No projects loaded. Check that data/projects.json exists.")
            return

    for project in projects:
        status_pill = STATUS_PILLS.get(project.get("status", ""),
            '<span style="background:rgba(107,114,128,0.12);color:#9ca3af;padding:3px 11px;'
            'border-radius:20px;font-size:0.7rem;font-weight:700;letter-spacing:0.09em;'
            'border:1px solid rgba(107,114,128,0.3);">UNKNOWN</span>')
        accent_color = STATUS_ACCENT.get(project.get("status", ""), "#6B7280")
        critical_count = project.get("critical_findings", 0)

        with st.container(border=True):
            # Colored top accent bar
            st.markdown(
                f'<div style="height:3px;background:{accent_color};border-radius:2px;'
                f'margin:-4px -4px 14px -4px;opacity:0.85;"></div>',
                unsafe_allow_html=True,
            )

            header_col, badge_col = st.columns([3, 1])

            with header_col:
                st.markdown(f"### {project['name']}")
                st.markdown(
                    f'<p style="color:#6B7280;font-size:0.78rem;margin:-6px 0 8px;">'
                    f'{project["address"]}  ·  {project["building_type"]}</p>',
                    unsafe_allow_html=True,
                )

            with badge_col:
                st.markdown(
                    f'<div style="text-align:right;padding-top:4px;">{status_pill}</div>',
                    unsafe_allow_html=True,
                )
                if critical_count > 0:
                    st.markdown(
                        f'<div style="text-align:right;margin-top:6px;">'
                        f'<span style="background:rgba(239,68,68,0.12);color:#f87171;'
                        f'padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;'
                        f'border:1px solid rgba(239,68,68,0.3);">△ {critical_count} CRITICAL</span></div>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div style="height:1px;background:rgba(255,255,255,0.06);margin:4px 0 12px;"></div>',
                        unsafe_allow_html=True)

            info_col1, info_col2, info_col3 = st.columns(3)
            info_col1.markdown(
                f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Last Inspection</div>'
                f'<div style="font-size:0.88rem;font-weight:500;margin-top:2px;">{project.get("last_inspection", "—")}</div>',
                unsafe_allow_html=True)
            info_col2.markdown(
                f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Open Findings</div>'
                f'<div style="font-size:0.88rem;font-weight:500;margin-top:2px;">{project.get("open_findings", 0)}</div>',
                unsafe_allow_html=True)
            info_col3.markdown(
                f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Inspections</div>'
                f'<div style="font-size:0.88rem;font-weight:500;margin-top:2px;">{project.get("total_inspections", 0)}</div>',
                unsafe_allow_html=True)

            is_active = bool(active and active.get("id") == project["id"])
            btn_label = "✓ Active project" if is_active else "Start inspection →"
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

            confirm_key = f"confirm_del_proj_{project['id']}"
            if not st.session_state.get(confirm_key):
                if st.button("✕ Delete project", key=f"delete_{project['id']}"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                st.warning("This will permanently delete the project. Are you sure?")
                cy, cn = st.columns(2)
                with cy:
                    if st.button("Yes, delete", key=f"del_proj_yes_{project['id']}", type="primary"):
                        st.session_state.projects = [
                            p for p in st.session_state.projects
                            if p["id"] != project["id"]
                        ]
                        if st.session_state.get("current_project", {}).get("id") == project["id"]:
                            st.session_state.current_project = None
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with cn:
                    if st.button("Cancel", key=f"del_proj_no_{project['id']}"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()

            if project.get("notes"):
                st.caption(project['notes'])

            # Project inspection brief
            insp_date = project.get('last_inspection', 'Not yet inspected')
            open_f = project.get('open_findings', 0)
            crit_f = project.get('critical_findings', 0)
            n_insp = project.get('total_inspections', 0)
            brief_color = "#DC2626" if crit_f > 0 else "#16A34A"
            crit_label = f"△ {crit_f} critical unresolved" if crit_f > 0 else "✓ No critical items"
            st.markdown(f"""
            <div style="background:#F8FAFC;border-radius:8px;padding:10px 14px;
                        margin-top:8px;border-left:4px solid {brief_color};font-size:0.82rem;color:#475569">
                Last inspected: <b>{insp_date}</b> &nbsp;·&nbsp;
                {open_f} open finding(s) &nbsp;·&nbsp;
                {n_insp} inspection(s) conducted &nbsp;·&nbsp;
                <span style="color:{brief_color};font-weight:600">{crit_label}</span>
            </div>
            """, unsafe_allow_html=True)

            # Show active inspection details inside the card
            if st.session_state.get("current_project") and st.session_state.get("current_project", {}).get("id") == project["id"]:
                items = st.session_state.get("checklist_items", [])
                if items:
                    checked = sum(1 for i in items if i.get("checked"))
                    total = len(items)
                    critical = sum(1 for i in items if i.get("severity") == "Critical" and not i.get("checked"))
                    pct = int(checked / total * 100) if total else 0
                    status_text = f"△ {critical} critical item(s) outstanding" if critical > 0 else "✓ No critical items"
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg,#1D4ED8,#1565C0);
                                border-radius:10px;padding:14px 18px;margin-top:10px;
                                box-shadow:0 4px 12px rgba(29,78,216,0.2)">
                        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                            <div>
                                <div style="color:rgba(255,255,255,0.75);font-size:0.68rem;font-weight:700;
                                            text-transform:uppercase;letter-spacing:0.1em;margin-bottom:2px">
                                    Active Inspection
                                </div>
                                <div style="color:white;font-size:0.82rem;font-weight:600">{status_text}</div>
                            </div>
                            <div style="text-align:right">
                                <div style="color:white;font-size:1.8rem;font-weight:800;line-height:1">{pct}%</div>
                                <div style="color:rgba(255,255,255,0.7);font-size:0.68rem;font-weight:600;
                                            text-transform:uppercase;letter-spacing:0.08em">Compliance</div>
                            </div>
                        </div>
                        <div style="margin-top:10px;background:rgba(255,255,255,0.2);border-radius:4px;height:5px">
                            <div style="background:white;border-radius:4px;height:5px;width:{pct}%"></div>
                        </div>
                        <div style="color:rgba(255,255,255,0.65);font-size:0.7rem;margin-top:4px">
                            {checked}/{total} checklist items complete
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
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
            try:
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
            except Exception:
                pass  # Network blip — silently skip, will retry next session
            finally:
                st.session_state[gallery_key] = True  # Always mark done to avoid infinite retry

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
            hazards_only = st.checkbox("Hazards only")
        with f3:
            search_query = st.text_input("Search descriptions")

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
        st.markdown(
            f'<div style="margin-bottom:12px;">'
            f'<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">Documentation</div>'
            f'<div style="font-size:1.3rem;font-weight:800;letter-spacing:0.02em;">Photo Gallery <span style="font-size:0.9rem;color:#6B7280;font-weight:400;">({len(filtered)} photos)</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not filtered:
            st.markdown("""
            <div style="border:2px dashed rgba(255,255,255,0.1);border-radius:12px;
                        padding:40px;text-align:center;color:#4B5563;margin:16px 0;">
                <div style="font-size:1.4rem;margin-bottom:8px;opacity:0.4;">▣</div>
                <div style="font-weight:600;font-size:0.9rem;margin-bottom:4px;color:#6B7280;">No photos match the current filters</div>
                <div style="font-size:0.8rem;color:#4B5563;">Try adjusting your filter criteria</div>
            </div>""", unsafe_allow_html=True)
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
                            st.caption("No preview available")
                        if photo.get("hazard_flag"):
                            st.error(f"△ {photo.get('hazard_details', '')}")
                        st.markdown(f"**Description:** {photo.get('ai_description', '_Not yet analysed_')}")
                        _pname = id_to_name.get(photo.get("project_id", ""), photo.get("project_id", "N/A"))
                        st.caption(f"Project: {_pname}")
                        st.caption(f"{photo.get('location', 'N/A')}  ·  {photo.get('timestamp', '')[:16]}")
    else:
        st.markdown("""
        <div style="border:2px dashed rgba(255,255,255,0.1);border-radius:12px;
                    padding:48px;text-align:center;color:#4B5563;margin:16px 0;">
            <div style="font-size:1.6rem;margin-bottom:10px;opacity:0.3;">▣</div>
            <div style="font-weight:700;font-size:0.95rem;margin-bottom:6px;color:#6B7280;">No photos yet</div>
            <div style="font-size:0.82rem;color:#4B5563;">Upload site photos from the Inspection tab</div>
        </div>""", unsafe_allow_html=True)