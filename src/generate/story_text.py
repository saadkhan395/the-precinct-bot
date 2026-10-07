import html
import re

import feedparser
import requests

from research.fetch_news import USER_AGENT


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def get_story_text(urls_cell, feeds):
    wanted = {}
    for line in str(urls_cell).splitlines():
        if ": " in line:
            outlet, url = line.split(": ", 1)
            wanted[url.strip()] = outlet.strip()
    names = set(wanted.values())
    parts = []
    for feed in feeds:
        if feed["name"] not in names:
            continue
        try:
            resp = requests.get(
                feed["url"], headers={"User-Agent": USER_AGENT}, timeout=30
            )
            resp.raise_for_status()
        except Exception:
            continue
        for e in feedparser.parse(resp.content).entries:
            link = (e.get("link") or "").strip()
            if link in wanted:
                summary = clean(e.get("summary") or e.get("description") or "")
                if summary:
                    parts.append(f"{wanted[link]}: {summary[:600]}")
    return "\n".join(parts)
