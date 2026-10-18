"""Fetch subject-relevant images from Unsplash (thematic) or Wikimedia (specific)."""
import os
import re
import requests

UNSPLASH_API = "https://api.unsplash.com"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"


def _extract_entity(headline: str) -> str:
    """Simple extraction of the main proper noun (e.g., 'Trump', 'Supreme Court')."""
    # Look for capitalized words that aren't at the start of the sentence
    words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", headline)
    if words:
        # Return the longest capitalized phrase
        return max(words, key=len)
    return headline.split()[0] if headline else ""


def fetch_wikimedia_image(query: str) -> str | None:
    """Search Wikimedia Commons for a specific subject. Returns image URL or None."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,
        "gsrlimit": 1,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    }
    try:
        r = requests.get(WIKIMEDIA_API, params=params, timeout=15)
        if r.ok:
            pages = r.json().get("query", {}).get("pages", {})
            for page in pages.values():
                info = page.get("imageinfo", [{}])[0]
                if "url" in info:
                    return info["url"]
    except Exception as e:
        print(f"Wikimedia fetch failed: {e}")
    return None


def fetch_unsplash_image(query: str) -> str | None:
    """Search Unsplash for a thematic background. Returns image URL or None."""
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not access_key:
        return None

    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {"query": query, "per_page": 1, "orientation": "portrait"}
    try:
        r = requests.get(f"{UNSPLASH_API}/search/photos", headers=headers, params=params, timeout=15)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                photo = results[0]
                # REQUIRED by Unsplash guidelines: trigger download endpoint
                requests.get(photo["links"]["download_location"], headers=headers, timeout=10)
                return photo["urls"]["regular"]
    except Exception as e:
        print(f"Unsplash fetch failed: {e}")
    return None


def get_image_for_headline(headline: str) -> str | None:
    """Two-tier strategy: try Wikimedia for specific entities, fallback to Unsplash."""
    entity = _extract_entity(headline)
    print(f"Looking for image for: '{entity}' (from headline: {headline[:50]}...)")

    # 1. Try Wikimedia for specific people/places
    url = fetch_wikimedia_image(entity)
    if url:
        print(f"  Found on Wikimedia: {url[:60]}...")
        return url

    # 2. Fallback to Unsplash for thematic background
    url = fetch_unsplash_image(headline)
    if url:
        print(f"  Found on Unsplash: {url[:60]}...")
        return url

    print("  No image found.")
    return None
