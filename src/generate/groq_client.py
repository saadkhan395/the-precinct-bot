import json
import os
import re

from groq import Groq

PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

SYSTEM = """You write posts for The Daily Precinct, a US political news brand.
Voice: calm, sharp, plain English. Politics without the noise.
STRICT RULES:
- Use ONLY facts that appear in the headline you are given. Never add names, numbers, dates, quotes, causes or details that are not in it.
- Neutral and non-partisan. No insults, no speculation, no calls to vote.
- Do not claim anything is confirmed beyond what the headline says.
Return ONLY a JSON object, nothing else, with exactly these keys:
{"hook": "max 6 words, plain, no clickbait",
 "headline": "max 14 words, factual rewrite of the given headline",
 "caption": "2 short sentences, max 300 characters, no new facts",
 "cta": "one short line asking readers to follow or share, max 90 characters",
 "hashtags": ["#USPolitics", "#PoliticsNews", "#DailyPrecinct"]}
Use 3 to 5 hashtags."""


def pick_model(client):
    ids = {m.id for m in client.models.list().data}
    for m in PREFERRED:
        if m in ids:
            return m
    raise RuntimeError("No preferred Groq model available. Found: " + ", ".join(sorted(ids)))


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def clean(data):
    for key in ("hook", "headline", "caption", "cta"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing field: {key}")
        data[key] = data[key].strip()
    tags = data.get("hashtags") or []
    tags = [t if t.startswith("#") else "#" + t for t in tags if isinstance(t, str)]
    data["hashtags"] = tags[:5] or ["#USPolitics", "#DailyPrecinct"]
    data["caption"] = data["caption"][:320]
    data["cta"] = data["cta"][:100]
    return data


def write_copy(headline, outlets):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    user = f"Headline: {headline}\nReported by: {outlets}"
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
            return clean(parse_json(resp.choices[0].message.content))
        except Exception as e:
            last = e
    raise RuntimeError(f"Groq copy failed: {last}")
