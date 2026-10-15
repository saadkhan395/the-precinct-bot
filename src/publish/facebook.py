"""Facebook Page publishing via Graph API.

BUG FIX: attached_media must be JSON-encoded string, not a Python list.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v26.0"
TIMEOUT = 60


def _token() -> str:
    t = os.environ.get("META_PAGE_ACCESS_TOKEN", "").strip()
    if not t:
        raise RuntimeError("META_PAGE_ACCESS_TOKEN is not set")
    return t


def _page_id() -> str:
    p = os.environ.get("META_PAGE_ID", "").strip()
    if not p:
        raise RuntimeError("META_PAGE_ID is not set")
    return p


def _upload_unpublished_photo(image_path: Path) -> str:
    with image_path.open("rb") as f:
        files = {"source": f}
        data = {"published": "false", "access_token": _token()}
        r = requests.post(
            f"{GRAPH}/{_page_id()}/photos",
            data=data,
            files=files,
            timeout=TIMEOUT,
        )
    if not r.ok:
        raise RuntimeError(f"Facebook photo upload {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def publish_image(image_path: Path, caption: str) -> str:
    with image_path.open("rb") as f:
        files = {"source": f}
        data = {"caption": caption, "access_token": _token()}
        r = requests.post(
            f"{GRAPH}/{_page_id()}/photos",
            data=data,
            files=files,
            timeout=TIMEOUT,
        )
    if not r.ok:
        raise RuntimeError(f"Facebook image post {r.status_code}: {r.text[:400]}")
    body = r.json()
    return str(body.get("post_id") or body.get("id"))


def publish_carousel(slide_paths: list, caption: str) -> str:
    """Publish a multi-photo Facebook post. Returns the FB post ID."""
    if not slide_paths:
        raise RuntimeError("No slide paths supplied")

    media_ids = [_upload_unpublished_photo(p) for p in slide_paths]
    # FIX: send attached_media as a JSON-encoded STRING, not a Python list.
    attached = json.dumps([{"media_fbid": mid} for mid in media_ids])

    r = requests.post(
        f"{GRAPH}/{_page_id()}/feed",
        data={
            "message": caption,
            "attached_media": attached,
            "access_token": _token(),
        },
        timeout=TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Facebook carousel post {r.status_code}: {r.text[:400]}")
    return str(r.json()["id"])


def publish_reel(video_path: Path, caption: str) -> str:
    with video_path.open("rb") as f:
        files = {"source": f}
        data = {"description": caption, "access_token": _token()}
        r = requests.post(
            f"{GRAPH}/{_page_id()}/videos",
            data=data,
            files=files,
            timeout=180,
        )
    if not r.ok:
        raise RuntimeError(f"Facebook video post {r.status_code}: {r.text[:400]}")
    return str(r.json()["id"])
