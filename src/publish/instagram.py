"""Instagram publishing via Instagram API.

Instagram's API does not accept file uploads. It requires a public URL for
every image and video. Since this repo is public, we build URLs pointing at
raw.githubusercontent.com.

Reads IG_USER_ID and INSTAGRAM_ACCESS_TOKEN from environment.
"""
from __future__ import annotations

import os
import time

import requests

GRAPH = "https://graph.instagram.com/v26.0"
TIMEOUT = 60
REPO_RAW = "https://raw.githubusercontent.com/Saadkhan395/the-precinct-bot/main"


def _token() -> str:
    t = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not t:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN is not set")
    return t


def _ig_user_id() -> str:
    p = os.environ.get("IG_USER_ID", "").strip()
    if not p:
        raise RuntimeError("IG_USER_ID is not set")
    return p


def media_url(relative_path: str) -> str:
    """Turn a repo-relative path into a public raw.githubusercontent.com URL."""
    path = relative_path.lstrip("/")
    return f"{REPO_RAW}/{path}"


def _create_container(payload: dict) -> str:
    payload = {**payload, "access_token": _token()}
    r = requests.post(
        f"{GRAPH}/{_ig_user_id()}/media",
        data=payload,
        timeout=TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Instagram media create {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def _publish_container(creation_id: str) -> str:
    r = requests.post(
        f"{GRAPH}/{_ig_user_id()}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": _token(),
        },
        timeout=TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Instagram publish {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def _wait_until_ready(creation_id: str, max_wait: int = 180) -> None:
    """Poll container status until FINISHED or error. For reels only."""
    start = time.time()
    while time.time() - start < max_wait:
        r = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": _token()},
            timeout=TIMEOUT,
        )
        if r.ok:
            code = r.json().get("status_code", "")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram container failed: {r.text[:400]}")
        time.sleep(10)
    raise RuntimeError("Instagram container did not finish processing in time")


def publish_image(image_url: str, caption: str) -> str:
    """Publish a single image. Returns the IG media ID."""
    cid = _create_container({"image_url": image_url, "caption": caption})
    return _publish_container(cid)


def publish_carousel(slide_urls: list, caption: str) -> str:
    """Publish a carousel. Returns the IG media ID.

    Steps:
      1. Create one child container per slide (is_carousel_item=true).
      2. Create a parent CAROUSEL container with the child IDs.
      3. Publish the parent.
    """
    if not slide_urls:
        raise RuntimeError("No slide URLs supplied")

    children = [_create_container({
        "image_url": url,
        "is_carousel_item": "true",
    }) for url in slide_urls]

    parent = _create_container({
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    })
    return _publish_container(parent)


def publish_reel(video_url: str, caption: str) -> str:
    """Publish a reel. Returns the IG media ID.

    Steps:
      1. Create REELS container with video_url.
      2. Poll status until FINISHED.
      3. Publish.
    """
    cid = _create_container({
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
    })
    _wait_until_ready(cid)
    return _publish_container(cid)