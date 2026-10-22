import os
import re
import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
UNSPLASH_API = "https://api.unsplash.com"

def fetch_news_image(url: str) -> str | None:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.ok:
            match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
            if not match:
                match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text, re.IGNORECASE)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

def fetch_wikipedia_image(entity: str) -> str | None:
    params = {
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": entity, "gsrlimit": 1,
        "prop": "pageimages", "piprop": "original",
    }
    try:
        r = requests.get(WIKIPEDIA_API, params=params, timeout=15)
        if r.ok:
            pages = r.json().get("query", {}).get("pages", [])
            if pages and "original" in pages[0]:
                return pages[0]["original"]["source"]
    except Exception:
        pass
    return None

def fetch_unsplash_image(query: str) -> str | None:
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not access_key: return None

    headers = {"Authorization": f"Client-ID {access_key}"}
    # Use only the first 3 words to get a broader, better match
    clean_query = " ".join(query.split()[:3]) 
    params = {"query": clean_query, "per_page": 1, "orientation": "portrait"}
    try:
        r = requests.get(f"{UNSPLASH_API}/search/photos", headers=headers, params=params, timeout=15)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                return results[0]["urls"]["regular"]
    except Exception:
        pass
    return None

def get_image_for_headline(headline: str, source_urls: str) -> str | None:
    """Main fetcher for the main story/cover."""
    # 1. Try OG Image from news article
    urls = re.findall(r"https://[^\s]+", source_urls)
    if urls:
        url = fetch_news_image(urls[0])
        if url: return url

    # 2. Try Wikipedia for main entity
    clean_headline = re.sub(r"'s\b", "", headline)
    words = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", clean_headline)
    entity = max(words, key=len) if words else headline.split()[0]

    url = fetch_wikipedia_image(entity)
    if url: return url

    # 3. Fallback to Unsplash
    return fetch_unsplash_image(headline)

def get_image_for_slide(text: str) -> str | None:
    """Fetches a specific image for a carousel/reel slide's content."""
    # 1. Try Wikipedia for the main subject in the slide text
    words = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", text)
    if words:
        entity = max(words, key=len)
        url = fetch_wikipedia_image(entity)
        if url: return url
    
    # 2. Fallback to Unsplash based on the slide text
    return fetch_unsplash_image(text)
