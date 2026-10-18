"""Fetch subject-relevant images from Wikipedia (faces) or Unsplash (themes)."""
import os
import re
import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
UNSPLASH_API = "https://api.unsplash.com"

# If the headline contains these words, use them for the Unsplash fallback
THEMES = [
    "White House", "Senate", "Congress", "Supreme Court", "Border", 
    "Election", "Economy", "Pentagon", "Capitol", "Immigration", "Voting", "Politics"
]

def _extract_entity(headline: str) -> str:
    """Extract the main proper noun (e.g., 'Kimberly Guilfoyle')."""
    words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", headline)
    if words:
        return max(words, key=len)
    return headline.split()[0] if headline else ""

def _extract_theme(headline: str) -> str:
    """Find a generic political theme for Unsplash."""
    for theme in THEMES:
        if theme.lower() in headline.lower():
            return theme
    return "US Politics" 

def fetch_wikipedia_image(entity: str) -> str | None:
    """Fetch the main Wikipedia article image for a specific person/place."""
    params = {
        "action": "query",
        "titles": entity,
        "prop": "pageimages",
        "pithumbsize": 1200,
        "format": "json"
    }
    try:
        r = requests.get(WIKIPEDIA_API, params=params, timeout=15)
        if r.ok:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                # If the page exists and has a thumbnail
                if "thumbnail" in page:
                    return page["thumbnail"]["source"]
    except Exception as e:
        print(f"  Wikipedia fetch failed: {e}")
    return None

def fetch_unsplash_image(query: str) -> str | None:
    """Search Unsplash for a thematic background."""
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        print("  [Unsplash] Error: UNSPLASH_ACCESS_KEY is not set.")
        return None

    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {"query": query, "per_page": 1, "orientation": "portrait"}
    try:
        r = requests.get(f"{UNSPLASH_API}/search/photos", headers=headers, params=params, timeout=15)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                photo = results[0]
                requests.get(photo["links"]["download_location"], headers=headers, timeout=10)
                return photo["urls"]["regular"]
    except Exception as e:
        print(f"  Unsplash fetch failed: {e}")
    return None

def get_image_for_headline(headline: str) -> str | None:
    """Try Wikipedia for the actual person, fallback to Unsplash theme."""
    entity = _extract_entity(headline)
    theme = _extract_theme(headline)
    print(f"Looking for image. Entity: '{entity}', Theme: '{theme}'")

    # 1. Try Wikipedia for the actual person's face
    url = fetch_wikipedia_image(entity)
    if url:
        print(f"  Found on Wikipedia: {url[:60]}...")
        return url

    # 2. Fallback to Unsplash for thematic background
    url = fetch_unsplash_image(theme)
    if url:
        print(f"  Found on Unsplash for '{theme}': {url[:60]}...")
        return url

    print("  No image found.")
    return None
