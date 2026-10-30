from datetime import datetime, timedelta, timezone

import gspread

from generate.carousel_copy import write_carousel
from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from media.render_carousel import render_carousel
from media.fetch_image import get_image_for_headline, get_image_for_slide
from research.fetch_news import load_yaml

def candidates(research_ws, used_ids, max_age_hours):
    now = datetime.now(timezone.utc)
    found = []
    for r in research_ws.get_all_records():
        if r.get("Status") != "Verified":
            continue
        cid = str(r["Cluster ID"])
        if any(f"{p}-{cid}" in used_ids for p in ("IMG", "CAR", "REEL")):
            continue
        try:
            earliest = datetime.fromisoformat(str(r["Earliest Published (UTC)"]))
        except Exception:
            continue
        if now - earliest > timedelta(hours=max_age_hours):
            continue
        found.append(r)
    found.sort(
        key=lambda r: (int(r["Source Count"]), str(r["Earliest Published (UTC)"])),
        reverse=True,
    )
    return found

def main():
    settings = load_yaml("config/settings.yaml") or {}
    max_age = settings.get("verification", {}).get("max_source_age_hours", 48)
    feeds = load_yaml("config/sources.yaml")["feeds"]

    sh = connect()
    try:
        research_ws = sh.worksheet("Research")
    except gspread.WorksheetNotFound:
        print("No Research tab yet. Run 'Research News' first.")
        return
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    used_ids = set(content_ws.col_values(headers.index("Content ID") + 1))
    types = content_ws.col_values(headers.index("Content Type") + 1)
    carousel_count = sum(1 for t in types if t == "carousel")

    story, copy, text = None, None, ""
    for r in candidates(research_ws, used_ids, max_age)[:5]:
        text = get_story_text(r["Source URLs"], feeds)
        if len(text) < 80:
            print(f"Skipping (not enough source text): {r['Headline']}")
            continue
        
        try:
            print(f"Generating copy for: {r['Headline']}...")
            copy = write_carousel(r["Headline"], r["Outlets"], text)
            story = r
            break
        except Exception as e:
            print(f"Skipping story due to AI safety block: {e}")
            continue

    if not story:
        print("No suitable fresh verified story passed AI safety checks.")
        return

    cid = "CAR-" + str(story["Cluster ID"])
    outlets = story["Outlets"]
    source_count = int(story["Source Count"])
    print(f"Story selected: {story['Headline']} ({outlets})")

    print("Fetching real images for carousel slides...")
    image_urls = []
    
    cover_img = get_image_for_headline(story["Headline"], story["Source URLs"])
    image_urls.append(cover_img or "")
    
    s1_text = copy["slides"][0]["points"][0] if copy["slides"] else story["Headline"]
    s1_img = get_image_for_slide(s1_text)
    image_urls.append(s1_img or cover_img or "")
    
    s2_text = copy["slides"][1]["points"][0] if len(copy["slides"]) > 1 else story["Headline"]
    s2_img = get_image_for_slide(s2_text)
    image_urls.append(s2_img or cover_img or "")
    
    image_urls.append(cover_img or "")

    paths, style = render_carousel(
        cid, copy, outlets, source_count, carousel_count, image_urls
    )

    # THIS IS THE BLOCK THAT WAS BROKEN:
    caption = (
        f"📌 {copy['category'].upper()}\n\n"
        f"{copy['caption']}\n\n"
        f"💡 Why it matters:\n{copy['why_it_matters']}\n\n"
        f"{copy['cta']}\n\n"
        f"Sources: {outlets}\n\n"
        + " ".join(copy["hashtags"])
    )

    alts = [f"Slide 1: {copy['cover_headline']}"]
    for i, s in enumerate(copy["slides"], start=2):
        alts.append(f"Slide {i}: {s['title']}. " + " ".join(s["points"]))
    alts.append(f"Slide {len(alts) + 1}: Outlets reporting this story: {outlets}.")
    alts.append(f"Slide {len(alts) + 1}: Follow The Daily Precinct for more.")

    values = {
        "Content ID": cid,
        "Content Type": "carousel",
        "Topic": story["Headline"],
        "Source": outlets,
        "Source URL": story["Source URLs"],
        "Source Publication Date": story["Earliest Published (UTC)"],
        "Research Date": story["Research Timestamp (UTC)"],
        "Creation Date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "Status": "Draft",
        "Caption": caption,
        "Alt Text": " | ".join(alts),
        "Creative Format": f"{style}; {len(paths)} slides",
        "Validation Result": "pending",
    }
    content_ws.append_row(
        [values.get(h, "") for h in headers], value_input_option="RAW"
    )
    print(f"Slides saved: {len(paths)} in output/carousels/{cid} (style: {style})")
    print("CAROUSEL OK")

if __name__ == "__main__":
    main()
