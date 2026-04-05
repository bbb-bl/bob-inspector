import streamlit as st
import uuid
import os
import json
from datetime import datetime
from PIL import Image
import io

from utils.llm_utils import describe_photo
from utils.severity import load_checklist_from_csv, classify_severity
from utils.storage import upload_photo, save_description, load_photos_from_supabase


# ── FOLDER SYSTEM ────────────────────────────────────────────────
def slugify(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-")

def get_project_dir(project_name: str) -> str:
    return os.path.join("data", "projects_data", slugify(project_name))

def get_project_name_from_id(project_id: str) -> str:
    for p in st.session_state.get("projects", []):
        if p["id"] == project_id:
            return p["name"]
    return project_id

def save_photo_to_disk(photo: dict):
    """Save image bytes + AI description to project folder."""
    project_name = get_project_name_from_id(photo.get("project_id", "demo"))
    photos_dir = os.path.join(get_project_dir(project_name), "photos")
    desc_dir = os.path.join(get_project_dir(project_name), "descriptions")
    os.makedirs(photos_dir, exist_ok=True)
    os.makedirs(desc_dir, exist_ok=True)

    # Save image
    if photo.get("image_bytes"):
        img_path = os.path.join(photos_dir, photo["id"] + "_" + photo["filename"])
        with open(img_path, "wb") as f:
            f.write(photo["image_bytes"])

    # Save description as JSON
    desc_path = os.path.join(desc_dir, photo["id"] + ".json")
    meta = {k: v for k, v in photo.items() if k not in ["image_bytes", "image_pil"]}
    with open(desc_path, "w") as f:
        json.dump(meta, f, indent=2)

def load_photos_from_disk(project_name: str) -> list:
    """Load all photos for a project from disk."""
    desc_dir = os.path.join(get_project_dir(project_name), "descriptions")
    photos_dir = os.path.join(get_project_dir(project_name), "photos")
    if not os.path.exists(desc_dir):
        return []

    photos = []
    for fname in os.listdir(desc_dir):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(desc_dir, fname), "r") as f:
            meta = json.load(f)

        # Load image bytes
        img_path = os.path.join(photos_dir, meta["id"] + "_" + meta["filename"])
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                meta["image_bytes"] = f.read()
            try:
                pil_img = Image.open(io.BytesIO(meta["image_bytes"]))
                pil_img.load()
                meta["image_pil"] = pil_img
            except Exception:
                meta["image_pil"] = None
        else:
            meta["image_bytes"] = None
            meta["image_pil"] = None

        photos.append(meta)
    return photos


def render():
    st.markdown(
        '<div style="margin-bottom:8px;">'
        '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">Active Session</div>'
        '<div style="font-size:1.8rem;font-weight:900;letter-spacing:0.01em;">On-Site Inspection</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── SAFE INIT — prevent None crash in dashboard.py
    if not st.session_state.get("current_project"):
        st.session_state.current_project = {}

    # ── PROJECT SELECTOR ─────────────────────────────────────────
    if getattr(st.session_state, "projects", None):
        project_names = [p["name"] for p in st.session_state.projects]

        # Default to current project if one is already selected
        current = st.session_state.get("current_project") or {}
        current_name = current.get("name")
        default_idx = project_names.index(current_name) if current_name in project_names else None

        selected = st.selectbox(
            "Select project",
            project_names,
            index=default_idx,
            placeholder="— Choose a project to begin —",
        )

        project_selected = selected is not None

        if project_selected:
            st.session_state.current_project = next(
                p for p in st.session_state.projects if p["name"] == selected
            )
    else:
        st.warning("No projects found — fixtures not loaded yet.")
        st.session_state.current_project = {"id": "demo", "name": "Demo Project"}
        project_selected = True

    # ── ENSURE STATE KEYS ────────────────────────────────────────
    if "photos" not in st.session_state:
        st.session_state.photos = []
    if "checklist_items" not in st.session_state:
        st.session_state.checklist_items = []
    if "voice_notes" not in st.session_state:
        st.session_state.voice_notes = []
    if "voice_transcription_index" not in st.session_state:
        st.session_state.voice_transcription_index = 0
    if "added_to_checklist" not in st.session_state:
        st.session_state.added_to_checklist = set()
    if "recording" not in st.session_state:
        st.session_state.recording = False
    if "newly_analysed_ids" not in st.session_state:
        st.session_state.newly_analysed_ids = set()
    if "newly_uploaded_ids" not in st.session_state:
        st.session_state.newly_uploaded_ids = set()
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    # Load saved photos for current project from Supabase (once per project)
    project_id = (st.session_state.current_project or {}).get("id", "")

    # Per-project deleted filenames — must be after project_id is defined
    deleted_key = f"deleted_filenames_{project_id}"
    if deleted_key not in st.session_state:
        st.session_state[deleted_key] = set()

    if project_selected and project_id:
        loaded_key = f"loaded_{project_id}"
        if not st.session_state.get(loaded_key):
            project_name = st.session_state.current_project.get("name", project_id)
            try:
                with st.spinner(f"Loading project data for {project_name}..."):
                    saved = load_photos_from_supabase(project_name)
                    existing_ids = [p["id"] for p in st.session_state.photos]
                    for p in saved:
                        if p["id"] not in existing_ids:
                            st.session_state.photos.append(p)
            except Exception:
                pass  # Network blip — silently skip, will retry next session
            finally:
                st.session_state[loaded_key] = True  # Always mark done to avoid infinite retry

        # Load historical flagged items for this project (once per project)
        flags_key = f"flags_loaded_{project_id}"
        if not st.session_state.get(flags_key):
            try:
                from components.dashboard import load_historical_flags
                project_dict = st.session_state.current_project or {}
                st.session_state["historical_flags"] = load_historical_flags(project_dict)
            except Exception:
                st.session_state["historical_flags"] = {}
            st.session_state[flags_key] = True

    # ── HELPER: photos for THIS project only ────────────────────
    def current_project_photos():
        return [p for p in st.session_state.photos if p.get("project_id") == project_id]

    # ── BACKFILL location for all photos using project address ───
    project_id_to_address = {
        p["id"]: p.get("address", "Barcelona, Spain")
        for p in st.session_state.get("projects", [])
    }
    project_name_to_address = {
        p["name"]: p.get("address", "Barcelona, Spain")
        for p in st.session_state.get("projects", [])
    }
    for photo in st.session_state.photos:
        if photo.get("location") in ["", "Barcelona, Spain", None]:
            pid = photo.get("project_id", "")
            # Try by project id first, then by project name
            address = project_id_to_address.get(pid) or project_name_to_address.get(pid, "Barcelona, Spain")
            photo["location"] = address

    # ── CRITICAL ITEMS BANNER ────────────────────────────────────
    if project_selected and st.session_state.checklist_items:
        critical_outstanding = [
            i for i in st.session_state.checklist_items
            if i.get("severity") == "Critical" and not i.get("checked")
        ]
        if critical_outstanding:
            previews = ", ".join(
                (i["text"][:45] + "…" if len(i["text"]) > 45 else i["text"])
                for i in critical_outstanding[:3]
            )
            if len(critical_outstanding) > 3:
                previews += f" +{len(critical_outstanding) - 3} more"
            st.markdown(f"""
            <div style="background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);
                        border-left:4px solid #EF4444;border-radius:8px;padding:12px 16px;margin:12px 0;">
                <div style="color:#f87171;font-weight:700;font-size:0.82rem;letter-spacing:0.06em;margin-bottom:4px;">
                    △ {len(critical_outstanding)} CRITICAL ITEM(S) REQUIRE ATTENTION
                </div>
                <div style="color:#9ca3af;font-size:0.78rem;line-height:1.5;">{previews}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── CHECKLIST ────────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<div style="margin-bottom:12px;">'
        '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">On-Site</div>'
        '<div style="font-size:1.3rem;font-weight:800;letter-spacing:0.02em;">Safety Checklist</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Auto-select building type from current project
    project_building_type = st.session_state.current_project.get("building_type")

    valid_types = ["Commercial", "Residential", "Educational"]
    if project_building_type in valid_types:
        building_type = project_building_type
        st.caption(f"Checklist type auto-set to **{building_type}** based on selected project.")
    else:
        building_type = st.selectbox(
            "Building type",
            valid_types,
            key="building_type_select"
        )

    # Load checklist when building type changes or checklist is empty
    if (
        not st.session_state.checklist_items
        or st.session_state.get("last_building_type") != building_type
    ):
        st.session_state.checklist_items = load_checklist_from_csv(
            "data/checklist.csv",
            building_type,
        )
        st.session_state["last_building_type"] = building_type

    # Sort by severity: Critical first, then Minor, then Recommendation
    severity_order = {"Critical": 0, "Minor": 1, "Recommendation": 2}
    items = sorted(
        st.session_state.checklist_items,
        key=lambda i: (i.get("checked", False), severity_order.get(i.get("severity", "Recommendation"), 2))
    )

    # Progress bar
    checked_count = sum(1 for i in items if i.get("checked"))
    total_count = len(items)
    critical_outstanding = [
        i for i in items if i.get("severity") == "Critical" and not i.get("checked")
    ]

    if critical_outstanding:
        st.error(f"△ {len(critical_outstanding)} critical item(s) outstanding")

    st.progress(checked_count / total_count if total_count > 0 else 0)
    st.caption(f"{checked_count} of {total_count} items completed")

    # Group items by zone (needed early for quick-nav)
    zones_preview = {}
    for item in items:
        z = item.get("zone", "General")
        zones_preview.setdefault(z, []).append(item)

    # ── Zone quick-nav ───────────────────────────────────────────
    if zones_preview:
        st.markdown(
            '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;'
            'color:#6B7280;font-weight:600;margin:8px 0 4px;">Jump to zone</div>',
            unsafe_allow_html=True,
        )
        nav_cols = st.columns(len(zones_preview))
        for idx, (zone_name, zone_items_preview) in enumerate(zones_preview.items()):
            zone_done = sum(1 for i in zone_items_preview if i.get("checked"))
            zone_has_crit = any(
                i.get("severity") == "Critical" and not i.get("checked")
                for i in zone_items_preview
            )
            dot_color = "#EF4444" if zone_has_crit else (
                "#22C55E" if zone_done == len(zone_items_preview) else "#3B82F6"
            )
            with nav_cols[idx]:
                if st.button(
                    zone_name,
                    key=f"nav_{zone_name}",
                    use_container_width=True,
                    help=f"{zone_done}/{len(zone_items_preview)} done"
                        + (" — critical items outstanding" if zone_has_crit else ""),
                ):
                    st.session_state["open_zone"] = zone_name
                    st.rerun()

    # ── Checklist search ─────────────────────────────────────
    search_q = st.text_input(
        "Search checklist",
        placeholder="Search items e.g. 'electrical', 'scaffolding'...",
        key="checklist_search",
        label_visibility="collapsed",
    )

    # Group items by zone
    zones = {}
    for item in items:
        zone = item.get("zone", "General")
        zones.setdefault(zone, []).append(item)

    # If searching, show a flat filtered list instead of zone expanders
    if search_q:
        q = search_q.lower()
        matching = [
            i for i in items
            if q in i.get("text", "").lower()
            or q in i.get("zone", "").lower()
            or q in i.get("detail", "").lower()
            or q in i.get("category", "").lower()
        ]
        if not matching:
            st.markdown(
                f'<div style="color:#6B7280;font-size:0.85rem;padding:12px 0;">No items match "{search_q}"</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-size:0.75rem;color:#6B7280;margin-bottom:8px;">'
                f'{len(matching)} item(s) matching "{search_q}"</div>',
                unsafe_allow_html=True,
            )
            historical_flags = st.session_state.get("historical_flags", {})
            for item in matching:
                sev = item.get("severity", "Rec")
                if sev == "Critical":
                    badge = '<span style="background:#FF4444;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Critical</span>'
                elif sev == "Minor":
                    badge = '<span style="background:#E8940A;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Minor</span>'
                else:
                    badge = '<span style="background:#2855C8;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Rec</span>'
                times_flagged = historical_flags.get(item.get("text", ""), 0)
                if times_flagged > 0 and not item.get("checked"):
                    visits = "visit" if times_flagged == 1 else "visits"
                    badge += (
                        f' <span style="background:rgba(245,158,11,0.15);color:#fbbf24;'
                        f'padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;'
                        f'border:1px solid rgba(245,158,11,0.3);">Outstanding {times_flagged} {visits}</span>'
                    )
                zone_label = f'<span style="color:#6B7280;font-size:0.72rem;"> — {item.get("zone","")}</span>'
                col1, col2 = st.columns([0.85, 0.15])
                with col1:
                    checked = st.checkbox(
                        item["text"],
                        value=item.get("checked", False),
                        key=f"srch_chk_{item['id']}",
                    )
                    if checked != item.get("checked", False):
                        item["checked"] = checked
                        if checked:
                            item["checked_at"] = datetime.now().strftime("%H:%M")
                            item["checked_by"] = (st.session_state.get("current_project") or {}).get("inspector", "")
                        else:
                            item.pop("checked_at", None)
                            item.pop("checked_by", None)
                        st.rerun()
                    if item.get("checked") and item.get("checked_at"):
                        by = f" · {item['checked_by']}" if item.get("checked_by") else ""
                        st.markdown(
                            f'<div style="font-size:0.7rem;color:#4ade80;margin:-4px 0 4px;">✓ Checked at {item["checked_at"]}{by}</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(f'<div style="font-size:0.72rem;color:#6B7280;margin-top:-4px;">{item.get("zone","")}</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(badge, unsafe_allow_html=True)

    if not search_q:
        for zone, zone_items in zones.items():
            zone_checked = sum(1 for i in zone_items if i.get("checked"))
            has_critical = any(
                i.get("severity") == "Critical" and not i.get("checked")
                for i in zone_items
            )
            zone_color = "#EF4444" if has_critical else (
                "#22C55E" if zone_checked == len(zone_items) else "#3B82F6"
            )
            st.markdown(
                f'<div style="height:2px;background:{zone_color};border-radius:1px;'
                f'margin-bottom:2px;opacity:0.7;"></div>',
                unsafe_allow_html=True,
            )
            is_open = st.session_state.get("open_zone") == zone
            with st.expander(
                f"{zone} ({zone_checked}/{len(zone_items)} done)", expanded=is_open
            ):
                historical_flags = st.session_state.get("historical_flags", {})
                for item in zone_items:
                    sev = item.get("severity", "Rec")
                    if sev == "Critical":
                        badge = '<span style="background:#FF4444;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Critical</span>'
                    elif sev == "Minor":
                        badge = '<span style="background:#E8940A;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Minor</span>'
                    else:
                        badge = '<span style="background:#2855C8;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Rec</span>'

                    times_flagged = historical_flags.get(item.get("text", ""), 0)
                    if times_flagged > 0 and not item.get("checked"):
                        visits = "visit" if times_flagged == 1 else "visits"
                        badge += (
                            f' <span style="background:rgba(245,158,11,0.15);color:#fbbf24;'
                            f'padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;'
                            f'border:1px solid rgba(245,158,11,0.3);">'
                            f'Outstanding {times_flagged} {visits}</span>'
                        )

                    col1, col2 = st.columns([0.85, 0.15])

                    with col1:
                        checked = st.checkbox(
                            item["text"],
                            value=item.get("checked", False),
                            key=f"chk_{item['id']}",
                        )
                        if checked != item.get("checked", False):
                            item["checked"] = checked
                            if checked:
                                item["checked_at"] = datetime.now().strftime("%H:%M")
                                inspector = (st.session_state.get("current_project") or {}).get("inspector", "")
                                item["checked_by"] = inspector
                            else:
                                item.pop("checked_at", None)
                                item.pop("checked_by", None)
                            st.session_state["open_zone"] = zone
                            st.rerun()
                        if item.get("checked") and item.get("checked_at"):
                            by = f" · {item['checked_by']}" if item.get("checked_by") else ""
                            st.markdown(
                                f'<div style="font-size:0.7rem;color:#4ade80;margin:-4px 0 4px;">✓ Checked at {item["checked_at"]}{by}</div>',
                                unsafe_allow_html=True,
                            )

                    with col2:
                        st.markdown(badge, unsafe_allow_html=True)

                    if item.get("detail"):
                        st.caption(item['detail'])

                    if item.get("checked", False):
                        notes = st.text_input(
                            "Notes",
                            value=item.get("notes", ""),
                            key=f"notes_{item['id']}",
                            placeholder="Add observation...",
                        )
                        if notes != item.get("notes", ""):
                            item["notes"] = notes
                            item["severity"] = (
                                classify_severity(notes) if notes else item.get("severity", "Rec")
                            )

    # Custom item input
    st.markdown("**Add custom item**")
    col_input, col_btn = st.columns([0.8, 0.2])
    with col_input:
        custom_text = st.text_input(
            "Custom item",
            key="custom_item_input",
            label_visibility="collapsed",
            placeholder="Describe the issue...",
        )
    with col_btn:
        if st.button("Add", key="add_custom_btn"):
            if custom_text.strip():
                new_item = {
                    "id": f"CUSTOM-{str(uuid.uuid4())[:6]}",
                    "text": custom_text.strip(),
                    "detail": "",
                    "zone": "Custom",
                    "building_type": "All",
                    "category": "Custom",
                    "regulation_ref": "",
                    "checked": False,
                    "notes": "",
                    "severity": classify_severity(custom_text.strip()),
                }
                st.session_state.checklist_items.append(new_item)
                st.rerun()

    # ── PHOTO UPLOAD ─────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<div style="margin-bottom:12px;">'
        '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">Documentation</div>'
        '<div style="font-size:1.3rem;font-weight:800;letter-spacing:0.02em;">Site Photos</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    uploaded_files = st.file_uploader(
        "Upload site photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
    )

    if uploaded_files:
        if not project_selected:
            st.warning("Please select a project before uploading photos.")
        else:
            existing_filenames = [
                p["filename"] for p in st.session_state.photos
                if p.get("project_id") == project_id
            ]
            new_count = 0
            for file in uploaded_files:
                if file.name in existing_filenames or file.name in st.session_state[deleted_key]:
                    continue

                image_bytes = file.read()
                try:
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    pil_img.load()
                except Exception:
                    st.warning(f"Skipping {file.name}: not a valid image")
                    continue

                photo = {
                    "id": str(uuid.uuid4())[:8],
                    "project_id": project_id,
                    "filename": file.name,
                    "timestamp": datetime.now().isoformat(),
                    "location": st.session_state.current_project.get("address", "Barcelona, Spain"),
                    "image_bytes": image_bytes,
                    "image_pil": pil_img,
                    "ai_description": "",
                    "hazard_flag": False,
                    "hazard_details": "",
                }
                st.session_state.photos.append(photo)
                st.session_state.newly_uploaded_ids.add(photo["id"])
                project_name = st.session_state.current_project.get("name", project_id)
                upload_photo(photo, project_name)
                new_count += 1

            if new_count:
                st.success(f"{new_count} new photo(s) saved!")

    # Backfill image_pil for older photos
    for photo in st.session_state.photos:
        if "image_pil" not in photo and photo.get("image_bytes"):
            try:
                pil_img = Image.open(io.BytesIO(photo["image_bytes"]))
                pil_img.load()
                photo["image_pil"] = pil_img
            except Exception:
                photo["image_pil"] = None

    # ── THUMBNAIL GRID — only shown after a project is selected ──
    if not project_selected:
        pass  # uploader visible above; grid hidden until project chosen
    else:
        project_photos = current_project_photos()

        if project_photos:
            photo_count = len(project_photos)
            hazard_count = sum(1 for p in project_photos if p.get("hazard_flag"))
            analysed_count = sum(
                1 for p in project_photos
                if p.get("ai_description") not in ["", "Analysis unavailable"]
            )

            c1, c2, c3 = st.columns(3)
            c1.metric("Photos", photo_count)
            c2.metric("Analysed", f"{analysed_count}/{photo_count}")
            c3.metric("Hazards", hazard_count)

            st.divider()

            # Split into previous vs newly uploaded this session
            old_photos = [p for p in project_photos if p["id"] not in st.session_state.newly_uploaded_ids]
            new_photos = [p for p in project_photos if p["id"] in st.session_state.newly_uploaded_ids]

            # ── Section 1: Previous photos (thumbnail grid only) ──
            if old_photos:
                with st.expander(f"Previous photos ({len(old_photos)})", expanded=False):
                    cols = st.columns(3)
                    for i, photo in enumerate(old_photos):
                        with cols[i % 3]:
                            if photo.get("image_pil") is not None:
                                st.image(photo["image_pil"], caption=photo["filename"], width=200)
                            else:
                                st.caption(f"{photo['filename']} (no preview)")
                            st.caption(
                                f"{photo.get('location', 'N/A')}  ·  "
                                f"{photo.get('timestamp', '')[:10]}"
                            )

            # ── Section 2: Newly uploaded photos (image + AI side by side if analysed) ──
            if new_photos:
                with st.expander(f"Newly uploaded photos ({len(new_photos)})", expanded=True):
                    for photo in new_photos:
                        with st.container(border=True):
                            img_col, ai_col = st.columns([0.35, 0.65])
                            with img_col:
                                if photo.get("image_pil") is not None:
                                    st.image(photo["image_pil"], caption=photo["filename"], width=400)
                                else:
                                    st.caption(f"{photo['filename']} (no preview)")
                                st.caption(
                                    f"{photo.get('location', 'N/A')}  ·  "
                                    f"{photo.get('timestamp', '')[:10]}"
                                )
                            with ai_col:
                                ai_desc = photo.get("ai_description", "")
                                if ai_desc == "":
                                    st.caption("Not analysed yet — click Analyse to run AI detection")
                                    st.markdown("""
                                    <style>
                                    div.delete-btn > div[data-testid="stButton"] > button {
                                        background-color: #dc3545 !important;
                                        color: white !important;
                                        border-color: #dc3545 !important;
                                    }
                                    div.delete-btn > div[data-testid="stButton"] > button:hover {
                                        background-color: #a71d2a !important;
                                    }
                                    </style>
                                    """, unsafe_allow_html=True)
                                    confirm_key = f"confirm_del_photo_{photo['id']}"
                                    if not st.session_state.get(confirm_key):
                                        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                                        if st.button("✕ Delete photo", key=f"del_{photo['id']}"):
                                            st.session_state[confirm_key] = True
                                            st.rerun()
                                        st.markdown('</div>', unsafe_allow_html=True)
                                    else:
                                        st.warning("Delete this photo?")
                                        cy, cn = st.columns(2)
                                        with cy:
                                            if st.button("Yes, delete", key=f"del_yes_{photo['id']}", type="primary"):
                                                st.session_state[deleted_key].add(photo["filename"])
                                                st.session_state.photos = [
                                                    p for p in st.session_state.photos if p["id"] != photo["id"]
                                                ]
                                                st.session_state.newly_uploaded_ids.discard(photo["id"])
                                                st.session_state.uploader_key += 1
                                                st.session_state.pop(confirm_key, None)
                                                st.rerun()
                                        with cn:
                                            if st.button("Cancel", key=f"del_no_{photo['id']}"):
                                                st.session_state.pop(confirm_key, None)
                                                st.rerun()
                                elif ai_desc == "Analysis unavailable":
                                    st.warning("Analysis failed")
                                elif photo.get("hazard_flag"):
                                    st.error("## Hazard detected")
                                    if photo.get("hazard_details"):
                                        st.warning(photo['hazard_details'])
                                    st.write(ai_desc)
                                else:
                                    st.success("## No hazard detected")
                                    st.write(ai_desc)

            st.divider()

            unanalysed = [
                p for p in project_photos
                if p.get("ai_description") == "" and p.get("image_bytes")
            ]
            if unanalysed:
                if st.button(f"Analyse {len(unanalysed)} photo(s) with AI", key="analyse_btn"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    success, failed = 0, 0
                    total = len(unanalysed)

                    for idx, photo in enumerate(unanalysed):
                        status_text.caption(f"Analysing {photo['filename']} ({idx+1}/{total})...")
                        try:
                            result = describe_photo(photo["image_bytes"])
                            photo["ai_description"] = result.get("description", "")
                            photo["hazard_flag"] = result.get("hazard_flag", False)
                            photo["hazard_details"] = result.get("hazard_details", "")
                            project_name = st.session_state.current_project.get("name", project_id)
                            save_description(photo, project_name)
                            st.session_state.newly_analysed_ids.add(photo["id"])
                            success += 1
                        except Exception:
                            photo["ai_description"] = "Analysis unavailable"
                            failed += 1
                            st.warning(f"Could not analyse {photo['filename']}")
                        progress_bar.progress((idx + 1) / total)

                    status_text.empty()
                    hazards = sum(1 for p in project_photos if p.get("hazard_flag"))
                    st.success(f"{success} photo(s) analysed. {hazards} hazard(s) detected.")
                    if failed:
                        st.warning(f"{failed} photo(s) failed.")
                    st.rerun()
            else:
                st.success("All photos have been analysed.")

            hazard_photos = [p for p in project_photos if p.get("hazard_flag")]
            if hazard_photos:
                st.divider()
                with st.expander(f"△ Hazard Summary ({len(hazard_photos)} found)", expanded=True):
                    st.caption(f"{len(hazard_photos)} hazard(s) found — review before leaving the site:")
                    for p in hazard_photos:
                        with st.container(border=True):
                            c1, c2 = st.columns([0.3, 0.7])
                            with c1:
                                if p.get("image_pil"):
                                    st.image(p["image_pil"], width=120)
                            with c2:
                                st.markdown(f"**{p['filename']}**")
                                st.caption(f"{p.get('location','N/A')}  ·  {p.get('timestamp','')[:10]}")
                                st.error(f"△ {p.get('hazard_details', 'Hazard detected')}")

        else:
            st.markdown("""
            <div style="border:2px dashed rgba(255,255,255,0.1);border-radius:12px;
                        padding:48px;text-align:center;margin:16px 0;">
                <div style="font-size:1.6rem;margin-bottom:10px;opacity:0.3;">▣</div>
                <div style="font-weight:700;font-size:0.95rem;margin-bottom:6px;color:#6B7280;">No photos yet</div>
                <div style="font-size:0.82rem;color:#4B5563;">Upload site photos above to get started</div>
            </div>""", unsafe_allow_html=True)

    # ── VOICE NOTES ──────────────────────────────────────────────
    st.divider()
    st.markdown(
        '<div style="margin-bottom:12px;">'
        '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">Field Notes</div>'
        '<div style="font-size:1.3rem;font-weight:800;letter-spacing:0.02em;">Voice Notes</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_rec, col_status = st.columns([0.3, 0.7])

    with col_rec:
        if not st.session_state.recording:
            if st.button("● Start recording", key="start_rec"):
                st.session_state.recording = True
                st.rerun()
        else:
            if st.button("■ Stop recording", key="stop_rec"):
                try:
                    with open("data/voice_transcriptions.json", "r") as f:
                        transcriptions = json.load(f)
                    idx = st.session_state.voice_transcription_index % len(transcriptions)
                    picked = transcriptions[idx]
                    st.session_state.voice_notes.append({
                        "timestamp": datetime.now().strftime("%H:%M"),
                        "text": picked["text"],
                        "zone": picked["zone"],
                        "severity": picked["auto_severity"]
                    })
                    st.session_state.voice_transcription_index += 1
                except Exception as e:
                    st.error(f"Could not load transcription: {e}")
                st.session_state.recording = False
                st.rerun()

    with col_status:
        if st.session_state.recording:
            st.markdown(
                '<div style="background:#FF4444;color:white;padding:8px 16px;border-radius:6px;font-size:14px;letter-spacing:0.02em;">● Recording — speak your observation</div>',
                unsafe_allow_html=True
            )
        else:
            st.caption("Press start to record an on-site observation")

    st.session_state.voice_notes = [
        n for n in st.session_state.voice_notes
        if all(k in n for k in ["text", "timestamp", "zone", "severity"])
    ]

    if st.session_state.voice_notes:
        st.markdown("**Recorded notes**")
        for i, note in enumerate(st.session_state.voice_notes):
            with st.container():
                col_note, col_add = st.columns([0.8, 0.2])
                with col_note:
                    sev = note.get("severity", "Recommendation")
                    if sev == "Critical":
                        badge = '<span style="background:#FF4444;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Critical</span>'
                    elif sev == "Minor":
                        badge = '<span style="background:#E8940A;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Minor</span>'
                    else:
                        badge = '<span style="background:#2855C8;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Rec</span>'
                    st.markdown(
                        f'<div style="padding:8px 0">'
                        f'<span style="font-size:12px;color:gray">{note["timestamp"]}  ·  {note["zone"]}</span>  {badge}<br>'
                        f'<span style="font-size:14px">{note["text"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with col_add:
                    if i in st.session_state.added_to_checklist:
                        st.markdown(
                            '<span style="color:#2E8B57;font-weight:bold;font-size:13px">✓ Added</span>',
                            unsafe_allow_html=True
                        )
                    else:
                        if st.button("+ Checklist", key=f"add_note_{i}"):
                            new_item = {
                                "id": f"VOICE-{str(uuid.uuid4())[:6]}",
                                "text": note["text"],
                                "detail": "Added from voice note",
                                "zone": note["zone"],
                                "building_type": "All",
                                "category": "Voice Note",
                                "regulation_ref": "",
                                "checked": False,
                                "notes": "",
                                "severity": note.get("severity", "Recommendation")
                            }
                            st.session_state.checklist_items.append(new_item)
                            st.session_state.added_to_checklist.add(i)
                            st.rerun()
    else:
        st.caption("No voice notes recorded yet.")

    # ── FINISH INSPECTION ─────────────────────────────────────────
    if project_selected:
        st.divider()
        st.markdown(
            '<div style="margin-bottom:12px;">'
            '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.16em;color:#2855C8;font-weight:700;margin-bottom:4px;">Wrap Up</div>'
            '<div style="font-size:1.3rem;font-weight:800;letter-spacing:0.02em;">Finish Inspection</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        all_items = st.session_state.checklist_items
        all_photos = st.session_state.photos
        all_notes = st.session_state.voice_notes
        done = sum(1 for i in all_items if i.get("checked"))
        total = len(all_items)
        crit_left = [i for i in all_items if i.get("severity") == "Critical" and not i.get("checked")]
        hazard_photos = [p for p in all_photos if p.get("hazard_flag")]
        pct = int(done / total * 100) if total else 0

        if not st.session_state.get("show_finish_summary"):
            if st.button("Mark inspection as complete →", type="primary", use_container_width=True):
                st.session_state["show_finish_summary"] = True
                st.rerun()
        else:
            ready = len(crit_left) == 0
            summary_color = "#22C55E" if ready else "#F59E0B"
            summary_icon = "✓" if ready else "△"
            hazard_color = "#f87171" if hazard_photos else "#4ade80"
            inspector_name = (st.session_state.get("current_project") or {}).get("inspector", "—")
            today_str = datetime.now().strftime("%d %B %Y  ·  %H:%M")

            # Build critical items block separately to avoid nested f-string issues
            if crit_left:
                crit_rows = "".join(
                    f'<div style="color:#9ca3af;font-size:0.75rem;margin-top:2px;">· {item["text"][:60]}</div>'
                    for item in crit_left[:3]
                )
                crit_block = (
                    '<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.2);'
                    'border-radius:6px;padding:10px 14px;margin-bottom:12px;">'
                    f'<div style="color:#f87171;font-size:0.78rem;font-weight:700;">'
                    f'△ {len(crit_left)} critical item(s) still outstanding — review before submitting</div>'
                    + crit_rows + '</div>'
                )
            else:
                crit_block = (
                    '<div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);'
                    'border-radius:6px;padding:10px 14px;margin-bottom:12px;">'
                    '<div style="color:#4ade80;font-size:0.78rem;font-weight:700;">✓ All critical items resolved</div></div>'
                )

            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.1);
                        border-top:3px solid {summary_color};border-radius:10px;padding:20px 24px;margin:8px 0;">
                <div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.12em;
                            color:{summary_color};font-weight:700;margin-bottom:12px;">
                    {summary_icon} Inspection Summary
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px;">
                    <div>
                        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Checklist</div>
                        <div style="font-size:1.6rem;font-weight:800;color:#e8e8f0;">{pct}%</div>
                        <div style="font-size:0.75rem;color:#6B7280;">{done}/{total} items</div>
                    </div>
                    <div>
                        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Hazards</div>
                        <div style="font-size:1.6rem;font-weight:800;color:{hazard_color};">{len(hazard_photos)}</div>
                        <div style="font-size:0.75rem;color:#6B7280;">in {len(all_photos)} photo(s)</div>
                    </div>
                    <div>
                        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Voice Notes</div>
                        <div style="font-size:1.6rem;font-weight:800;color:#e8e8f0;">{len(all_notes)}</div>
                        <div style="font-size:0.75rem;color:#6B7280;">recorded</div>
                    </div>
                </div>
                {crit_block}
                <div style="border-top:1px solid rgba(255,255,255,0.07);margin-top:4px;padding-top:12px;
                            display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Inspector</div>
                        <div style="font-size:0.88rem;font-weight:600;color:#e8e8f0;">{inspector_name}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;color:#6B7280;font-weight:600;">Completed</div>
                        <div style="font-size:0.88rem;font-weight:600;color:#e8e8f0;">{today_str}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Signature block ───────────────────────────────
            st.markdown(
                '<div style="margin-top:16px;">'
                '<div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:0.12em;'
                'color:#6B7280;font-weight:600;margin-bottom:6px;">Digital Signature</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            sig_col, _ = st.columns([2, 1])
            with sig_col:
                signature = st.text_input(
                    "Type your full name to sign this inspection",
                    value=st.session_state.get("inspection_signature", inspector_name),
                    placeholder="Full name...",
                    key="sig_input",
                    label_visibility="collapsed",
                )
            if signature:
                st.session_state["inspection_signature"] = signature
                st.session_state["inspection_signed_at"] = today_str
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#4ade80;margin-top:4px;">'
                    f'✓ Signed as <b>{signature}</b> — {today_str}</div>',
                    unsafe_allow_html=True,
                )

            st.divider()
            col_report, col_reset = st.columns([2, 1])
            with col_report:
                st.info("→ Go to Dashboard to generate and download your inspection report.")
            with col_reset:
                if st.button("Start new inspection", use_container_width=True):
                    st.session_state["show_finish_summary"] = False
                    st.session_state.pop("inspection_signature", None)
                    st.session_state.pop("inspection_signed_at", None)
                    st.rerun()
