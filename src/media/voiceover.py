import asyncio
import os
import subprocess
import edge_tts
import json

async def _generate_audio(text, mp3_path):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    with open(mp3_path, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])

def _get_duration(path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return float(json.loads(res.stdout)["format"]["duration"])

def generate_voiceover(script, cid):
    folder = f"output/reels/{cid}_audio"
    os.makedirs(folder, exist_ok=True)
    
    scenes = [
        script["scene_1_hook"], script["scene_2_context"], script["scene_3_main"],
        script["scene_4_details"], script["scene_5_impact"], script["scene_6_next"], script["scene_7_cta"]
    ]
    
    # 1. Generate individual audio for each scene
    audio_files = []
    scene_durations = []
    
    print(f"Generating scene-by-scene voiceover for {cid}...")
    for i, text in enumerate(scenes):
        mp3_path = f"{folder}/s{i}.mp3"
        asyncio.run(_generate_audio(text, mp3_path))
        audio_files.append(mp3_path)
        scene_durations.append(_get_duration(mp3_path))
        
    # 2. Create 0.5s silence
    silence_path = f"{folder}/silence.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.5", "-q:a", "9", "-acodec", "libmp3lame", silence_path], capture_output=True)
    
    # 3. Concatenate audio with silence
    list_path = f"{folder}/list.txt"
    with open(list_path, "w") as f:
        for i in range(len(audio_files)):
            f.write(f"file '{os.path.abspath(audio_files[i])}'\n")
            if i < len(audio_files) - 1:
                f.write(f"file '{os.path.abspath(silence_path)}'\n")
                
    final_mp3 = f"{folder}/voiceover.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", final_mp3], capture_output=True)
    
    # 4. Generate perfectly synced SRT
    srt_path = f"{folder}/subtitles.srt"
    curr_time = 0.0
    with open(srt_path, "w", encoding="utf-8") as f:
        sub_idx = 1
        for i, text in enumerate(scenes):
            dur = scene_durations[i]
            words = text.split()
            # Limit to 5 words per subtitle chunk for max 2 lines on screen
            chunks = [" ".join(words[j:j+5]) for j in range(0, len(words), 5)]
            time_per_chunk = dur / max(1, len(chunks))
            
            for chunk in chunks:
                start = curr_time
                end = curr_time + time_per_chunk
                f.write(f"{sub_idx}\n")
                f.write(f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start-int(start))*1000):03d} --> ")
                f.write(f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end-int(end))*1000):03d}\n")
                f.write(f"{chunk}\n\n")
                curr_time += time_per_chunk
                sub_idx += 1
                
            # Add the 0.5s silence to the timeline
            if i < len(scenes) - 1:
                curr_time += 0.5

    total_duration = _get_duration(final_mp3)
    print(f"Voiceover and Subtitles generated. Duration: {total_duration:.2f}s")
    return final_mp3, srt_path, total_duration, scene_durations
