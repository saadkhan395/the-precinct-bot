"""Fetch subject-relevant images from Wikipedia (faces) or Unsplash (themes)."""
import os
import re
import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
UNSPLASH_API = "https://api.unsplash.com"

THEMES = [
    "White House", "Senate", "Congress", "Supreme Court", "Border", 
    "Election", "Economy", "Pentagon", "Capitol", "Immigration", "Voting", "Politics"
]

# If these names appear anywhere in the headline, Wikipedia is searched for them FIRST.
VIP_NAMES = [
    "Trump", "Biden", "Harris", "Vance", "Obama", "Clinton", "Pelosi", 
    "Schumer", "McConnell", "Putin", "Zelensky", "Musk", "Guilfoyle", "Rubio"
]

ALIASES = {
    "trump": "Donald Trump", "biden": "Joe Biden", "harris": "Kamala Harris",
    "vance": "JD Vance", "obama": "Barack Obama", "putin": "Vladimir Putin",
    "zelensky": "Volodymyr Zelenskyy", "musk": "Elon Musk"
}

def _extract_entity(headline: str) -> str:
    # 1. Check VIP list first
    for name in VIP_NAMES:
        if name.lower() in headline.lower():
            return ALIASES.get(name.lower(), name)
            
    # 2. Fallback to longest capitalized phrase
    words = re.findall(r"\b[A-Z][a-zA-Z']+(?:\s+[A-Z][a-zA-Z']+)*\b", headline)
    if words:
        entity = max(words, key=len)
        return ALIASES.get(entity.lower(), entity)
    return "US Politics"

def _extract_theme(headline: str) -> str:
    for theme in THEMES:
        if theme.lower() in headline.lower():
            return theme
    return "US Politics"

def fetch_wikipedia_image(entity: str) -> str | None:
    params = {
        "action": "query", "titles": entity,
        "prop": "pageimages", "pithumbsize": 1200, "format": "json"
    }
    try:
        r = requests.get(WIKIPEDIA_API, params=params, timeout=15)
        if r.ok:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                if "thumbnail" in page:
                    return page["thumbnail"]["source"]
    except Exception as e:
        print(f"  Wikipedia fetch failed: {e}")
    return None

def fetch_unsplash_image(query: str) -> str | None:
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
    entity = _extract_entity(headline)
    theme = _extract_theme(headline)
    print(f"Looking for image. Entity: '{entity}', Theme: '{theme}'")

    url = fetch_wikipedia_image(entity)
    if url:
        print(f"  Found on Wikipedia: {url[:60]}...")
        return url

    url = fetch_unsplash_image(theme)
    if url:
        print(f"  Found on Unsplash for '{theme}': {url[:60]}...")
        return url

    print("  No image found.")
    return None
