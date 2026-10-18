"""Generate a weekly performance and strategy report.

Reads the Analytics, Content, and CompetitorInsights tabs.
Writes a plain-text summary to the Strategy tab.

This does not make automatic changes to the bot's behavior. It provides
a human-readable summary the operator can use to adjust strategy.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import gspread

STRATEGY_HEADERS = ["Run Date (UTC)", "Total Posts Tracked", "Top Format", "Top Topic", "Total Engagement", "Competitor Note", "Actionable Recommendation"]


def connect():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(info)
    return gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])


def _int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def main():
    sh = connect()
    
    try:
        analytics_ws = sh.worksheet("Analytics")
        content_ws = sh.worksheet("Content")
    except gspread.WorksheetNotFound:
        print("Required tabs missing. Run the analytics collector first.")
        return

    try:
        comp_ws = sh.worksheet("CompetitorInsights")
        comp_data = comp_ws.get_all_records()
    except gspread.WorksheetNotFound:
        comp_data = []

    analytics = analytics_ws.get_all_records()
    content = content_ws.get_all_records()

    if not analytics:
        print("No analytics data yet.")
        return

    # Map Content ID -> Content Type
    type_map = {str(r.get("Content ID")): str(r.get("Content Type")) for r in content}

    total_engagement = 0
    format_engagement = defaultdict(int)
    topic_engagement = defaultdict(int)
    best_post = {"cid": "", "score": 0}

    for row in analytics:
        cid = str(row.get("Content ID", ""))
        ctype = type_map.get(cid, "unknown")
        topic = str(row.get("Topic", "Unknown"))

        # Sum engagement across FB and IG
        score = (
            _int(row.get("FB Reactions", 0)) + _int(row.get("FB Comments", 0)) + _int(row.get("FB Shares", 0)) +
            _int(row.get("IG Likes", 0)) + _int(row.get("IG Comments", 0)) + _int(row.get("IG Saved", 0)) + _int(row.get("IG Shares", 0))
        )
        
        total_engagement += score
        format_engagement[ctype] += score
        topic_engagement[topic] += score
        
        if score > best_post["score"]:
            best_post = {"cid": cid, "score": score}

    # Determine top format
    top_format = max(format_engagement, key=format_engagement.get) if format_engagement else "N/A"
    # Determine top topic
    top_topic = max(topic_engagement, key=topic_engagement.get) if topic_engagement else "N/A"

    # Look at competitors
    comp_note = "No competitor data found."
    if comp_data:
        # Just take the most recent run's top keywords
        recent = comp_data[-1]
        top_kw = recent.get("Top Keywords", "")
        comp_note = f"Competitors are currently using keywords: {top_kw}"

    # Generate a recommendation (simple heuristic)
    if total_engagement == 0:
        rec = "Engagement is flat. Focus on stronger hooks and testing Reels."
    elif top_format == "image":
        rec = "Images are performing best. Consider shifting more of your schedule to images."
    elif top_format == "carousel":
        rec = "Carousels are working well. Try to ensure you are doing 3 per week."
    elif top_format == "reel":
        rec = "Reels are winning. Ensure you post 2 per week."
    else:
        rec = "Analyze top topics and lean into them next week."

    if top_topic and top_topic != "Unknown":
        rec += f" The topic '{top_topic[:50]}...' drove the most engagement."

    # Write to Strategy tab
    try:
        strat_ws = sh.worksheet("Strategy")
    except gspread.WorksheetNotFound:
        strat_ws = sh.add_worksheet(title="Strategy", rows=100, cols=len(STRATEGY_HEADERS))
        strat_ws.append_row(STRATEGY_HEADERS)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    strat_ws.append_row([
        now,
        len(analytics),
        top_format,
        top_topic[:150] if top_topic != "N/A" else top_topic,
        total_engagement,
        comp_note[:200],
        rec[:300]
    ], value_input_option="RAW")

    print(f"Weekly report generated.")
    print(f"Total posts: {len(analytics)} | Total engagement: {total_engagement}")
    print(f"Top format: {top_format}")
    print(f"Recommendation: {rec}")


if __name__ == "__main__":
    main()
