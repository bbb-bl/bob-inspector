import streamlit as st
import uuid
from datetime import datetime
from PIL import Image
import io

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
                    f"📁 {photo['project_id']} | "
                    f"📍 {photo['location']} | "
                    f"🕐 {photo['timestamp'][:10]}"
                )

                # Hazard status
                if photo["hazard_flag"]:
                    st.error("⚠ Hazard detected")
                elif photo["ai_description"] == "":
                    st.caption("Not analysed yet")
                else:
                    st.success("✅ No hazard detected")

                # AI description
                if photo["ai_description"]:
                    st.caption(f"🤖 {photo['ai_description']}")
                if photo["hazard_details"]:
                    st.warning(f"⚠ {photo['hazard_details']}")

    st.divider()

    # AI Analysis button
    if st.button("🤖 Analyse photos with AI", key="analyse_btn"):
        with st.spinner("Analysing photos..."):
            success, failed = 0, 0
            for photo in st.session_state.photos:
                if photo["ai_description"] == "":
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

            hazards = sum(1 for p in st.session_state.photos if p["hazard_flag"])
            st.success(f"✅ {success} photos analysed. {hazards} hazard(s) detected.")
            if failed:
                st.warning(f"{failed} photo(s) failed.")
            st.rerun()

    # CHECKLIST
    st.divider()
    st.subheader("📋 Safety Checklist")

    # Building type selector
    building_type = st.selectbox(
        "Building type",
        ["Commercial", "Residential", "Educational"],
        key="building_type_select",
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

    items = st.session_state.checklist_items

    # Progress bar
    checked_count = sum(1 for i in items if i["checked"])
    total_count = len(items)
    critical_outstanding = [
        i for i in items if i["severity"] == "Critical" and not i["checked"]
    ]

    if critical_outstanding:
        st.error(f"⚠ {len(critical_outstanding)} critical item(s) outstanding")

    st.progress(checked_count / total_count if total_count > 0 else 0)
    st.caption(f"{checked_count} of {total_count} items completed")

    st.divider()

    # Group items by zone (safe against missing zone keys)
    zones = {}
    for item in items:
        zone = item.get("zone", "General")  # fallback for missing zone
        zones.setdefault(zone, []).append(item)

    # Render each zone as an expander
    for zone, zone_items in zones.items():
        zone_checked = sum(1 for i in zone_items if i["checked"])
        is_open = st.session_state.get("open_zone") == zone
        with st.expander(
            f"{zone} ({zone_checked}/{len(zone_items)} done)", expanded=is_open
        ):
            for item in zone_items:
                # Severity badge
                if item["severity"] == "Critical":
                    badge = "Critical"
                elif item["severity"] == "Minor":
                    badge = "Minor"
                else:
                    badge = "Rec"

                col1, col2 = st.columns([0.85, 0.15])

                with col1:
                    checked = st.checkbox(
                        item["text"],
                        value=item["checked"],
                        key=f"chk_{item['id']}",
                    )

                    if checked != item["checked"]:
                        item["checked"] = checked
                        st.session_state["open_zone"] = zone
                        st.rerun()

                with col2:
                    st.markdown(badge, unsafe_allow_html=True)

                # Detail tooltip and notes field when checked
                if item.get("detail"):
                    st.caption(f"ℹ {item['detail']}")

                if item["checked"]:
                    notes = st.text_input(
                        "Notes",
                        value=item["notes"],
                        key=f"notes_{item['id']}",
                        placeholder="Add observation...",
                    )

                    if notes != item["notes"]:
                        item["notes"] = notes
                        item["severity"] = (
                            classify_severity(notes) if notes else item["severity"]
                        )

    # Custom item input
    st.divider()
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
