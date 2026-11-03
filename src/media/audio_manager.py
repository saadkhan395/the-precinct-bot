import os
import requests

AUDIO_DIR = "output/audio"

# Real, distinct royalty-free tracks
TRACK_MAP = {
    "Conflict": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample.mp3",
    "Tragedy": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample2.mp3",
    "Positive": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample3.mp3",
    "Economy": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample4.mp3",
    "Elections": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample5.mp3",
    "Controversy": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample6.mp3",
    "Breaking": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample7.mp3",
    "Science": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample8.mp3"
}
DEFAULT_TRACK = TRACK_MAP["Breaking"]

def ensure_audio_library():
    os.makedirs(AUDIO_DIR, exist_ok=True)

def get_track_for_category(category: str) -> str:
    ensure_audio_library()
    url = TRACK_MAP.get(category, DEFAULT_TRACK)
    safe_cat = category.lower().replace(' ', '_') if category else "default"
    filepath = os.path.join(AUDIO_DIR, f"track_{safe_cat}.mp3")
    
    if not os.path.exists(filepath):
        print(f"Downloading {category} audio track...")
        try:
            r = requests.get(url, timeout=20)
            if r.ok:
                with open(filepath, "wb") as f:
                    f.write(r.content)
            else:
                return None
        except Exception:
            return None
    return filepath
