"""Instagram publishing via Instagram API.

Requires public URLs for every image and video. Repo is public, so we
use raw.githubusercontent.com URLs.
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
        data={"creation_id": creation_id, "access_token": _token()},
        timeout=TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Instagram publish {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def _wait_until_ready(creation_id: str, max_wait: int = 60, interval: int = 3) -> None:
    start = time.time()
    last_code = ""
    while time.time() - start < max_wait:
        r = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": _token()},
            timeout=TIMEOUT,
        )
        if r.ok:
            last_code = r.json().get("status_code", "")
            if last_code == "FINISHED":
                return
            if last_code in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram container failed: {r.text[:400]}")
        elif r.status_code == 400:
            time.sleep(interval)
            continue
        time.sleep(interval)
    if last_code and last_code not in ("FINISHED", "ERROR", "EXPIRED"):
        return


def publish_image(image_url: str, caption: str) -> str:
    cid = _create_container({"image_url": image_url, "caption": caption})
    _wait_until_ready(cid, max_wait=45)
    return _publish_container(cid)


def publish_carousel(slide_urls: list, caption: str) -> str:
    if not slide_urls:
        raise RuntimeError("No slide URLs supplied")

    children = [
        _create_container({"image_url": url, "is_carousel_item": "true"})
        for url in slide_urls
    ]

    for child in children:
        _wait_until_ready(child, max_wait=45)

    parent = _create_container({
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    })
    _wait_until_ready(parent, max_wait=45)
    return _publish_container(parent)


def publish_reel(video_url: str, caption: str) -> str:
    cid = _create_container({
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
    })
    _wait_until_ready(cid, max_wait=180)
    return _publish_container(cid)
