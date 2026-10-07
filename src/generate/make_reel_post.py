import shutil
from datetime import datetime, timezone

import gspread

from generate.carousel_copy import write_carousel
from generate.make_carousel_post import candidates
from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from media.build_video import build_video, probe
from media.render_reel import render_scenes
from research.fetch_news import load_yaml

MIN_SECONDS = 3
MAX_SECONDS = 90


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
    reel_count = sum(1 for t in types if t == "reel")

    used = set(used_ids)
    for i in used_ids:
        if i.startswith("REEL-"):
            used.add("IMG-" + i[5:])

    story, copy = None, None
    for r in candidates(research_ws, used, max_age)[:5]:
        text = get_story_text(r["Source URLs"], feeds)
        if len(text) < 80:
            print(f"Skipping (not enough source text): {r['Headline']}")
            continue
        story = r
        copy = write_carousel(r["Headline"], r["Outlets"], text)
        break
    if not story:
        print("No suitable fresh verified story. Run 'Research News' first.")
        return

    cid = "REEL-" + str(story["Cluster ID"])
    outlets = story["Outlets"]
    print(f"Story: {story['Headline']} ({outlets})")

    scenes, style, pace, folder = render_scenes(
        cid, copy, outlets, int(story["Source Count"]), reel_count
    )
    final = f"output/reels/{cid}.mp4"
    build_video(scenes, folder, final)
    shutil.rmtree(folder, ignore_errors=True)

    info = probe(final)
    video = next(s for s in info["streams"] if s.get("width"))
    duration = float(video["duration"])
    width, height = video["width"], video["height"]
    if not (MIN_SECONDS <= duration <= MAX_SECONDS) or (width, height) != (1080, 1920):
        raise RuntimeError(f"Video failed checks: {duration}s, {width}x{height}")

    caption = (
        f"{copy['caption']}\n\n{copy['cta']}\n\nSources: {outlets}\n\n"
        + " ".join(copy["hashtags"])
    )
    description = (
        f"Vertical news video from The Daily Precinct. {copy['cover_headline']}. "
        f"Reported by {outlets}."
    )
    values = {
        "Content ID": cid,
        "Content Type": "reel",
        "Topic": story["Headline"],
        "Source": outlets,
        "Source URL": story["Source URLs"],
        "Source Publication Date": story["Earliest Published (UTC)"],
        "Research Date": story["Research Timestamp (UTC)"],
        "Creation Date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "Status": "Draft",
        "Caption": caption,
        "Alt Text": description,
        "Creative Format": f"{style}; {pace} pacing; {duration:.0f}s",
        "Validation Result": "pending (Step 11)",
    }
    content_ws.append_row(
        [values.get(h, "") for h in headers], value_input_option="RAW"
    )
    print(f"Video saved: {final} ({duration:.1f}s, {width}x{height}, {style}, {pace} pacing)")
    print(f"Cover headline: {copy['cover_headline']}")
    print("REEL OK")


if __name__ == "__main__":
    main()
