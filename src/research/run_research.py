import json
import os
from datetime import datetime, timezone

import gspread

from research.fetch_news import fetch_all, load_yaml
from verify.cluster import cluster_items, verify_clusters

HEADERS = [
    "Cluster ID",
    "Research Timestamp (UTC)",
    "Status",
    "Headline",
    "Source Count",
    "Outlets",
    "Source URLs",
    "Earliest Published (UTC)",
    "Latest Published (UTC)",
    "Verification Rule",
]


def write_to_sheet(verified, min_sources, max_age):
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(info)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        ws = sh.worksheet("Research")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Research", rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)
    existing = set(ws.col_values(1))
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rule = f"{min_sources}+ independent outlets, max age {max_age}h"
    rows = []
    for r in verified:
        if r["cluster_id"] in existing:
            continue
        rows.append(
            [
                r["cluster_id"],
                ts,
                r["status"],
                r["headline"],
                r["source_count"],
                r["outlets"],
                r["urls"],
                r["earliest"],
                r["latest"],
                rule,
            ]
        )
    if rows:
        ws.append_rows(rows, value_input_option="RAW")
    print(f"Sheet rows added: {len(rows)} (duplicates skipped)")


def main():
    feeds = load_yaml("config/sources.yaml")["feeds"]
    settings = load_yaml("config/settings.yaml") or {}
    ver = settings.get("verification", {})
    min_sources = ver.get("min_independent_sources", 2)
    max_age = ver.get("max_source_age_hours", 48)

    items, status = fetch_all(feeds, max_age)
    print("FEED STATUS:")
    for name, msg in status.items():
        print(f"  {name}: {msg}")
    print(f"Fresh items (last {max_age}h): {len(items)}")

    results = verify_clusters(cluster_items(items), min_sources)
    verified = [r for r in results if r["status"] == "Verified"]
    rejected = [r for r in results if r["status"] == "Rejected"]
    print(
        f"Stories: {len(results)} | Verified: {len(verified)} | "
        f"Rejected (single source): {len(rejected)}"
    )
    for r in verified[:10]:
        print(f"  VERIFIED ({r['source_count']} outlets): {r['headline']}")

    write_to_sheet(verified, min_sources, max_age)
    print("RESEARCH OK")


if __name__ == "__main__":
    main()
