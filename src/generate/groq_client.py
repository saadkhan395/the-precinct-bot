import json
import os
import re
from groq import Groq

PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

SYSTEM = """You are a Senior Political News Editor for The Daily Precinct.
Your voice is authoritative, accessible, and strictly non-partisan. 
Do NOT just rewrite the headline. Provide editorial value.

STRICT RULES:
- Use ONLY facts present in the source text. Never invent quotes, statistics, or events.
- Categorize the content into ONE of: "Breaking News", "Policy Explainer", "Political Timeline", "Fact Check", "Historical Context", or "Analysis".
- Distinguish facts from claims (e.g., "Senator X claimed..." vs "The report showed...").

Return ONLY a JSON object with exactly these keys:
{
  "category": "Select one from the list above",
  "hook": "max 6 words, plain, no clickbait",
  "headline": "max 14 words, factual rewrite",
  "caption": "2 short sentences summarizing what happened.",
  "why_it_matters": "1-2 sentences explaining the significance without speculation. If the source doesn't state it, infer only the immediate political impact.",
  "cta": "one short line asking readers to follow or share, max 90 characters",
  "hashtags": ["#USPolitics", "#PoliticsNews", "#DailyPrecinct"]
}
Use 3 to 5 hashtags."""

def pick_model(client):
    ids = {m.id for m in client.models.list().data}
    for m in PREFERRED:
        if m in ids:
            return m
    raise RuntimeError("No preferred Groq model available.")

def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])

def clean(data):
    for key in ("category", "hook", "headline", "caption", "why_it_matters", "cta"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing field: {key}")
        data[key] = data[key].strip()
    tags = data.get("hashtags") or []
    tags = [t if t.startswith("#") else "#" + t for t in tags if isinstance(t, str)]
    data["hashtags"] = tags[:5] or ["#USPolitics", "#DailyPrecinct"]
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
