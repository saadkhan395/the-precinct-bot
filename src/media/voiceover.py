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

def _generate_failsafe_srt(text, duration, srt_path):
    """Generates a perfectly timed SRT file based on word count."""
    words = text.split()
    if not words:
        return
        
    # Group words into chunks of 5-6 for subtitles
    chunks = []
    current_chunk = []
    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= 6:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    # Calculate time per chunk
    time_per_chunk = duration / len(chunks)
    
    def format_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"

    with open(srt_path, "w", encoding="utf-8") as f:
        current_time = 0.0
        for i, chunk in enumerate(chunks):
            start = format_time(current_time)
            current_time += time_per_chunk
            end = format_time(current_time)
            f.write(f"{i+1}\n{start} --> {end}\n{chunk}\n\n")

def generate_voiceover(text, cid):
    """Generates MP3 and robust SRT subtitles, returns duration."""
    folder = f"output/reels/{cid}_audio"
    os.makedirs(folder, exist_ok=True)
    mp3_path = f"{folder}/voiceover.mp3"
    srt_path = f"{folder}/subtitles.srt"
    
    print(f"Generating voiceover for {cid}...")
    asyncio.run(_generate_audio(text, mp3_path))
    
    # Get exact duration
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", mp3_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    
    # Generate the failsafe SRT
    _generate_failsafe_srt(text, duration, srt_path)
    print(f"Voiceover and Subtitles generated. Duration: {duration:.2f}s")
    
    return mp3_path, srt_path, duration
