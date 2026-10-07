import os
import re

from groq import Groq

from generate.groq_client import parse_json, pick_model

SYSTEM = """You write carousel posts for The Daily Precinct, a US political news brand.
Voice: calm, sharp, plain English. Politics without the noise.
STRICT RULES:
- Use ONLY facts that appear in the SOURCE TEXT you are given. If a detail is not there, leave it out. Never invent names, numbers, dates, quotes or causes.
- Mention a person, place, organization, event or date ONLY if its name appears in the SOURCE TEXT. Never add background, history or context from your own knowledge.
- Every point must restate something the SOURCE TEXT says, in your own words.
- Neutral and non-partisan. No insults, no speculation, no calls to vote.
- If the source text supports only a few points, return fewer points.
Return ONLY a JSON object, nothing else, with exactly these keys:
{"hook": "max 6 words, plain, no clickbait",
 "cover_headline": "max 14 words, factual headline",
 "slides": [
   {"title": "max 3 words, e.g. The Facts", "points": ["max 22 words each", "..."]},
   {"title": "max 3 words, e.g. The Details", "points": ["max 22 words each", "..."]}
 ],
 "caption": "2 short sentences, max 300 characters, no new facts",
 "cta": "one short line asking readers to follow or share, max 90 characters",
 "hashtags": ["#USPolitics", "#PoliticsNews", "#DailyPrecinct"]}
Each slide has 2 or 3 points. Use 3 to 5 hashtags."""


def clean_copy(data):
    for key in ("hook", "cover_headline", "caption", "cta"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing field: {key}")
        data[key] = data[key].strip()
    slides = []
    for s in data.get("slides") or []:
        title = str(s.get("title", "")).strip()[:30]
        points = [
            str(p).strip()[:170] for p in (s.get("points") or []) if str(p).strip()
        ][:3]
        if title and points:
            slides.append({"title": title, "points": points})
    if not slides:
        raise ValueError("No usable slides")
    data["slides"] = slides[:3]
    tags = data.get("hashtags") or []
    tags = [t if t.startswith("#") else "#" + t for t in tags if isinstance(t, str)]
    data["hashtags"] = tags[:5] or ["#USPolitics", "#DailyPrecinct"]
    data["caption"] = data["caption"][:320]
    data["cta"] = data["cta"][:100]
    return data


def invented_names(copy, source_text, headline):
    ref = (source_text + " " + headline).lower()
    chunks = [copy["cover_headline"], copy["caption"]]
    chunks += [p for s in copy["slides"] for p in s["points"]]
    bad = set()
    for chunk in chunks:
        for sent in re.split(r"(?<=[.!?])\s+", chunk):
            for w in sent.split()[1:]:
                w2 = re.sub(r"[^A-Za-z'-]", "", w)
                if len(w2) > 2 and w2[0].isupper():
                    base = re.sub(r"'s?$", "", w2).lower()
                    if base not in ref:
                        bad.add(w2)
    return sorted(bad)


def write_carousel(headline, outlets, source_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    base_user = (
        f"Headline: {headline}\nReported by: {outlets}\n\n"
        f"SOURCE TEXT:\n{source_text}"
    )
    user = base_user
    last_error = None
    last_copy = None
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            copy = clean_copy(parse_json(resp.choices[0].message.content))
        except Exception as e:
            last_error = e
            continue
        last_copy = copy
        bad = invented_names(copy, source_text, headline)
        if not bad:
            return copy
        user = (
            base_user
            + "\n\nYour last draft used names or words that are NOT in the SOURCE TEXT: "
            + ", ".join(bad)
            + ". Rewrite it and remove them."
        )
    if last_copy:
        return last_copy
    raise RuntimeError(f"Groq carousel copy failed: {last_error}")
