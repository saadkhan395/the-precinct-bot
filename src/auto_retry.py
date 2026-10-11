"""Retry rejected drafts using source-grounded copy regeneration.

This module only retries text/AI-review failures. It deliberately does not
auto-retry missing/corrupt media or source/freshness/duplicate failures,
because those require rebuilding media or selecting a different story.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import gspread

from generate.carousel_copy import write_carousel
from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from generate.groq_client import write_copy
from research.fetch_news import load_yaml

MAX_ATTEMPTS = 3
RETRYABLE = {"factual_support", "spelling_grammar", "neutral_tone", "policy_flags"}
RETRY_HEADERS = ["Retry Attempts", "Retry Last Attempt", "Retry Notes"]

def ensure_columns(ws):
    headers = ws.row_values(1)
    for name in RETRY_HEADERS:
        if name not in headers:
            headers.append(name)
            ws.update_cell(1, len(headers), name)
    return {name: headers.index(name) + 1 for name in headers}

def main():
    settings = load_yaml("config/settings.yaml") or {}
    feeds = (load_yaml("config/sources.yaml") or {}).get("feeds", [])
    sh = connect()
    ws = get_content_ws(sh)
    col = ensure_columns(ws)
    rows = ws.get_all_records()
    try:
        research = sh.worksheet("Research").get_all_records()
    except gspread.WorksheetNotFound:
        raise RuntimeError("Research worksheet is missing; cannot regenerate from sources.")

    research_by_id = {str(r.get("Cluster ID", "")).strip(): r for r in research}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    processed = 0

    for sheet_row, row in enumerate(rows, start=2):
        if str(row.get("Status", "")).strip() != "Rejected":
            continue
        failed = str(row.get("Error Message", "") or row.get("Validation Result", ""))
        failed_names = {x.strip().split(":", 1)[0] for x in failed.split(";") if x.strip()}
        # Retry only failures that can be fixed by rewriting copy.
        if not (failed_names & RETRYABLE):
            continue
        try:
            attempts = int(row.get("Retry Attempts") or 0)
        except (TypeError, ValueError):
            attempts = 0
        if attempts >= MAX_ATTEMPTS:
            ws.update_cell(sheet_row, col["Retry Notes"], "Retry limit reached; manual review required.")
            continue

        cid = str(row.get("Content ID", "")).strip()
        cluster_id = cid.split("-", 1)[1] if "-" in cid else ""
        story = research_by_id.get(cluster_id)
        if not story or str(story.get("Status", "")).strip() != "Verified":
            ws.update_cell(sheet_row, col["Retry Notes"], "No matching Verified Research row; manual review required.")
            continue

        source_text = get_story_text(str(row.get("Source URL", "")), feeds)
        if len(source_text.strip()) < 80:
            ws.update_cell(sheet_row, col["Retry Notes"], "Insufficient source text to regenerate safely.")
            continue

        feedback = (
            "Fix these QC failures without adding facts: "
            + "; ".join(sorted(failed_names & RETRYABLE))
            + ". Preserve neutral, non-partisan tone. Use only the supplied source text."
        )
        kind = str(row.get("Content Type", "")).strip().lower()
        outlets = str(row.get("Source", "") or story.get("Outlets", ""))
        headline = str(row.get("Topic", "") or story.get("Headline", ""))

        # Ask the existing generator for source-grounded replacement copy.
        if kind == "image":
            copy = write_copy(headline + "\nQC feedback: " + feedback, outlets)
            caption = f"{copy['caption']}\n\n{copy['cta']}\n\nSources: {outlets}\n\n" + " ".join(copy["hashtags"])
            alt = f"News graphic from The Daily Precinct. Headline: {copy['headline']}. Reported by {outlets}."
            # Visual text is not regenerated here; only accept if the existing
            # graphic's headline still represents the same source story.
        elif kind in {"carousel", "reel"}:
            copy = write_carousel(headline + "\nQC feedback: " + feedback, outlets, source_text)
            caption = f"{copy['caption']}\n\n{copy['cta']}\n\nSources: {outlets}\n\n" + " ".join(copy["hashtags"])
            if kind == "carousel":
                alt_parts = [f"Slide 1: {copy['cover_headline']}"]
                for i, slide in enumerate(copy["slides"], start=2):
                    alt_parts.append(f"Slide {i}: {slide['title']}. " + " ".join(slide["points"]))
                alt = " | ".join(alt_parts)
            else:
                alt = f"Vertical news video from The Daily Precinct. {copy['cover_headline']}. Reported by {outlets}."
        else:
            ws.update_cell(sheet_row, col["Retry Notes"], f"Unsupported content type: {kind}")
            continue

        # Preserve existing media and source metadata; QC reruns before approval.
        # Do not schedule automatically. Status returns to Draft for the normal QC gate.
        headers = ws.row_values(1)
        if "Caption" in headers:
            ws.update_cell(sheet_row, headers.index("Caption") + 1, caption)
        if "Alt Text" in headers:
            ws.update_cell(sheet_row, headers.index("Alt Text") + 1, alt)
        if "Status" in headers:
            ws.update_cell(sheet_row, headers.index("Status") + 1, "Draft")
        if "Validation Result" in headers:
            ws.update_cell(sheet_row, headers.index("Validation Result") + 1, "Retry pending QC")
        ws.update_cell(sheet_row, col["Retry Attempts"], attempts + 1)
        ws.update_cell(sheet_row, col["Retry Last Attempt"], now)
        ws.update_cell(sheet_row, col["Retry Notes"], "Regenerated copy; queued for QC. Verify visual text/media alignment.")
        processed += 1

    print(f"Automatic retry finished. Regenerated {processed} rejected item(s).")

if __name__ == "__main__":
    main()
