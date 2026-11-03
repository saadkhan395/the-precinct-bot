import json
import os
import subprocess

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-800:])
    return r.stdout

def build_video(scenes, folder, final, vo, srt, music):
    clips = []
    total = 0
    
    # 1. Render Scenes with Ken Burns Motion
    for i, (png, sec) in enumerate(scenes):
        clip = f"{folder}/c{i}.mp4"
        pan = "-(on*0.5)" if i % 2 == 0 else "+(on*0.5)"
        vf = (
            "scale=2160:3840,"
            f"zoompan=z='min(zoom+0.0005,1.05)':x='iw/2-(iw/zoom/2){pan}':y='ih/2-(ih/zoom/2)'"
            f":d={int(sec*30)}:s=1080x1920:fps=30,"
            "fade=t=in:st=0:d=0.3,fade=t=out:st={sec-0.3}:d=0.3,format=yuv420p"
        )
        run([
            "ffmpeg", "-y", "-i", png, "-vf", vf, "-frames:v", str(int(sec*30)),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", clip
        ])
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
