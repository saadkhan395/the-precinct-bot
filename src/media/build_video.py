import json
import os
import subprocess

FPS = 30 # Prompt requires 30 FPS
FADE = 0.4

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

def build_video(scenes, folder, final_path, voiceover_path, music_path):
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

    if not voiceover_path:
        raise RuntimeError("Voiceover is required for the new pipeline.")

    if music_path and os.path.exists(music_path):
        # FIXED: Added asplit to split the voiceover into two streams
        audio_filter = (
    "[1:a]loudnorm=I=-14:TP=-1.0:LRA=11[vo_norm];"
    "[vo_norm]asplit=2[vo_side][vo_mix];"
    "[2:a]volume=0.15[bg];"
    "[bg][vo_side]sidechaincompress=threshold=0.1:ratio=8:attack=50:release=1000[bg_ducked];"
    "[bg_ducked][vo_mix]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        run([
            "ffmpeg", "-y",
            "-i", silent_video,
            "-i", voiceover_path,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex", audio_filter,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_duration),
            "-movflags", "+faststart",
            final_path
        ])
    else:
        # Fallback to voiceover only
        run([
            "ffmpeg", "-y", "-i", silent_video, "-i", voiceover_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_duration),
            "-movflags", "+faststart", final_path
        ])
        
    return final_path

def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height,duration", "-of", "json", path])
    return json.loads(out)
