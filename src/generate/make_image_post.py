import json
import os
from datetime import datetime, timedelta, timezone

import gspread

from generate.groq_client import write_copy
from media.render_image import render_post
from media.fetch_image import get_image_for_headline
from research.fetch_news import load_yaml

CONTENT_HEADERS = [
    "Content ID", "Content Type", "Topic", "Source", "Source URL", 
    "Source Publication Date", "Research Date", "Creation Date", "Status", 
    "Scheduled Time", "Published Time", "Facebook Post ID", "Instagram Media ID", 
    "Caption", "Alt Text", "Creative Format", "Competitor Inspiration Category", 
    "Validation Result", "Error Message",
]

def connect():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gc = gspread.service_account_from_dict(info)
    return gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])

def get_content_ws(sh):
    try:
        ws = sh.worksheet("Content")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Content", rows=1000, cols=len(CONTENT_HEADERS))
    if not ws.row_values(1):
        ws.append_row(CONTENT_HEADERS)
    return ws

def pick_story(research_ws, used_ids, max_age_hours):
    now = datetime.now(timezone.utc)
    for r in reversed(research_ws.get_all_records()):
        if r.get("Status") != "Verified":
            continue
        cid = "IMG-" + str(r["Cluster ID"])
        if any(f"{p}-{cid[4:]}" in used_ids for p in ("IMG", "CAR", "REEL")):
            continue
        try:
            earliest = datetime.fromisoformat(str(r["Earliest Published (UTC)"]))
        except Exception:
            continue
        if now - earliest > timedelta(hours=max_age_hours):
            continue
        return r, cid
    return None, None

def main():
    settings = load_yaml("config/settings.yaml") or {}
    max_age = settings.get("verification", {}).get("max_source_age_hours", 48)

    sh = connect()
    try:
        research_ws = sh.worksheet("Research")
    except gspread.WorksheetNotFound:
        print("No Research tab yet. Run 'Research News' first.")
        return
        
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    existing_ids = set(content_ws.col_values(headers.index("Content ID") + 1))
    types = content_ws.col_values(headers.index("Content Type") + 1)
    image_count = sum(1 for t in types if t == "image")

    story, cid = pick_story(research_ws, existing_ids, max_age)
    if not story:
        print("No new fresh verified story. Run 'Research News' first.")
        return

    outlets = story["Outlets"]
    source_urls = story["Source URLs"]
    print(f"Story: {story['Headline']} ({outlets})")
    
    copy = write_copy(story["Headline"], outlets)
    
    print("Fetching background image...")
    image_url = get_image_for_headline(story["Headline"], source_urls)
    
    path, style = render_post(
        cid, copy["hook"], copy["headline"], outlets, int(story["Source Count"]), image_count, image_url
    )

    caption = (
        f"📌 {copy['category'].upper()}\n\n"
        f"{copy['caption']}\n\n"
        f"💡 Why it matters:\n{copy['why_it_matters']}\n\n"
        f"{copy['cta']}\n\n"
        f"Sources: {outlets}\n\n"
        + " ".join(copy["hashtags"])
    )
    
    alt = f"{copy['category']} graphic from The Daily Precinct. Headline: {copy['headline']}. Why it matters: {copy['why_it_matters']}. Reported by {outlets}."
    
    values = {
        "Content ID": cid,
        "Content Type": "image",
        "Topic": story["Headline"],
        "Source": outlets,
        "Source URL": source_urls,
        "Source Publication Date": story["Earliest Published (UTC)"],
        "Research Date": story["Research Timestamp (UTC)"],
        "Creation Date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "Status": "Draft",
        "Caption": caption,
        "Alt Text": alt,
        "Creative Format": style,
        "Validation Result": "pending",
    }
    content_ws.append_row([values.get(h, "") for h in headers], value_input_option="RAW")
    
    print(f"Image saved: {path} (style: {style})")
    print("IMAGE POST OK")

if __name__ == "__main__":
    main()
