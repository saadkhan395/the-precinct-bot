"""Collect Facebook and Instagram metrics for published posts.

Reads the Content tab. For every row with Status == "Published",
fetches engagement metrics from both platforms and writes one row per
Content ID to the Analytics tab.

Idempotent: re-running overwrites the same row instead of duplicating.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import gspread
import requests

GRAPH_FB = "https://graph.facebook.com/v26.0"
GRAPH_IG = "https://graph.instagram.com/v26.0"
TIMEOUT = 45

ANALYTICS_HEADERS = [
    "Content ID",
    "Content Type",
    "Topic",
    "Published Time",
    "Last Collected",
    "FB Post ID",
    "FB Reactions",
    "FB Comments",
    "FB Shares",
    "IG Media ID",
    "IG Likes",
    "IG Comments",
    "IG Reach",
    "IG Impressions",
    "IG Saved",
    "IG Shares",
    "IG Plays",
]


def connect():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(info)
    return gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])


def get_analytics_ws(sh):
    try:
        ws = sh.worksheet("Analytics")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Analytics", rows=2000, cols=len(ANALYTICS_HEADERS))
        ws.append_row(ANALYTICS_HEADERS)
    return ws


def _get_fb_metrics(post_id: str, token: str) -> dict:
    """Fetch FB post metrics. Returns dict with any metrics that succeeded."""
    out = {}
    try:
        r = requests.get(
            f"{GRAPH_FB}/{post_id}",
            params={
                "fields": "shares,comments.summary(true),reactions.summary(true)",
                "access_token": token,
            },
            timeout=TIMEOUT,
        )
        if r.ok:
            data = r.json()
            out["FB Reactions"] = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
            out["FB Comments"] = data.get("comments", {}).get("summary", {}).get("total_count", 0)
            out["FB Shares"] = data.get("shares", {}).get("count", 0)
    except Exception as e:
        print(f"  FB metrics error: {e}")
    return out


def _get_ig_metrics(media_id: str, token: str) -> dict:
    """Fetch IG metrics for an image/carousel/reel."""
    out = {}
    try:
        r = requests.get(
            f"{GRAPH_IG}/{media_id}",
            params={
                "fields": "like_count,comments_count,media_type",
                "access_token": token,
            },
            timeout=TIMEOUT,
        )
        if r.ok:
            data = r.json()
            out["IG Likes"] = data.get("like_count", 0)
            out["IG Comments"] = data.get("comments_count", 0)
    except Exception as e:
        print(f"  IG basic metrics error: {e}")

    # Insights: reach, impressions, saved, shares (and plays for video)
    metrics = ["reach", "impressions", "saved", "shares"]
    try:
        r = requests.get(
            f"{GRAPH_IG}/{media_id}/insights",
            params={"metric": ",".join(metrics), "access_token": token},
            timeout=TIMEOUT,
        )
        if r.ok:
            for entry in r.json().get("data", []):
                name = entry.get("name", "")
                value = entry.get("values", [{}])[0].get("value", 0)
                key = {
                    "reach": "IG Reach",
                    "impressions": "IG Impressions",
                    "saved": "IG Saved",
                    "shares": "IG Shares",
                }.get(name)
                if key:
                    out[key] = value
    except Exception as e:
        print(f"  IG insights error: {e}")

    # Plays for reels
    try:
        r = requests.get(
            f"{GRAPH_IG}/{media_id}/insights",
            params={"metric": "plays", "access_token": token},
            timeout=TIMEOUT,
        )
        if r.ok:
            for entry in r.json().get("data", []):
                if entry.get("name") == "plays":
                    out["IG Plays"] = entry.get("values", [{}])[0].get("value", 0)
    except Exception:
        pass

    return out


def main():
    sh = connect()
    content_ws = sh.worksheet("Content")
    analytics_ws = get_analytics_ws(sh)

    fb_token = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not fb_token or not ig_token:
        raise RuntimeError("Missing META_PAGE_ACCESS_TOKEN or INSTAGRAM_ACCESS_TOKEN")

    rows = content_ws.get_all_records()
    existing = analytics_ws.get_all_records()
    existing_by_id = {str(r.get("Content ID", "")).strip(): i + 2 for i, r in enumerate(existing)}
    headers_an = analytics_ws.row_values(1)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    collected = 0

    for row in rows:
        if str(row.get("Status", "")).strip() != "Published":
            continue
        cid = str(row.get("Content ID", "")).strip()
        if not cid:
            continue

        fb_id = str(row.get("Facebook Post ID", "")).strip()
        ig_id = str(row.get("Instagram Media ID", "")).strip()

        print(f"\n=== {cid} ===")
        metrics = {}
        if fb_id:
            metrics.update(_get_fb_metrics(fb_id, fb_token))
        if ig_id:
            metrics.update(_get_ig_metrics(ig_id, ig_token))

        values = {
            "Content ID": cid,
            "Content Type": str(row.get("Content Type", "")),
            "Topic": str(row.get("Topic", ""))[:200],
            "Published Time": str(row.get("Published Time", "")),
            "Last Collected": now,
            "FB Post ID": fb_id,
            "IG Media ID": ig_id,
        }
        values.update(metrics)

        row_values = [values.get(h, "") for h in headers_an]

        if cid in existing_by_id:
            sheet_row = existing_by_id[cid]
            for col_idx, val in enumerate(row_values, start=1):
                analytics_ws.update_cell(sheet_row, col_idx, val)
        else:
            analytics_ws.append_row(row_values, value_input_option="RAW")
        collected += 1
        print(f"  Collected: {metrics}")

    print(f"\nDone. Collected metrics for {collected} published item(s).")


if __name__ == "__main__":
    main()
