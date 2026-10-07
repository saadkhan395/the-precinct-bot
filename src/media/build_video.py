import json
import os
import subprocess

FPS = 25
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
        "zoompan=z='min(zoom+0.0006,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s=1080x1920:fps={FPS},"
        f"fade=t=in:st=0:d={FADE},fade=t=out:st={seconds - FADE}:d={FADE},"
        "format=yuv420p"
    )
    run(
        [
            "ffmpeg", "-y", "-i", png, "-vf", vf, "-frames:v", str(frames),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS), out,
        ]
    )


def build_video(scenes, folder, final_path):
    clips = []
    for i, (png, seconds) in enumerate(scenes):
        clip = f"{folder}/clip{i:02d}.mp4"
        scene_clip(png, seconds, clip)
        clips.append(clip)
    list_path = f"{folder}/clips.txt"
    with open(list_path, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    silent = f"{folder}/video_only.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", silent])
    run(
        [
            "ffmpeg", "-y", "-i", silent,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", final_path,
        ]
    )
    return final_path


def probe(path):
    out = run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_name,width,height,duration", "-of", "json", path,
        ]
    )
    return json.loads(out)
