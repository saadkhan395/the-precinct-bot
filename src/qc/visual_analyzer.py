import os
import json
import subprocess
from PIL import Image, ImageStat

def check_dimensions(path, expected_size):
    try:
        with Image.open(path) as img:
            if list(img.size) != expected_size:
                return False, f"Size {img.size} != {expected_size}"
            return True, "Size OK"
    except Exception as e:
        return False, str(e)

def check_safe_margins(path, margin_px=80):
    """Checks if the bottom 200px is the Midnight Navy background."""
    try:
        with Image.open(path) as img:
            w, h = img.size
            footer = img.crop((0, h - 200, w, h)).convert("RGB")
            stat = ImageStat.Stat(footer)
            avg = stat.mean
            # Midnight Navy is (10, 22, 48)
            if avg[0] < 30 and avg[1] < 40 and avg[2] < 70:
                return True, "Safe zone is solid Navy."
            return False, "Background behind text is not the standard Navy box."
    except Exception as e:
        return False, str(e)

def check_image_quality(path):
    try:
        with Image.open(path) as img:
            stat = ImageStat.Stat(img.convert("L"))
            if stat.stddev[0] < 15:
                return False, "Image appears washed out or blurred."
            return True, "Image quality OK."
    except Exception as e:
        return False, str(e)

def check_contrast(path):
    try:
        with Image.open(path) as img:
            w, h = img.size
            footer = img.crop((0, h - 200, w, h)).convert("L")
            stat = ImageStat.Stat(footer)
            if stat.stddev[0] > 60:
                return False, "High contrast variance in text area. Text might be unreadable."
            return True, "Contrast OK."
    except Exception as e:
        return False, str(e)

def check_video_specs(path):
    """Strict checks for the 60-second Reel specifications."""
    try:
        # Run ffprobe to get stream data
        cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,duration", "-of", "json", path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return False, "ffprobe failed to read video."

        info = json.loads(res.stdout)
        streams = info.get("streams", [])
        
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            return False, "No video stream found."
        
        # 1. Check Resolution
        if video_stream.get("width") != 1080 or video_stream.get("height") != 1920:
            return False, f"Resolution is {video_stream.get('width')}x{video_stream.get('height')}, expected 1080x1920."
            
        # 2. Check Frame Rate (Must be exactly 30)
        fps_str = video_stream.get("r_frame_rate", "0/1")
        num, den = map(int, fps_str.split('/'))
        fps = num / den
        if int(fps) != 30:
            return False, f"Frame rate is {fps:.2f}, expected 30."

        # 3. Check Duration (50 to 65 seconds)
        duration = float(video_stream.get("duration", 0))
        if duration < 50 or duration > 65:
            return False, f"Duration is {duration:.1f}s, expected ~60s (50-65s limit)."

        # 4. Check Audio Presence
        if not audio_stream:
            return False, "No audio stream found (Voiceover/Music missing)."
        if audio_stream.get("codec_name") != "aac":
            return False, f"Audio codec is {audio_stream.get('codec_name')}, expected AAC."

        return True, f"Video specs OK: {duration:.1f}s, 30FPS, 1080x1920, AAC Audio."
        
    except Exception as e:
        return False, f"Video validation error: {str(e)}"
