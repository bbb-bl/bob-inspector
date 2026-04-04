"""
utils/storage.py
Supabase Storage integration for BOB Inspector.
Photos are saved per project: {project_name}/{photo_id}_{filename}
"""

import time
import streamlit as st
from supabase import create_client
import json

BUCKET = "Photos"

@st.cache_resource
def get_supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def slugify(name: str) -> str:
    # Convert to safe folder name: lowercase, spaces to hyphens
    import re
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9]+', '-', name)
    return name.strip('-')


def upload_photo(photo: dict, project_name: str) -> bool:
    """Upload image to Supabase Storage under project folder."""
    try:
        client = get_supabase_client()
        folder = slugify(project_name)
        file_path = f"{folder}/{photo['id']}_{photo['filename']}"

        client.storage.from_(BUCKET).upload(
            path=file_path,
            file=photo["image_bytes"],
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        return True
    except Exception as e:
        st.warning(f"Could not upload {photo['filename']}: {e}")
        return False


def save_description(photo: dict, project_name: str) -> bool:
    """Save AI description as JSON to Supabase Storage."""
    try:
        client = get_supabase_client()
        folder = slugify(project_name)
        file_path = f"{folder}/descriptions/{photo['id']}.json"

        meta = {k: v for k, v in photo.items() if k not in ["image_bytes", "image_pil"]}
        data = json.dumps(meta, indent=2).encode("utf-8")

        client.storage.from_(BUCKET).upload(
            path=file_path,
            file=data,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
        return True
    except Exception as e:
        st.warning(f"Could not save description for {photo['filename']}: {e}")
        return False


def load_photos_from_supabase(project_name: str, retries: int = 3, delay: float = 1.5) -> list:
    """Load all photos + descriptions for a project from Supabase.
    Retries up to `retries` times on transient network errors (Errno 35).
    """
    from PIL import Image
    import io

    client = get_supabase_client()
    folder = slugify(project_name)
    desc_folder = f"{folder}/descriptions"

    for attempt in range(retries):
        try:
            # List description files
            files = client.storage.from_(BUCKET).list(desc_folder)
            if not files:
                return []

            photos = []
            for f in files:
                if not f["name"].endswith(".json"):
                    continue

                # Download description JSON
                desc_path = f"{desc_folder}/{f['name']}"
                res = client.storage.from_(BUCKET).download(desc_path)
                meta = json.loads(res.decode("utf-8"))

                # Download image bytes
                img_path = f"{folder}/{meta['id']}_{meta['filename']}"
                try:
                    img_bytes = client.storage.from_(BUCKET).download(img_path)
                    meta["image_bytes"] = img_bytes
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    pil_img.load()
                    meta["image_pil"] = pil_img
                except Exception:
                    meta["image_bytes"] = None
                    meta["image_pil"] = None

                photos.append(meta)

            return photos

        except Exception as e:
            err_str = str(e)
            is_transient = any(x in err_str for x in ["Errno 35", "Errno 11", "temporarily unavailable"])
            if is_transient and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))  # 1.5s → 3s → 4.5s
                continue
            # Non-retryable error or all retries exhausted — fail silently
            return []

    return []