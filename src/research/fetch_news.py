import calendar
from datetime import datetime, timezone

import feedparser
import requests
import yaml

USER_AGENT = "Mozilla/5.0 (compatible; DailyPresentBot/1.0)"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_time(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)


def fetch_feed(feed, timeout=30):
    try:
        resp = requests.get(
            feed["url"], headers={"User-Agent": USER_AGENT}, timeout=timeout
        )
        resp.raise_for_status()
    except Exception as e:
        return [], f"FAILED: {e}"
    parsed = feedparser.parse(resp.content)
    items = []
    for e in parsed.entries:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        if not title or not link:
            continue
        items.append(
            {
                "source": feed["name"],
                "title": title,
                "url": link,
                "published": parse_time(e),
            }
        )
    return items, f"OK ({len(items)} items)"


def fetch_all(feeds, max_age_hours):
    now = datetime.now(timezone.utc)
    fresh = []
    status = {}
    for feed in feeds:
        items, msg = fetch_feed(feed)
        status[feed["name"]] = msg
        for it in items:
            if it["published"] is None:
                continue
            age_h = (now - it["published"]).total_seconds() / 3600
            if -1 <= age_h <= max_age_hours:
                fresh.append(it)
    return fresh, status
