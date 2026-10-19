"""Manages royalty-free background audio for Reels autonomously."""
import os
import random
import requests

AUDIO_DIR = "output/audio"

# Public domain / royalty-free tracks (Creative Commons 0 or equivalent)
SAFE_TRACKS = [
    "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample.mp3",
    "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample2.mp3",
    "https://github.com/rafaelreis-hotmart/Audio-Sample-files/raw/master/sample3.mp3"
]

def ensure_audio_library():
    """Downloads the tracks if they don't exist locally."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    local_tracks = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]
    
    if not local_tracks:
        print("Downloading safe audio library...")
        for i, url in enumerate(SAFE_TRACKS):
            try:
                r = requests.get(url, timeout=20)
                if r.ok:
                    with open(os.path.join(AUDIO_DIR, f"track_{i}.mp3"), "wb") as f:
                        f.write(r.content)
                    print(f"  Downloaded track_{i}.mp3")
            except Exception as e:
                print(f"  Failed to download track: {e}")

def get_random_track() -> str:
    """Returns the path to a random audio track."""
    ensure_audio_library()
    tracks = [os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR) if f.endswith('.mp3')]
    if not tracks:
        return None
    return random.choice(tracks)
