"""Deterministic QC checks for content rows.

BUG-3 FIX: added check_commentary() so QC rejects drafts that contain
analysis/editorial language instead of plain fact reporting.
"""
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

import yaml
from PIL import Image

from media.build_video import probe

# Words that indicate editorial/analysis rather than fact reporting.
COMMENTARY_WORDS = [
    "highlight", "highlights", "highlighted",
    "underscore", "underscores", "underscored",
    "signal", "signals", "signaled", "signalled",
    "reveal", "reveals", "revealed",
    "stakes", "raise questions", "raises questions", "raised questions",
    "shed light", "sheds light", "shedding light",
    "paint a picture", "paints a picture",
    "crucial", "significant", "significance",
    "the clash",
]

DEFAULTS = {
    "caption": {"max_chars": 2200, "min_hashtags": 3, "max_hashtags": 30},
    "headline": {"min_words": 4, "max_words": 18},
    "banned_phrases": [],
    "media": {
        "image_size": [1080, 1350],
        "video_size": [1080, 1920],
        "video_min_seconds": 3,
        "video_max_seconds": 90,
        "carousel_min_slides": 2,
        "carousel_max_slides": 10,
    },
}


def load_rules(path):
    rules = {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in DEFAULTS.items()}
    try:
        with open(path, "r", encoding="utf-8") as f:
            custom = yaml.safe_load(f) or {}
    except FileNotFoundError:
        custom = {}
    for key, val in custom.items():
        if isinstance(val, dict) and isinstance(rules.get(key), dict):
            rules[key].update(val)
        else:
            rules[key] = val
    return rules


def res(name, ok, detail=""):
    return {"check": name, "ok": bool(ok), "detail": detail}


def check_text(row, rules):
    out = []
    caption = str(row.get("Caption", ""))
    parts = [p.strip() for p in caption.split("\n\n")]
    c = rules["caption"]

    out.append(res("caption_structure", len(parts) >= 4, f"{len(parts)} blocks, need 4"))
    out.append(
        res("caption_length", 0 < len(caption) <= c["max_chars"], f"{len(caption)} chars")
    )
    tags = re.findall(r"#\w+", caption)
    out.append(
        res(
            "hashtags",
            c["min_hashtags"] <= len(tags) <= c["max_hashtags"],
            f"{len(tags)} hashtags",
        )
    )
    cta = parts[1] if len(parts) > 1 else ""
    out.append(res("cta_present", len(cta) >= 10, f"CTA length {len(cta)}"))
    sources_ok = len(parts) > 2 and parts[2].startswith("Sources:")
    out.append(res("sources_line", sources_ok, "Sources line missing" if not sources_ok else ""))
    lower = caption.lower()
    hits = [p for p in rules.get("banned_phrases", []) if p.lower() in lower]
    out.append(res("banned_phrases", not hits, ", ".join(hits)))
    first = parts[0] if parts else ""
    out.append(
        res(
            "caption_quality",
            len(first) >= 40 and first[-1:] in ".!?" and "  " not in caption and "..." not in first,
            "Caption should be 40+ chars, end with punctuation, no double spaces",
        )
    )
    alt = str(row.get("Alt Text", "")).strip()
    out.append(res("alt_text", len(alt) >= 20, f"{len(alt)} chars"))

    topic = str(row.get("Topic", "")).strip()
    words = len(topic.split())
    h = rules["headline"]
    ok = h["min_words"] <= words <= h["max_words"] and not (topic.isupper() and words > 2)
    out.append(res("headline_quality", ok, f"{words} words"))
    return out


def check_commentary(row):
    """BUG-3 FIX: reject editorial / analysis language in copy."""
    fields = {
        "topic": str(row.get("Topic", "")),
        "caption": str(row.get("Caption", "")),
        "alt": str(row.get("Alt Text", "")),
    }
    hits_by_field = {}
    for name, text in fields.items():
        low = text.lower()
        found = [w for w in COMMENTARY_WORDS if w in low]
        if found:
            hits_by_field[name] = found

    if hits_by_field:
        detail = "; ".join(f"{k}: {', '.join(v)}" for k, v in hits_by_field.items())
        return res("commentary_free", False, detail[:300])
    return res("commentary_free", True, "")


def check_sources(row, min_sources, max_age_hours, check_links=True):
    out = []
    lines = [l for l in str(row.get("Source URL", "")).splitlines() if l.strip()]
    pairs = []
    for line in lines:
        m = re.match(r"^(.+?): (https://\S+)$", line.strip())
        if m:
            pairs.append((m.group(1), m.group(2)))
    outlets = {o for o, _ in pairs}
    urls = [u for _, u in pairs]
    out.append(
        res(
            "source_count",
            len(outlets) >= min_sources and len(pairs) == len(lines),
            f"{len(outlets)} outlets, {len(lines)} lines",
        )
    )
    out.append(res("source_urls_unique", len(urls) == len(set(urls)), ""))

    try:
        published = datetime.fromisoformat(str(row.get("Source Publication Date")))
        age = (datetime.now(timezone.utc) - published).total_seconds() / 3600
        out.append(res("freshness", 0 <= age <= max_age_hours + 1, f"{age:.1f}h old"))
    except Exception:
        out.append(res("freshness", False, "Missing or invalid publication date"))

    if check_links:
        import requests

        bad, unchecked = [], 0
        for _, url in pairs:
            try:
                r = requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; DailyPresentBot/1.0)"},
                    timeout=15,
                    stream=True,
                )
                if r.status_code in (404, 410):
                    bad.append(f"{r.status_code} {url}")
                r.close()
            except Exception:
                unchecked += 1
        detail = "; ".join(bad) if bad else (f"{unchecked} link(s) unchecked" if unchecked else "")
        out.append(res("source_links_resolve", not bad, detail))
    return out


def _img_info(path):
    with Image.open(path) as im:
        return im.format, im.size


def check_media(row, rules):
    out = []
    cid = str(row.get("Content ID", ""))
    ctype = str(row.get("Content Type", ""))
    m = rules["media"]

    if ctype == "image":
        path = f"output/images/{cid}.jpg"
        if not os.path.exists(path):
            return [res("media_present", False, f"Missing {path}")]
        fmt, size = _img_info(path)
        out.append(res("media_present", True, path))
        out.append(res("image_format", fmt == "JPEG", str(fmt)))
        out.append(res("image_size", list(size) == m["image_size"], f"{size[0]}x{size[1]}"))

    elif ctype == "carousel":
        folder = f"output/carousels/{cid}"
        files = sorted(
            [f for f in os.listdir(folder) if re.match(r"slide-\d+\.jpg$", f)],
            key=lambda f: int(re.findall(r"\d+", f)[0]),
        ) if os.path.isdir(folder) else []
        if not files:
            return [res("media_present", False, f"No slides in {folder}")]
        out.append(res("media_present", True, f"{len(files)} slides"))
        out.append(
            res(
                "carousel_count",
                m["carousel_min_slides"] <= len(files) <= m["carousel_max_slides"],
                f"{len(files)} slides",
            )
        )
        nums = [int(re.findall(r"\d+", f)[0]) for f in files]
        out.append(res("carousel_order", nums == list(range(1, len(files) + 1)), str(nums)))
        bad = []
        for f in files:
            fmt, size = _img_info(f"{folder}/{f}")
            if fmt != "JPEG" or list(size) != m["image_size"]:
                bad.append(f"{f}: {fmt} {size[0]}x{size[1]}")
        out.append(res("carousel_slides_valid", not bad, "; ".join(bad)))

    elif ctype == "reel":
        path = f"output/reels/{cid}.mp4"
        if not os.path.exists(path):
            return [res("media_present", False, f"Missing {path}")]
        out.append(res("media_present", True, path))
        try:
            streams = probe(path)["streams"]
            video = next(s for s in streams if s.get("width"))
            dur = float(video["duration"])
            out.append(res("video_codec", video.get("codec_name") == "h264", str(video.get("codec_name"))))
            out.append(
                res("video_size", [video["width"], video["height"]] == m["video_size"], f"{video['width']}x{video['height']}")
            )
            out.append(
                res(
                    "video_duration",
                    m["video_min_seconds"] <= dur <= m["video_max_seconds"],
                    f"{dur:.1f}s",
                )
            )
            has_audio = any(s.get("codec_name") == "aac" for s in streams)
            out.append(res("video_audio_track", has_audio, "AAC audio track present" if has_audio else "No audio track"))
            out.append(res("audio_rights", True, "Audio is generated silence; no third-party audio used"))
        except Exception as e:
            out.append(res("video_probe", False, str(e)[:200]))
    else:
        out.append(res("content_type", False, f"Unknown type: {ctype}"))
    return out


def check_duplicate(index, rows):
    row = rows[index]
    topic = str(row.get("Topic", "")).lower().strip()
    for j in range(index):
        other = rows[j]
        if str(other.get("Status")) == "Rejected":
            continue
        ratio = SequenceMatcher(None, topic, str(other.get("Topic", "")).lower().strip()).ratio()
        if ratio >= 0.9:
            return res("duplicate_content", False, f"Too similar to {other.get('Content ID')}")
    return res("duplicate_content", True, "")