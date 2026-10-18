import os
import re
import requests

UNSPLASH_API = "https://api.unsplash.com"
THEMES = ["White House", "Senate", "Congress", "Supreme Court", "Border", "Election", "Economy", "Pentagon", "Capitol", "Immigration", "Voting"]

def _extract_theme(headline: str) -> str:
    for theme in THEMES:
        if theme.lower() in headline.lower():
            return theme
    return "US Politics"

def fetch_news_image(source_urls: str) -> str | None:
    """Extract the og:image (main image) directly from the news article."""
    # The Source URLs are formatted as "Outlet: https://..."
    urls = re.findall(r"https://[^\s]+", source_urls)
    if not urls:
        return None

    url = urls[0] # Try the first source
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        print(f"  Fetching article HTML from: {url[:50]}...")
        r = requests.get(url, headers=headers, timeout=15)
        if r.ok:
            # Look for the Open Graph image tag
            match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', r.text)
            if match:
                img_url = match.group(1)
                print(f"  Found OG Image: {img_url[:60]}...")
                return img_url
    except Exception as e:
        print(f"  Failed to parse article image: {e}")
    
    return None

def fetch_unsplash_image(query: str) -> str | None:
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not access_key: return None

    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {"query": query, "per_page": 1, "orientation": "portrait"}
    try:
        r = requests.get(f"{UNSPLASH_API}/search/photos", headers=headers, params=params, timeout=15)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                return results[0]["urls"]["regular"]
    except Exception as e:
        print(f"  Unsplash fetch failed: {e}")
    return None

def get_image_for_headline(headline: str, source_urls: str) -> str | None:
    """Try to get the real news image first, fallback to thematic stock photo."""
    print("Looking for real news image...")
    url = fetch_news_image(source_urls)
    if url:
        return url

    theme = _extract_theme(headline)
    print(f"Fallback to Unsplash theme: '{theme}'")
    url = fetch_unsplash_image(theme)
    if url:
        return url

    print("  No image found.")
    return None
