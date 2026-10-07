import json
import os
from datetime import datetime, timezone

import gspread

from competitors.feed_patterns import analyze
from research.fetch_news import fetch_all, load_yaml

HEADERS = [
    "Run Date (UTC)",
    "Outlet",
    "Posts Analysed",
    "Avg Headline Words",
    "% Questions",
    "% With Numbers",
    "% With Quotes",
    "% With Colon",
    "Top Keywords",
    "Peak Posting Hours (ET)",
    "Posts Per Day",
]


def write_to_sheet(rows):
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        ws = sh.worksheet("CompetitorInsights")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="CompetitorInsights", rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today in set(ws.col_values(1)):
        print(f"Already analysed today ({today}); nothing added.")
        return
    ws.append_rows([[today] + r for r in rows], value_input_option="RAW")
    print(f"Rows added: {len(rows)}")


def main():
    feeds = load_yaml("config/sources.yaml")["feeds"]
    items, status = fetch_all(feeds, 168)
    print("FEED STATUS:")
    for name, msg in status.items():
        print(f"  {name}: {msg}")
    print(f"Items analysed (last 7 days): {len(items)}")
    if not items:
        print("No items found. Stopping.")
        return
    rows = analyze(items)
    for r in rows:
        print(f"  {r[0]}: {r[1]} posts | keywords: {r[7]}")
    write_to_sheet(rows)
    print("COMPETITORS OK")


if __name__ == "__main__":
    main()
