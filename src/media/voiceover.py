import asyncio, os, subprocess, edge_tts, json

async def _generate_audio(text, mp3_path):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    with open(mp3_path, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])

def _generate_failsafe_srt(text, duration, srt_path):
    words = text.split()
    chunks = [" ".join(words[i:i+6]) for i in range(0, len(words), 6)]
    time_per_chunk = duration / max(1, len(chunks))
    
    def fmt(s):
        return f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d},{int((s-int(s))*1000):03d}"
        
    with open(srt_path, "w", encoding="utf-8") as f:
        curr = 0.0
        for i, chunk in enumerate(chunks):
            f.write(f"{i+1}\n{fmt(curr)} --> {fmt(curr+time_per_chunk)}\n{chunk}\n\n")
            curr += time_per_chunk

def generate_voiceover(text, cid):
    folder = f"output/reels/{cid}_audio"
    os.makedirs(folder, exist_ok=True)
    mp3_path, srt_path = f"{folder}/voiceover.mp3", f"{folder}/subtitles.srt"
    
    asyncio.run(_generate_audio(text, mp3_path))
    
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", mp3_path]
    duration = float(json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)["format"]["duration"])
    _generate_failsafe_srt(text, duration, srt_path)
    return mp3_path, srt_path, duration
