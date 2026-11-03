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
    try:
        with Image.open(path) as img:
            w, h = img.size
            footer = img.crop((0, h - 200, w, h)).convert("RGB")
            stat = ImageStat.Stat(footer)
            avg = stat.mean
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
    """Extracts frames and checks actual rendered video for errors."""
    try:
        # 1. Run ffprobe to verify technical streams
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
        
        if video_stream.get("width") != 1080 or video_stream.get("height") != 1920:
            return False, "Resolution is not 1080x1920."

        fps_str = video_stream.get("r_frame_rate", "0/1")
        num, den = map(int, fps_str.split('/'))
        if int(num / den) != 30:
            return False, "Frame rate is not 30 FPS."

        duration = float(video_stream.get("duration", 0))
        if duration < 50 or duration > 65:
            return False, f"Duration {duration}s is outside 50-65s limit."

        if not audio_stream:
            return False, "No audio stream found."

        # 2. Extract 3 frames (at 25%, 50%, 75% of the video) to check visually
        check_points = [duration * 0.25, duration * 0.50, duration * 0.75]
        for i, ts in enumerate(check_points):
            frame_path = f"output/reels/qc_frame_{i}.jpg"
            extract_cmd = ["ffmpeg", "-y", "-ss", str(ts), "-i", path, "-frames:v", "1", frame_path]
            subprocess.run(extract_cmd, capture_output=True)
            
            if not os.path.exists(frame_path):
                return False, f"Failed to extract frame at {ts:.1f}s."

            with Image.open(frame_path) as img:
                # Check if the frame is just a black screen (meaning ffmpeg failed to load images)
                stat = ImageStat.Stat(img.convert("L"))
                if stat.mean[0] < 10:
                    return False, f"Frame at {ts:.1f}s is completely black (render failure)."
                
                # Check if bottom text area has contrast (meaning text/subtitles exist)
                w, h = img.size
                footer = img.crop((0, h - 400, w, h)).convert("L")
                footer_stat = ImageStat.Stat(footer)
                if footer_stat.stddev[0] < 5:
                    return False, f"Frame at {ts:.1f}s has no visible text in the bottom area."
                    
            os.remove(frame_path)

        return True, f"Video specs and visual frames OK ({duration:.1f}s, 30FPS, Audio present)."
        
    except Exception as e:
        return False, f"Video validation error: {str(e)}"
