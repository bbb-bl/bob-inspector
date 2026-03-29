import streamlit as st
import uuid
from datetime import datetime
from PIL import Image
import io
import json

from utils.llm_utils import describe_photo
from utils.severity import load_checklist_from_csv, classify_severity


def render():
    st.header("📋 On-Site Inspection")

    # Project selector
    if getattr(st.session_state, "projects", None):
        project_names = [p["name"] for p in st.session_state.projects]
        selected = st.selectbox("Select project", project_names)
        st.session_state.current_project = next(
            p for p in st.session_state.projects if p["name"] == selected
        )
    else:
        st.warning("No projects found — Aymen's fixtures not loaded yet.")
        st.session_state.current_project = {"id": "demo", "name": "Demo Project"}

    # Ensure state keys exist
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

     # CHECKLIST
    st.divider()
    st.subheader("📋 Safety Checklist")

    # Auto-select building type from current project
    project_building_type = None
    if st.session_state.current_project:
        project_building_type = st.session_state.current_project.get("building_type")

    valid_types = ["Commercial", "Residential", "Educational"]
    if project_building_type in valid_types:
        building_type = project_building_type
        st.caption(f"📋 Checklist type auto-set to **{building_type}** based on selected project.")
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
    # Within each severity, checked items go to the bottom
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
        st.error(f"⚠ {len(critical_outstanding)} critical item(s) outstanding")

    st.progress(checked_count / total_count if total_count > 0 else 0)
    st.caption(f"{checked_count} of {total_count} items completed")

    # Group items by zone (safe against missing zone keys)
    zones = {}
    for item in items:
        zone = item.get("zone", "General")
        zones.setdefault(zone, []).append(item)

    # Render each zone as an expander
    for zone, zone_items in zones.items():
        zone_checked = sum(1 for i in zone_items if i.get("checked"))
        is_open = st.session_state.get("open_zone") == zone
        with st.expander(
            f"{zone} ({zone_checked}/{len(zone_items)} done)", expanded=is_open
        ):
            for item in zone_items:
                # Severity badge
                sev = item.get("severity", "Rec")
                if sev == "Critical":
                    badge = '<span style="background:#FF4444;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Critical</span>'
                elif sev == "Minor":
                    badge = '<span style="background:#E8940A;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Minor</span>'
                else:
                    badge = '<span style="background:#2855C8;color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">Rec</span>'

                col1, col2 = st.columns([0.85, 0.15])

                with col1:
                    checked = st.checkbox(
                        item["text"],
                        value=item.get("checked", False),
                        key=f"chk_{item['id']}",
                    )

                    if checked != item.get("checked", False):
                        item["checked"] = checked
                        st.session_state["open_zone"] = zone
                        st.rerun()

                with col2:
                    st.markdown(badge, unsafe_allow_html=True)

                # Detail tooltip and notes field when checked
                if item.get("detail"):
                    st.caption(f"ℹ {item['detail']}")

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

    st.divider()
    # Photo upload
    st.subheader("📸 Upload Site Photos")
    uploaded_files = st.file_uploader(
        "Upload site photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for file in uploaded_files:
            existing_ids = [p["filename"] for p in st.session_state.photos]
            if file.name in existing_ids:
                continue

            image_bytes = file.read()
            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
                pil_img.load()  # validate image
            except Exception:
                st.warning(f"Skipping {file.name}: not a valid image")
                continue

            photo = {
                "id": str(uuid.uuid4())[:8],
                "project_id": st.session_state.current_project["id"],
                "filename": file.name,
                "timestamp": datetime.now().isoformat(),
                "location": "Barcelona, Spain",
                "image_bytes": image_bytes,  # for LLM / APIs
                "image_pil": pil_img,        # for display
                "ai_description": "",
                "hazard_flag": False,
                "hazard_details": "",
            }

            st.session_state.photos.append(photo)

        st.success(f"{len(st.session_state.photos)} photo(s) uploaded!")

    # Backfill image_pil for older photos that only have image_bytes
    for photo in st.session_state.photos:
        if "image_pil" not in photo and "image_bytes" in photo:
            try:
                pil_img = Image.open(io.BytesIO(photo["image_bytes"]))
                pil_img.load()
                photo["image_pil"] = pil_img
            except Exception:
                photo["image_pil"] = None

    # Thumbnail grid
    if st.session_state.photos:
        cols = st.columns(3)
        for i, photo in enumerate(st.session_state.photos):
            with cols[i % 3]:
                if photo.get("image_pil") is not None:
                    st.image(photo["image_pil"], caption=photo["filename"], width=200)
                else:
                    st.warning(f"Cannot display {photo['filename']}")

                # Metadata
                st.caption(
                    f"📁 {photo.get('project_id', 'N/A')} | "
                    f"📍 {photo.get('location', 'N/A')} | "
                    f"🕐 {photo.get('timestamp', '')[:10]}"
                )

                # Hazard status
                if photo.get("hazard_flag"):
                    st.error("⚠ Hazard detected")
                elif photo.get("ai_description") == "":
                    st.caption("Not analysed yet")
                else:
                    st.success("✅ No hazard detected")

                # AI description
                if photo.get("ai_description"):
                    st.caption(f"🤖 {photo['ai_description']}")
                if photo.get("hazard_details"):
                    st.warning(f"⚠ {photo['hazard_details']}")

    # AI Analysis button
    if st.button("🤖 Analyse photos with AI", key="analyse_btn"):
        with st.spinner("Analysing photos..."):
            success, failed = 0, 0
            for photo in st.session_state.photos:
                if photo.get("ai_description") == "" and photo.get("image_bytes"):
                    try:
                        result = describe_photo(photo["image_bytes"])
                        photo["ai_description"] = result.get("description", "")
                        photo["hazard_flag"] = result.get("hazard_flag", False)
                        photo["hazard_details"] = result.get("hazard_details", "")
                        success += 1
                    except Exception:
                        photo["ai_description"] = "Analysis unavailable"
                        failed += 1
                        st.warning(f"Could not analyse {photo['filename']}")

            hazards = sum(1 for p in st.session_state.photos if p.get("hazard_flag"))
            st.success(f"✅ {success} photos analysed. {hazards} hazard(s) detected.")
            if failed:
                st.warning(f"{failed} photo(s) failed.")
            st.rerun()

    # ── VOICE NOTES ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🎙 Voice Notes")

    col_rec, col_status = st.columns([0.3, 0.7])

    with col_rec:
        if not st.session_state.recording:
            if st.button("🎙 Start recording", key="start_rec"):
                st.session_state.recording = True
                st.rerun()
        else:
            if st.button("⏹ Stop recording", key="stop_rec"):
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
                '<div style="background:#FF4444;color:white;padding:8px 16px;border-radius:6px;font-size:14px;">🔴 Recording... speak your observation</div>',
                unsafe_allow_html=True
            )
        else:
            st.caption("Press start to record an on-site observation")

    # Remove any stale notes missing required keys
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