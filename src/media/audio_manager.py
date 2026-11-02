import os
import random
import requests

AUDIO_DIR = "output/audio"

# Categories mapped to safe, royalty-free public domain tracks
TRACK_MAP = {
    "Conflict": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample.mp3",
    "Tragedy": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample2.mp3",
    "Positive": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample3.mp3",
    "Economy": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample.mp3",
    "Elections": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample2.mp3",
    "Controversy": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample.mp3",
    "Breaking": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample2.mp3",
    "Science": "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample3.mp3"
}
DEFAULT_TRACK = "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample.mp3"

def ensure_audio_library():
    os.makedirs(AUDIO_DIR, exist_ok=True)

def get_track_for_category(category: str) -> str:
    """Selects a track based on the editorial category."""
    ensure_audio_library()
    
    # Fallback if category is missing or unknown
    url = TRACK_MAP.get(category, DEFAULT_TRACK)
    filename = f"track_{category.lower().replace(' ', '_')}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"Downloading {category} audio track...")
        try:
            r = requests.get(url, timeout=20)
            if r.ok:
                with open(filepath, "wb") as f:
                    f.write(r.content)
            else:
                return None
        except Exception as e:
            print(f"Failed to download audio: {e}")
            return None
            
    return filepath
