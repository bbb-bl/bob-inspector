import streamlit as st
import uuid
from datetime import datetime
from utils.llm_utils import describe_photo


def render():
    st.header("📋 On-Site Inspection")

    # Project selector
    if st.session_state.projects:
        project_names = [p["name"] for p in st.session_state.projects]
        selected = st.selectbox("Select project", project_names)
        st.session_state.current_project = next(
            p for p in st.session_state.projects if p["name"] == selected
        )
    else:
        st.warning("No projects found — Aymen's fixtures not loaded yet.")
        st.session_state.current_project = {"id": "demo", "name": "Demo Project"}

    st.divider()

    # Photo upload
    st.subheader("📸 Upload Site Photos")
    uploaded_files = st.file_uploader(
        "Upload site photos",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            existing_ids = [p["filename"] for p in st.session_state.photos]
            if file.name not in existing_ids:
                photo = {
                    "id": str(uuid.uuid4())[:8],
                    "project_id": st.session_state.current_project["id"],
                    "filename": file.name,
                    "timestamp": datetime.now().isoformat(),
                    "location": "Barcelona, Spain",
                    "image_bytes": file.read(),
                    "ai_description": "",
                    "hazard_flag": False,
                    "hazard_details": ""
                }
                st.session_state.photos.append(photo)

        st.success(f"{len(st.session_state.photos)} photo(s) uploaded!")

        # Thumbnail grid
        cols = st.columns(3)
        for i, photo in enumerate(st.session_state.photos):
            with cols[i % 3]:
                st.image(photo["image_bytes"], caption=photo["filename"], width=200)
                # Metadata
                st.caption(
                    f"📁 {photo['project_id']}  |  "
                    f"📍 {photo['location']}  |  "
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
                if photo["ai_description"] and photo["ai_description"] != "":
                    st.caption(f"🤖 {photo['ai_description']}")
                if photo["hazard_details"] and photo["hazard_details"] != "":
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
                            photo["ai_description"] = result["description"]
                            photo["hazard_flag"] = result["hazard_flag"]
                            photo["hazard_details"] = result["hazard_details"]
                            success += 1
                        except Exception as e:
                            photo["ai_description"] = "Analysis unavailable"
                            failed += 1
                            st.warning(f"Could not analyse {photo['filename']}")
            hazards = sum(1 for p in st.session_state.photos if p["hazard_flag"])
            st.success(f"✅ {success} photos analysed. {hazards} hazard(s) detected.")
            if failed:
                st.warning(f"{failed} photo(s) failed.")
            st.rerun()
