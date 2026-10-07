import os

from groq import Groq

from generate.groq_client import parse_json, pick_model

SYSTEM = """You write carousel posts for The Daily Precinct, a US political news brand.
Voice: calm, sharp, plain English. Politics without the noise.
STRICT RULES:
- Use ONLY facts that appear in the SOURCE TEXT you are given. If a detail is not there, leave it out. Never invent names, numbers, dates, quotes or causes.
- Write in your own words. Do not copy sentences from the source text.
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


def write_carousel(headline, outlets, source_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    user = (
        f"Headline: {headline}\nReported by: {outlets}\n\n"
        f"SOURCE TEXT:\n{source_text}"
    )
    last = None
    for _ in range(2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                temperature=0.4,
            )
            return clean_copy(parse_json(resp.choices[0].message.content))
        except Exception as e:
            last = e
    raise RuntimeError(f"Groq carousel copy failed: {last}")
