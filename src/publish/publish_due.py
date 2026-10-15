"""Publish due content to Facebook and Instagram independently.

Reads the Content tab. For each row where:
  - Status == "Scheduled"
  - Scheduled Time is in the past
  - Neither Facebook Post ID nor Instagram Media ID is set

...it attempts to publish to each platform. Facebook and Instagram are
published independently: one may succeed while the other fails. The row is
only marked "Published" when BOTH have IDs recorded.

On partial failure, IDs already obtained are stored so subsequent runs do
not double-post on the platform that already succeeded.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import gspread

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generate.make_image_post import connect, get_content_ws  # noqa: E402
from publish import facebook, instagram  # noqa: E402


MAX_PER_RUN = 5


def _get(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _parse_time(raw: str) -> datetime | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _media_paths(content_id: str, content_type: str):
    """Return absolute paths for the media attached to this row."""
    root = Path(__file__).resolve().parents[2]
    if content_type == "image":
        p = root / "output/images" / f"{content_id}.jpg"
        return [p] if p.is_file() else []
    if content_type == "carousel":
        folder = root / "output/carousels" / content_id
        if not folder.is_dir():
            return []
        slides = sorted(
            [p for p in folder.glob("slide-*.jpg")],
            key=lambda p: int(p.stem.split("-")[1]),
        )
        return slides
    if content_type == "reel":
        p = root / "output/reels" / f"{content_id}.mp4"
        return [p] if p.is_file() else []
    return []


def _relative(path: Path) -> str:
    root = Path(__file__).resolve().parents[2]
    return str(path.relative_to(root)).replace("\\", "/")


def _set_cell(ws, col, sheet_row, name, value):
    if name in col:
        ws.update_cell(sheet_row, col[name], value)


def main():
    sh = connect()
    try:
        content_ws = get_content_ws(sh)
    except Exception as e:
        print(f"FATAL: cannot open Content tab: {e}")
        return

    headers = content_ws.row_values(1)
    col = {h: i + 1 for i, h in enumerate(headers)}
    rows = content_ws.get_all_records()

    now = datetime.now(timezone.utc)
    due = []
    for idx, row in enumerate(rows, start=2):
        if _get(row.get("Status")) != "Scheduled":
            continue
        when = _parse_time(_get(row.get("Scheduled Time")))
        if when is None or when > now:
            continue
        fb_id = _get(row.get("Facebook Post ID"))
        ig_id = _get(row.get("Instagram Media ID"))
        if fb_id and ig_id:
            # Both already done; fix status and skip.
            _set_cell(content_ws, col, idx, "Status", "Published")
            continue
        due.append((idx, row, fb_id, ig_id))

    if not due:
        print("No due content to publish.")
        return

    print(f"Found {len(due)} due item(s).")

    published = 0
    for sheet_row, row, existing_fb, existing_ig in due[:MAX_PER_RUN]:
        cid = _get(row.get("Content ID"))
        ctype = _get(row.get("Content Type"))
        caption = _get(row.get("Caption"))
        print(f"\n=== {cid} ({ctype}) ===")

        paths = _media_paths(cid, ctype)
        if not paths:
            print(f"SKIP: media missing for {cid}")
            _set_cell(content_ws, col, sheet_row, "Error Message", "Media missing at publish time")
            continue

        # --- Facebook (independent) ---
        fb_result = existing_fb
        if not existing_fb:
            try:
                if ctype == "image":
                    fb_result = facebook.publish_image(paths[0], caption)
                elif ctype == "carousel":
                    fb_result = facebook.publish_carousel(paths, caption)
                elif ctype == "reel":
                    fb_result = facebook.publish_reel(paths[0], caption)
                print(f"Facebook OK: {fb_result}")
                _set_cell(content_ws, col, sheet_row, "Facebook Post ID", fb_result)
            except Exception as e:
                print(f"Facebook FAILED: {e}")
                _set_cell(content_ws, col, sheet_row, "Error Message", f"FB: {str(e)[:300]}")
        else:
            print(f"Facebook already posted: {existing_fb}")

        # --- Instagram (independent) ---
        ig_result = existing_ig
        if not existing_ig:
            try:
                urls = [instagram.media_url(_relative(p)) for p in paths]
                if ctype == "image":
                    ig_result = instagram.publish_image(urls[0], caption)
                elif ctype == "carousel":
                    ig_result = instagram.publish_carousel(urls, caption)
                elif ctype == "reel":
                    ig_result = instagram.publish_reel(urls[0], caption)
                print(f"Instagram OK: {ig_result}")
                _set_cell(content_ws, col, sheet_row, "Instagram Media ID", ig_result)
            except Exception as e:
                print(f"Instagram FAILED: {e}")
                _set_cell(content_ws, col, sheet_row, "Error Message", f"IG: {str(e)[:300]}")
        else:
            print(f"Instagram already posted: {existing_ig}")

        # --- Mark published only if BOTH succeeded ---
        if fb_result and ig_result:
            _set_cell(content_ws, col, sheet_row, "Status", "Published")
            _set_cell(
                content_ws,
                col,
                sheet_row,
                "Published Time",
                now.isoformat(timespec="seconds"),
            )
            _set_cell(content_ws, col, sheet_row, "Error Message", "")
            published += 1
            print(f"PUBLISHED: {cid}")
        else:
            print(f"PARTIAL: {cid} (FB={bool(fb_result)}, IG={bool(ig_result)})")

    print(f"\nDone. Fully published: {published}/{len(due[:MAX_PER_RUN])}")


if __name__ == "__main__":
    main()