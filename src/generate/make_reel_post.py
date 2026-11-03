import shutil
from datetime import datetime, timezone
import gspread

from generate.reel_copy import write_reel_script
from generate.make_carousel_post import candidates
from generate.make_image_post import connect, get_content_ws
from generate.story_text import get_story_text
from media.build_video import build_video
from media.render_reel import render_scenes
from media.voiceover import generate_voiceover
from media.audio_manager import get_track_for_category
from media.fetch_image import get_image_for_headline, get_image_for_slide
from research.fetch_news import load_yaml

def main():
    settings = load_yaml("config/settings.yaml") or {}
    sh = connect()
    content_ws = get_content_ws(sh)
    headers = content_ws.row_values(1)
    used_ids = set(content_ws.col_values(headers.index("Content ID") + 1))

    story, script = None, None
    for r in candidates(sh.worksheet("Research"), used_ids, settings.get("verification", {}).get("max_source_age_hours", 48))[:5]:
        text = get_story_text(r["Source URLs"], load_yaml("config/sources.yaml")["feeds"])
        if len(text) < 80: 
            continue
        try:
            script = write_reel_script(r["Headline"], r["Outlets"], text)
            story = r
            break
        except Exception as e:
            print(f"Skipping story: {e}")

    if not story or not script:
        print("No suitable story found. Exiting.")
        return

    cid = "REEL-" + str(story["Cluster ID"])
    print(f"Generating video for: {cid}")
    
    # Captures scene-by-scene voiceover + exact durations
    vo_path, srt_path, total_duration, scene_durations = generate_voiceover(script, cid)

    urls, used = [], set()
    main_img = get_image_for_headline(story["Headline"], story["Source URLs"])
    if main_img: used.add(main_img)
    urls.append(main_img)
    
    for t in [script["scene_2_context"], script["scene_3_main"], script["scene_4_details"], script["scene_5_impact"], script["scene_6_next"]]:
        img = get_image_for_slide(t)
        if img and img not in used: 
            urls.append(img)
            used.add(img)
        else: 
            urls.append(None)
    urls.append(main_img)

    music = get_track_for_category(script["category"])
    
    # Pass exact durations to ensure perfect sync
    scenes, folder = render_scenes(cid, script, urls, scene_durations)
    
    final = f"output/reels/{cid}.mp4"
    build_video(scenes, folder, final, vo_path, srt_path, music)
    shutil.rmtree(folder, ignore_errors=True)

    values = {
        "Content ID": cid, "Content Type": "reel", "Topic": story["Headline"], "Source": story["Outlets"],
        "Source URL": story["Source URLs"], "Source Publication Date": story["Earliest Published (UTC)"],
        "Research Date": story["Research Timestamp (UTC)"], "Creation Date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "Status": "Draft", "Caption": f"📌 {script['category'].upper()}\n\n{script['caption']}\n\n💡 Why it matters:\n{script['why_it_matters']}\n\nSources: {story['Outlets']}\n\n" + " ".join(script["hashtags"]),
        "Alt Text": f"Vertical video. {script['caption']}", "Creative Format": f"elite; {total_duration:.1f}s; {script['category']} Audio", "Validation Result": "pending",
    }
    content_ws.append_row([values.get(h, "") for h in headers], value_input_option="RAW")
    print(f"REEL OK: {final}")

if __name__ == "__main__":
    main()
