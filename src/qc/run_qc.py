from datetime import datetime, timezone

import gspread

from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from qc.ai_review import review, to_checks
from qc.checks import (
    check_duplicate,
    check_media,
    check_sources,
    check_text,
    load_rules,
)
from research.fetch_news import load_yaml

MAX_PER_RUN = 10
REVIEW_HEADERS = [
    "Content ID",
    "Reason Rejected",
    "Failed Check",
    "Created At",
    "Reviewer Decision",
    "Reviewed At",
]


def get_review_ws(sh):
    try:
        ws = sh.worksheet("ReviewQueue")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="ReviewQueue", rows=1000, cols=len(REVIEW_HEADERS))
    if not ws.row_values(1):
        ws.append_row(REVIEW_HEADERS)
    return ws


def main():
    rules = load_rules("config/compliance_rules.yaml")
    settings = load_yaml("config/settings.yaml") or {}
    ver = settings.get("verification", {})
    min_sources = ver.get("min_independent_sources", 2)
    max_age = ver.get("max_source_age_hours", 48)
    feeds = load_yaml("config/sources.yaml")["feeds"]

    sh = connect()
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    col = {h: i + 1 for i, h in enumerate(headers)}
    rows = content_ws.get_all_records()
    review_ws = None
    done = 0

    for idx, row in enumerate(rows):
        if str(row.get("Status")) != "Draft":
            continue
        if done >= MAX_PER_RUN:
            break
        done += 1
        cid = row["Content ID"]
        sheet_row = idx + 2

        checks = []
        checks += check_text(row, rules)
        checks += check_sources(row, min_sources, max_age)
        checks += check_media(row, rules)
        checks.append(check_duplicate(idx, rows))

        text = get_story_text(row.get("Source URL", ""), feeds)
        checks += to_checks(
            review(row.get("Topic", ""), text, row.get("Caption", ""), row.get("Alt Text", ""))
        )

        failed = [c for c in checks if not c["ok"]]
        if failed:
            reasons = "; ".join(f"{c['check']}: {c['detail']}".strip(": ") for c in failed)
            content_ws.update_cell(sheet_row, col["Status"], "Rejected")
            content_ws.update_cell(sheet_row, col["Validation Result"], f"FAIL ({len(failed)})")
            content_ws.update_cell(sheet_row, col["Error Message"], reasons[:900])
            if review_ws is None:
                review_ws = get_review_ws(sh)
            review_ws.append_row(
                [
                    cid,
                    reasons[:900],
                    ", ".join(c["check"] for c in failed),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "",
                    "",
                ],
                value_input_option="RAW",
            )
            print(f"FAIL {cid}: {', '.join(c['check'] for c in failed)}")
        else:
            content_ws.update_cell(sheet_row, col["Status"], "Approved")
            content_ws.update_cell(
                sheet_row, col["Validation Result"], f"PASS ({len(checks)} checks)"
            )
            content_ws.update_cell(sheet_row, col["Error Message"], "")
            print(f"PASS {cid}: {len(checks)} checks")

    if done == 0:
        print("No Draft items to check.")
    print("QC OK")


if __name__ == "__main__":
    main()
