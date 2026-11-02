import shutil
from datetime import datetime, timezone
import gspread

from generate.reel_copy import write_reel_script
from generate.make_carousel_post import candidates
from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from media.build_video import build_video, probe
from media.render_reel import render_scenes
from media.voiceover import generate_voiceover
from media.audio_manager import get_track_for_category
from media.fetch_image import get_image_for_headline, get_image_for_slide
from research.fetch_news import load_yaml

def main():
    settings = load_yaml("config/settings.yaml") or {}
    max_age = settings.get("verification", {}).get("max_source_age_hours", 48)
    feeds = load_yaml("config/sources.yaml")["feeds"]

    sh = connect()
    try:
        research_ws = sh.worksheet("Research")
    except gspread.WorksheetNotFound:
        return
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    used_ids = set(content_ws.col_values(headers.index("Content ID") + 1))

    story, script = None, None
    for r in candidates(research_ws, used_ids, max_age)[:5]:
        text = get_story_text(r["Source URLs"], feeds)
        if len(text) < 80: continue
        try:
            script = write_reel_script(r["Headline"], r["Outlets"], text)
            story = r
            break
        except Exception as e:
            print(f"Skipping story: {e}")

    if not story:
        print("No suitable story.")
        return

    cid = "REEL-" + str(story["Cluster ID"])
    outlets = story["Outlets"]
    print(f"Story: {story['Headline']} | Category: {script['category']}")

    # 1. Generate Voiceover
    vo_path, total_duration = generate_voiceover(script["voiceover_script"], cid)

    # 2. Fetch 7 Images for the 7 Scenes
    print("Fetching 7 scene images...")
    scene_texts = [
        script["scene_1_hook"], script["scene_2_context"], 
        script["scene_3_main"], script["scene_4_details"], 
        script["scene_5_impact"], script["scene_6_next"], script["scene_7_cta"]
    ]
    
    main_img = get_image_for_headline(story["Headline"], story["Source URLs"]) or ""
    image_urls = [main_img]
    
    # Get unique images for scenes 2-6
    for text in scene_texts[1:6]:
        img = get_image_for_slide(text)
        image_urls.append(img or main_img)
        
    # Scene 7 is the CTA (reuse main image or use a generic brand image)
    image_urls.append(main_img)

    # 3. Fetch Music based on Category
    music_path = get_track_for_category(script["category"])

    # 4. Render Frames
    scenes, folder = render_scenes(cid, script, image_urls, total_duration)
    
    # 5. Build Final Video
    final = f"output/reels/{cid}.mp4"
    build_video(scenes, folder, final, vo_path, music_path)
    shutil.rmtree(folder, ignore_errors=True)

    # 6. Validation
    info = probe(final)
    video = next(s for s in info["streams"] if s.get("width"))
    duration = float(video["duration"])
    if duration < 50 or duration > 65:
        raise RuntimeError(f"Video failed length check: {duration}s")

    # 7. Sheet Update
    caption = (
        f"📌 {script['category'].upper()}\n\n"
        f"{script['caption']}\n\n"
        f"💡 Why it matters:\n{script['why_it_matters']}\n\n"
        f"Follow for clear updates on the stories shaping America.\n\n"
        f"Sources: {outlets}\n\n"
        + " ".join(script["hashtags"])
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
        "Alt Text": f"Vertical video. {script['caption']}",
        "Creative Format": f"elite_editorial; {duration:.1f}s; {script['category']} Audio",
        "Validation Result": "pending",
    }
    content_ws.append_row([values.get(h, "") for h in headers], value_input_option="RAW")
    print(f"REEL OK: {final} ({duration:.1f}s)")

if __name__ == "__main__":
    main()
