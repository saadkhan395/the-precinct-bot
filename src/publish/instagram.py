"""Instagram publishing via Instagram API."""
from __future__ import annotations

import os
import time

import requests

GRAPH = "https://graph.instagram.com/v26.0"
TIMEOUT = 60
REPO_RAW = "https://raw.githubusercontent.com/Saadkhan395/the-precinct-bot/main"


def _token():
    t = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not t:
        raise RuntimeError("INSTAGRAM_ACCESS_TOKEN is not set")
    return t


def _ig_user_id():
    p = os.environ.get("IG_USER_ID", "").strip()
    if not p:
        raise RuntimeError("IG_USER_ID is not set")
    return p


def media_url(relative_path):
    path = relative_path.lstrip("/")
    return f"{REPO_RAW}/{path}"


def _create_container(payload):
    payload = dict(payload)
    payload["access_token"] = _token()
    r = requests.post(
        f"{GRAPH}/{_ig_user_id()}/media",
        data=payload,
        timeout=TIMEOUT,
    )
    if not r.ok:
        raise RuntimeError(f"Instagram media create {r.status_code}: {r.text[:400]}")
    return r.json()["id"]


def _publish_container(creation_id, max_attempts=8, delay=5):
    """Publish the container. Retries on 'media not ready' errors.

    Instagram often returns error_subcode 2207027 ("The media is not ready
    for publishing") even after a status poll said FINISHED. Retrying the
    publish call itself is the only reliable fix.
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        r = requests.post(
            f"{GRAPH}/{_ig_user_id()}/media_publish",
            data={"creation_id": creation_id, "access_token": _token()},
            timeout=TIMEOUT,
        )
        if r.ok:
            return r.json()["id"]

        body = r.text[:400]
        last_error = f"Instagram publish {r.status_code}: {body}"

        # Retry only on the specific 'not ready' condition.
        if "2207027" in body or "not ready" in body.lower():
            print(f"  [retry {attempt}/{max_attempts}] media not ready, waiting {delay}s...")
            time.sleep(delay)
            continue

        # Any other error is a hard failure.
        raise RuntimeError(last_error)

    raise RuntimeError(f"Instagram publish failed after {max_attempts} attempts: {last_error}")


def _wait_until_ready(creation_id, max_wait=90, interval=4):
    """Poll container status. Best-effort; publish will retry anyway."""
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
        time.sleep(interval)


def publish_image(image_url, caption):
    cid = _create_container({"image_url": image_url, "caption": caption})
    _wait_until_ready(cid, max_wait=30)
    return _publish_container(cid)


def publish_carousel(slide_urls, caption):
    if not slide_urls:
        raise RuntimeError("No slide URLs supplied")

    children = []
    for url in slide_urls:
        child = _create_container({"image_url": url, "is_carousel_item": "true"})
        children.append(child)

    for child in children:
        _wait_until_ready(child, max_wait=30)

    parent = _create_container({
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
    })
    _wait_until_ready(parent, max_wait=30)
    return _publish_container(parent)


def publish_reel(video_url, caption):
    cid = _create_container({
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
    })
    _wait_until_ready(cid, max_wait=180)
    return _publish_container(cid)
