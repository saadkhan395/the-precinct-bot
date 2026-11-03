import json
import os
import subprocess

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-800:])
    return r.stdout

def scene_clip(png, seconds, index, out):
    frames = int(seconds * 30)
    
    # STAGE 3: Rotating Cinematic Motions
    motion = index % 4
    
    if motion == 0:
        # Zoom in, pan right
        z = "min(zoom+0.0008,1.08)"
        x = "iw/2-(iw/zoom/2) - (on*1.5)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == 1:
        # Zoom out, pan left
        z = "if(eq(on,1),1.08,max(zoom-0.0008,1.0))"
        x = "iw/2-(iw/zoom/2) + (on*1.5)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == 2:
        # Zoom in, pan down
        z = "min(zoom+0.0008,1.08)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2) + (on*1.5)"
    else:
        # Zoom out, pan up
        z = "if(eq(on,1),1.08,max(zoom-0.0008,1.0))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2) - (on*1.5)"

    # Professional 0.4s Crossfade
    fade_dur = 0.4
    fade_out_start = max(0.0, seconds - fade_dur)
    
    vf = (
        "scale=2160:3840," 
        f"zoompan=z='{z}':x='{x}':y='{y}'"
        f":d={frames}:s=1080x1920:fps=30,"
        f"fade=t=in:st=0:d={fade_dur},fade=t=out:st={fade_out_start}:d={fade_dur},format=yuv420p"
    )
    
    run([
        "ffmpeg", "-y", "-i", png, "-vf", vf, "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", out
    ])

def build_video(scenes, folder, final, vo, srt, music):
    clips = []
    total = 0
    
    # 1. Render Scenes with Advanced Motion
    for i, (png, sec) in enumerate(scenes):
        clip = f"{folder}/c{i}.mp4"
        scene_clip(png, sec, i, clip)
        clips.append(clip)
        total += sec
        
    with open(f"{folder}/list.txt", "w") as f:
        for c in clips: 
            f.write(f"file '{os.path.abspath(c)}'\n")
        
    silent = f"{folder}/v.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{folder}/list.txt", "-c", "copy", silent])
    
    # 2. Burn Subtitles
    subs = f"{folder}/subs.mp4"
    if srt and os.path.exists(srt):
        sub_filter = f"subtitles='{os.path.abspath(srt)}':force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00F0EBE6,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,MarginV=260'"
        run(["ffmpeg", "-y", "-i", silent, "-vf", sub_filter, "-c:v", "libx264", "-crf", "20", subs])
    else:
        subs = silent
        
    # 3. Audio Mixing (Ducking) with SAFETY CHECKS
    if music and os.path.exists(music):
        af = (
            "[1:a]loudnorm=I=-14:TP=-1.0:LRA=11[vo];"
            "[vo]asplit=2[v1][v2];"
            "[2:a]volume=0.15[bg];"
            "[bg][v1]sidechaincompress=threshold=0.1:ratio=8:attack=50:release=1000[duck];"
            "[duck][v2]amix=inputs=2:duration=first[aout]"
        )
        run([
            "ffmpeg", "-y", "-i", subs, "-i", vo, "-stream_loop", "-1", "-i", music,
            "-filter_complex", af, "-map", "0:v:0", "-map", "[aout]", 
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(total), 
            "-movflags", "+faststart", final
        ])
    else:
        print("WARNING: Music missing. Rendering Voiceover only.")
        run([
            "ffmpeg", "-y", "-i", subs, "-i", vo,
            "-map", "0:v:0", "-map", "1:a:0", 
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(total), 
            "-movflags", "+faststart", final
        ])
        
    return final
