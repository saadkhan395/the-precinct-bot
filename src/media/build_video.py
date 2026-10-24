import json
import os
import subprocess
from media.audio_manager import get_random_track

FPS = 25
FADE = 0.3

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-800:])
    return r.stdout

def scene_clip(png, seconds, out):
    frames = int(seconds * FPS)
    vf = (
        "scale=2160:3840,"
        "zoompan=z='min(zoom+0.0005,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1080x1920:fps={FPS},"
        f"fade=t=in:st=0:d={FADE},fade=t=out:st={seconds - FADE}:d={FADE},"
        "format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-i", png, "-vf", vf, "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), out,
    ])

def generate_srt(scenes, srt_path):
    """Generates an accurate .srt file based on exact scene durations."""
    def fmt_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    current_time = 0.0
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (png, duration) in enumerate(scenes, start=1):
            start = fmt_time(current_time)
            current_time += duration
            end = fmt_time(current_time)
            # Note: We don't actually use this text, we use the burned-in text.
            # But if you wanted to extract it, you'd read the script here.
            f.write(f"{i}\n{start} --> {end}\nCaption {i}\n\n")

def build_video(scenes, folder, final_path, voiceover_path):
    clips = []
    total_duration = 0
    for i, (png, seconds) in enumerate(scenes):
        clip = f"{folder}/clip{i:02d}.mp4"
        scene_clip(png, seconds, clip)
        clips.append(clip)
        total_duration += seconds
        
    list_path = f"{folder}/clips.txt"
    with open(list_path, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
            
    silent_video = f"{folder}/video_only.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", silent_video])

    bg_music = get_random_track()
    
    # Audio Mixing: Voiceover (100% volume) + Music (10% volume)
    if bg_music and voiceover_path:
        audio_filter = (
            f"[1:a]volume=1.0[vo];"
            f"[2:a]volume=0.10,afade=t=in:st=0:d=2.0,afade=t=out:st={total_duration-2.0}:d=2.0[bg];"
            f"[vo][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        run([
            "ffmpeg", "-y",
            "-i", silent_video,
            "-i", voiceover_path,
            "-stream_loop", "-1", "-i", bg_music,
            "-filter_complex", audio_filter,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_duration),
            "-movflags", "+faststart",
            final_path
        ])
    elif voiceover_path:
        # Voiceover only, no music
        run([
            "ffmpeg", "-y", "-i", silent_video, "-i", voiceover_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_duration),
            "-movflags", "+faststart", final_path
        ])
    else:
        raise RuntimeError("No voiceover generated. Cannot build video.")
        
    return final_path

def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,duration", "-of", "json", path])
    return json.loads(out)
