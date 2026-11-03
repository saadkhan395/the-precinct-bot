import asyncio
import os
import subprocess
import edge_tts
import json

async def _generate_audio_and_srt(text, mp3_path, srt_path):
    voice = "en-US-ChristopherNeural" 
    communicate = edge_tts.Communicate(text, voice)
    
    submaker = edge_tts.SubMaker()
    with open(mp3_path, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
                
    with open(srt_path, "w", encoding="utf-8") as f:
        # THE FIX: Changed generate_subs() to get_srt()
        f.write(submaker.get_srt())

def generate_voiceover(text, cid):
    """Generates MP3 voiceover and SRT subtitles, returns duration."""
    folder = f"output/reels/{cid}_audio"
    os.makedirs(folder, exist_ok=True)
    mp3_path = f"{folder}/voiceover.mp3"
    srt_path = f"{folder}/subtitles.srt"
    
    print(f"Generating voiceover and subtitles for {cid}...")
    asyncio.run(_generate_audio_and_srt(text, mp3_path, srt_path))
    
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", mp3_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    
    print(f"Voiceover generated. Duration: {duration:.2f}s")
    return mp3_path, srt_path, duration
