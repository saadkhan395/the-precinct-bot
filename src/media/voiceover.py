import asyncio
import os
import subprocess
import edge_tts
import json

async def _generate_audio(text, output_path):
    # Use a professional-sounding US news anchor voice
    voice = "en-US-ChristopherNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_voiceover(text, cid):
    """Generates MP3 voiceover and returns the duration in seconds."""
    folder = f"output/reels/{cid}_audio"
    os.makedirs(folder, exist_ok=True)
    mp3_path = f"{folder}/voiceover.mp3"
    
    print(f"Generating voiceover for {cid}...")
    asyncio.run(_generate_audio(text, mp3_path))
    
    # Get exact duration using ffprobe
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", mp3_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("ffprobe failed to read voiceover duration.")
        
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    
    print(f"Voiceover generated. Duration: {duration:.2f}s")
    return mp3_path, duration
