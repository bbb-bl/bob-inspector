"""
components/dashboard.py
Aymen — Day 2: Dashboard tab
Aymen — Day 3: Report generation
Aymen — Day 4: Download button
Aymen — Day 5: PDF export + charts + professional UI
"""

import json
import os
import uuid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st

PINK  = "#C02050"
DARK  = "#1A1A2E"
BLUE  = "#2855C8"
GREEN = "#2D9E5F"
RED   = "#E63946"
AMBER = "#E8940A"
GREY  = "#6C757D"
LIGHT = "#F7D6E0"


def inject_css():
    st.markdown("""
    <style>
    html, body, [class*="css"] { font-family: 'Inter','Segoe UI',sans-serif; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    [data-testid="metric-container"] {
        background: white;
        border: 1px solid #F0E0E8;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    [data-testid="metric-container"] label {
        color: #6C757D !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #1A1A2E !important;
    }
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1A1A2E;
        padding: 0.4rem 0.75rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #C02050;
    }
    .badge-progress { background:#EFF6FF;color:#2855C8;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600; }
    .badge-pending  { background:#FFFBEB;color:#E8940A;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600; }
    .badge-complete { background:#F0FDF4;color:#2D9E5F;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600; }
    .badge-critical { background:#FEF2F2;color:#E63946;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600; }
    .stButton > button[kind="primary"] {
        background: #C02050 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def _donut_chart(checked, total):
    if total == 0:
        return
    pct = int(checked / total * 100)
    fig, ax = plt.subplots(figsize=(3, 3), facecolor="none")
    ax.pie([checked, total - checked], colors=[PINK, "#F0E0E8"], startangle=90,
           wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 2})
    ax.text(0, 0.05, f"{pct}%", ha="center", va="center",
            fontsize=18, fontweight="bold", color=DARK)
    ax.text(0, -0.25, "complete", ha="center", va="center", fontsize=8, color=GREY)
    ax.set_aspect("equal")
    fig.patch.set_alpha(0)
    plt.tight_layout(pad=0.1)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def _severity_bar(items):
    sevs   = ["Critical", "High", "Minor", "Recommendation"]
    colors = {"Critical": RED, "High": AMBER, "Minor": GREY, "Recommendation": GREEN}
    done = {s: 0 for s in sevs}
    todo = {s: 0 for s in sevs}
    for item in items:
        s = item.get("severity", "Recommendation")
        if s not in sevs:
            s = "Recommendation"
        if item.get("checked"):
            done[s] += 1
        else:
            todo[s] += 1
    active = [s for s in sevs if done[s] + todo[s] > 0]
    if not active:
        return
    fig, ax = plt.subplots(figsize=(4.5, max(1.8, len(active) * 0.65)), facecolor="none")
    for i, s in enumerate(active):
        total_s = done[s] + todo[s]
        ax.barh(i, total_s, color="#F0E0E8", height=0.5)
        ax.barh(i, done[s], color=colors[s], height=0.5)
        ax.text(total_s + 0.05, i, f"{done[s]}/{total_s}", va="center", fontsize=8, color=DARK)
    ax.set_yticks(range(len(active)))
    ax.set_yticklabels(active, fontsize=9, color=DARK)
    ax.set_xlim(0, max(done[s] + todo[s] for s in active) + 1.8)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, colors=GREY)
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)
    plt.tight_layout(pad=0.3)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _zone_heatmap(items):
    zones = {}
    for item in items:
        z = item.get("zone", "General")
        zones.setdefault(z, {"done": 0, "total": 0})
        zones[z]["total"] += 1
        if item.get("checked"):
            zones[z]["done"] += 1
    if not zones:
        return
    labels = list(zones.keys())
    pcts   = [zones[z]["done"] / zones[z]["total"] * 100 for z in labels]
    bcolors = [RED if p < 40 else AMBER if p < 70 else GREEN for p in pcts]
    fig, ax = plt.subplots(figsize=(4.5, max(1.5, len(labels) * 0.55)), facecolor="none")
    bars = ax.barh(labels, pcts, color=bcolors, height=0.5)
    for bar, pct in zip(bars, pcts):
        ax.text(min(pct + 1, 96), bar.get_y() + bar.get_height() / 2,
                f"{pct:.0f}%", va="center", fontsize=8, color=DARK)
    ax.set_xlim(0, 115)
    ax.set_xlabel("% Complete", fontsize=8, color=GREY)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, colors=GREY)
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)
    legend = [mpatches.Patch(color=RED, label="<40%"),
              mpatches.Patch(color=AMBER, label="40-70%"),
              mpatches.Patch(color=GREEN, label=">70%")]
    ax.legend(handles=legend, fontsize=7, loc="lower right", frameon=False)
    plt.tight_layout(pad=0.3)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _hazard_pie(photos):
    hazards = sum(1 for p in photos if p.get("hazard_flag"))
    safe = len(photos) - hazards
    if not photos:
        return
    fig, ax = plt.subplots(figsize=(2.8, 2.8), facecolor="none")
    ax.pie([hazards, safe], colors=[RED, GREEN], startangle=90,
           labels=[f"Hazard\n{hazards}", f"Safe\n{safe}"],
           textprops={"fontsize": 9, "color": DARK},
           wedgeprops={"edgecolor": "white", "linewidth": 2})
    ax.set_aspect("equal")
    fig.patch.set_alpha(0)
    plt.tight_layout(pad=0.1)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def render_analytics(items, photos):
    if not items and not photos:
        return
    st.markdown('<div class="section-header">📊 Live Analytics</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.1, 2, 2])
    with c1:
        st.caption("**Completion**")
        checked = sum(1 for i in items if i.get("checked"))
        _donut_chart(checked, len(items))
    with c2:
        st.caption("**By severity**")
        _severity_bar(items)
    with c3:
        st.caption("**By zone**")
        _zone_heatmap(items)

    if photos and any(p.get("ai_description") for p in photos):
        st.divider()
        ph1, ph2 = st.columns([1, 2.5])
        with ph1:
            st.caption("**Photo hazards**")
            _hazard_pie(photos)
        with ph2:
            st.caption("**Hazard details**")
            for p in [p for p in photos if p.get("hazard_flag")]:
                st.markdown(
                    f"<div style='background:#FEF2F2;border-left:3px solid {RED};"
                    f"border-radius:6px;padding:8px 12px;margin-bottom:6px;font-size:0.85rem'>"
                    f"⚠️ <b>{p.get('filename','')}</b><br>{p.get('hazard_details','')}</div>",
                    unsafe_allow_html=True
                )


def load_projects():
    if "projects" not in st.session_state:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "projects.json")
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                st.session_state.projects = json.load(f)
        except FileNotFoundError:
            st.error("data/projects.json not found.")
            st.session_state.projects = []


def load_sample_inspection():
    if "sample_inspection_loaded" not in st.session_state:
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_inspection.json")
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                sample = json.load(f)
            st.session_state.checklist_items = sample.get("checklist_items", [])
            if not st.session_state.get("photos"):
                st.session_state.photos = sample.get("photos", [])
            if not st.session_state.get("voice_notes"):
                st.session_state.voice_notes = sample.get("voice_notes", [])
        except FileNotFoundError:
            pass
        st.session_state.sample_inspection_loaded = True


STATUS_COLORS = {"In progress": "🔵", "Pending review": "🟡", "Complete": "🟢", "On hold": "🔴"}
STATUS_BADGE  = {"In progress": "badge-progress", "Pending review": "badge-pending",
                 "Complete": "badge-complete"}


def render_report_section():
    from utils.report import generate_report
    from utils.report_pdf import build_pdf

    st.markdown('<div class="section-header">📄 Generate Inspection Report</div>',
                unsafe_allow_html=True)

    project         = st.session_state.get("current_project")
    checklist_items = st.session_state.get("checklist_items", [])
    photos          = st.session_state.get("photos", [])
    voice_notes     = st.session_state.get("voice_notes", [])

    if not project:
        st.info("👆 Select a project above and click 'Start →' first.")
        return

    st.markdown(
        f"<div style='background:#F7D6E0;border-radius:8px;padding:10px 16px;"
        f"margin-bottom:12px;font-size:0.9rem;color:{DARK}'>"
        f"📋 <b>{project['name']}</b> · {project.get('address','')} · "
        f"Inspector: {project.get('inspector','—')}</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Checklist items", len(checklist_items),
              delta=f"{sum(1 for i in checklist_items if i.get('checked'))} done")
    c2.metric("Photos", len(photos),
              delta=f"{sum(1 for p in photos if p.get('hazard_flag'))} hazards")
    c3.metric("Voice notes", len(voice_notes))

    if st.button("🤖 Generate report with AI", type="primary", use_container_width=True):
        with st.spinner("BOB is writing your report..."):
            try:
                report = generate_report(project, checklist_items, photos, voice_notes)
                st.session_state.generated_report = report
            except Exception as e:
                st.error(f"Error: {str(e)}")
                return

    if st.session_state.get("generated_report"):
        st.success("✅ Report ready — review and download below.")
        edited = st.text_area("Report (editable before download)",
                              value=st.session_state.generated_report, height=380)
        st.session_state.generated_report = edited
        project_name = project.get("name", "inspection").replace(" ", "_")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download PDF",
                               data=build_pdf(st.session_state.generated_report, project),
                               file_name=f"inspection_{project_name}.pdf",
                               mime="application/pdf", type="primary",
                               use_container_width=True)
        with d2:
            st.download_button("⬇️ Download Markdown",
                               data=st.session_state.generated_report,
                               file_name=f"inspection_{project_name}.md",
                               mime="text/markdown", use_container_width=True)


def render_dashboard():
    inject_css()
    load_projects()
    load_sample_inspection()

    projects   = st.session_state.get("projects", [])
    live_items = st.session_state.get("checklist_items", [])
    photos     = st.session_state.get("photos", [])

    total_open     = sum(1 for i in live_items if not i.get("checked"))
    total_critical = sum(1 for i in live_items
                         if not i.get("checked") and i.get("severity") == "Critical")
    total_inspections = sum(p.get("total_inspections", 0) for p in projects)

    st.markdown('<div class="section-header">📊 Project Overview</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Projects",          len(projects))
    m2.metric("Open Findings",     total_open)
    m3.metric("Critical",          total_critical,
              delta=f"{total_critical} urgent" if total_critical else None,
              delta_color="inverse")
    m4.metric("Total Inspections", total_inspections)

    st.divider()
    render_analytics(live_items, photos)
    st.divider()

    st.markdown('<div class="section-header">🏗️ Projects</div>', unsafe_allow_html=True)

    with st.expander("➕ Add new project"):
        with st.form("new_project_form"):
            name  = st.text_input("Project name *")
            addr  = st.text_input("Address *")
            btype = st.selectbox("Building type", ["Commercial", "Residential", "Educational"])
            insp  = st.text_input("Inspector name *")
            stat  = st.selectbox("Status", ["In progress", "Pending review", "Complete"])
            if st.form_submit_button("Create project"):
                if name and addr and insp:
                    st.session_state.projects.append({
                        "id": f"proj-{str(uuid.uuid4())[:6]}",
                        "name": name, "address": addr, "building_type": btype,
                        "status": stat, "inspector": insp,
                        "last_inspection": "Not yet inspected",
                        "total_inspections": 0, "open_findings": 0,
                        "critical_findings": 0, "notes": ""
                    })
                    st.success(f"✅ Project '{name}' created!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")

    if not projects:
        st.info("No projects loaded.")
        return

    for project in projects:
        status_icon    = STATUS_COLORS.get(project.get("status", ""), "⚪")
        critical_count = project.get("critical_findings", 0)
        badge_class    = STATUS_BADGE.get(project.get("status", ""), "badge-progress")

        with st.container(border=True):
            h_col, b_col = st.columns([3, 1])
            with h_col:
                st.markdown(f"### {project['name']}")
                st.caption(f"📍 {project['address']}  ·  🏗️ {project['building_type']}")
            with b_col:
                st.markdown(
                    f"<span class='{badge_class}'>{status_icon} {project['status']}</span>",
                    unsafe_allow_html=True)
                if critical_count > 0:
                    st.markdown(
                        f"<span class='badge-critical'>⚠️ {critical_count} critical</span>",
                        unsafe_allow_html=True)

            i1, i2, i3, btn = st.columns([2, 2, 2, 1])
            i1.markdown(f"**Last inspection**  \n{project.get('last_inspection','—')}")
            i2.markdown(f"**Open findings**  \n{project.get('open_findings', 0)}")
            i3.markdown(f"**Inspections**  \n{project.get('total_inspections', 0)}")
            with btn:
                if st.button("Start →", key=f"start_{project['id']}", type="primary"):
                    st.session_state.current_project = project
                    # For proj-001, always reload the sample inspection data
                    if project["id"] == "proj-001":
                        import json as _json
                        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_inspection.json")
                        try:
                            with open(data_path, "r", encoding="utf-8") as f:
                                sample = _json.load(f)
                            st.session_state.checklist_items = sample.get("checklist_items", [])
                            st.session_state.photos          = sample.get("photos", [])
                            st.session_state.voice_notes     = sample.get("voice_notes", [])
                        except FileNotFoundError:
                            pass
                    st.rerun()

            if project.get("notes"):
                st.caption(f"💬 {project['notes']}")

            if (st.session_state.get("current_project") and
                    st.session_state.current_project.get("id") == project["id"]):
                items = st.session_state.checklist_items
                if items:
                    checked = sum(1 for i in items if i.get("checked"))
                    total   = len(items)
                    crit    = sum(1 for i in items
                                  if i.get("severity") == "Critical" and not i.get("checked"))
                    st.progress(checked / total if total > 0 else 0,
                                text=f"✅ {checked}/{total} items complete")
                    if crit > 0:
                        st.error(f"⚠ {crit} critical item(s) still outstanding")
                    else:
                        st.success("✅ No critical items outstanding")

    st.divider()
    render_report_section()

    st.divider()
    st.markdown('<div class="section-header">📸 Photo Gallery</div>', unsafe_allow_html=True)

    all_photos = st.session_state.get("photos", [])
    if all_photos:
        id_to_name = {p["id"]: p["name"] for p in projects}
        f1, f2, f3 = st.columns(3)
        with f1:
            names = ["All"] + list({
                id_to_name.get(p.get("project_id", ""), "Unknown") for p in all_photos})
            selected_project = st.selectbox("Project", names)
        with f2:
            hazards_only = st.checkbox("⚠️ Hazards only")
        with f3:
            search_query = st.text_input("🔍 Search descriptions")

        filtered = all_photos
        if selected_project != "All":
            filtered = [p for p in filtered
                        if id_to_name.get(p.get("project_id", ""), "Unknown") == selected_project]
        if hazards_only:
            filtered = [p for p in filtered if p.get("hazard_flag")]
        if search_query:
            q = search_query.lower()
            filtered = [p for p in filtered if q in p.get("ai_description", "").lower()]

        st.caption(f"{len(filtered)} photo(s) shown")
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
                            st.caption("🖼️ No preview (fixture data)")
                        if photo.get("hazard_flag"):
                            st.error(f"⚠️ {photo.get('hazard_details','')}")
                        else:
                            st.success("✅ No hazard detected")
                        st.markdown(
                            f"**AI description:** {photo.get('ai_description','_Not analysed_')}")
                        pname = id_to_name.get(photo.get("project_id", ""), "Unknown")
                        st.caption(
                            f"🗂 {pname}  ·  📍 {photo.get('location','N/A')}"
                            f"  ·  🕐 {photo.get('timestamp','')[:16]}")
    else:
        st.info("No photos yet — upload from the Inspection tab.")
