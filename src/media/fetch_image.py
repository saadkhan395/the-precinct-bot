import os
import re
import requests

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
UNSPLASH_API = "https://api.unsplash.com"

def fetch_news_image(source_urls: str) -> str | None:
    """Extract the og:image (main image) directly from the news article."""
    urls = re.findall(r"https://[^\s]+", source_urls)
    if not urls: return None
    
    url = urls[0]
    # Use a real browser user-agent to bypass basic blocks
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.ok:
            # Look for the Open Graph image tag (handles different attribute orders)
            match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
            if not match:
                match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text, re.IGNORECASE)
            if match:
                print(f"  Found Article Image: {match.group(1)[:60]}...")
                return match.group(1)
    except Exception as e:
        print(f"  Article parse failed: {e}")
    return None

def fetch_wikipedia_image(entity: str) -> str | None:
    """Use Wikipedia generator search to find the closest page and its portrait."""
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
                print(f"  Found Wikipedia Portrait: {pages[0]['original']['source'][:60]}...")
                return pages[0]["original"]["source"]
    except Exception as e:
        print(f"  Wikipedia fetch failed: {e}")
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
                print(f"  Found Unsplash Fallback: {results[0]['urls']['regular'][:60]}...")
                return results[0]["urls"]["regular"]
    except Exception as e:
        print(f"  Unsplash fetch failed: {e}")
    return None

def get_image_for_headline(headline: str, source_urls: str) -> str | None:
    print("1. Trying to extract real image from news article...")
    url = fetch_news_image(source_urls)
    if url: return url

    # Extract the main entity name (e.g., "Pete Hegseth")
    clean_headline = re.sub(r"'s\b", "", headline)
    words = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", clean_headline)
    entity = max(words, key=len) if words else headline.split()[0]

    print(f"2. Trying Wikipedia for: '{entity}'")
    url = fetch_wikipedia_image(entity)
    if url: return url

    print("3. Falling back to Unsplash theme...")
    url = fetch_unsplash_image("US Politics")
    if url: return url

    return None
