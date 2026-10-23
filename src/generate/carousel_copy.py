import os
import re
from groq import Groq

from generate.groq_client import parse_json, pick_model

SYSTEM = """You write multi-slide carousels for The Daily Precinct.
Voice: calm, sharp, plain English. Facts first.

STRICT RULES:
- Use ONLY facts from the SOURCE TEXT. Never invent names, quotes, or causes.
- Categorize the content into ONE of: "Breaking News", "Policy Explainer", "Political Timeline", "Fact Check", "Historical Context", or "Analysis".
- Every point must restate something the SOURCE TEXT says. No commentary or analysis.

Return ONLY a JSON object with exactly these keys:
{
  "category": "Select one from the list above",
  "hook": "max 6 words, plain",
  "cover_headline": "max 14 words, factual",
  "slides": [
    {"title": "e.g., The Facts", "points": ["max 22 words each", "..."]},
    {"title": "e.g., The Context", "points": ["max 22 words each", "..."]}
  ],
  "caption": "2 short sentences summarizing the story.",
  "why_it_matters": "1-2 sentences explaining the political significance based ONLY on the provided text.",
  "cta": "one short line asking readers to follow",
  "hashtags": ["#USPolitics", "#PoliticsNews", "#DailyPrecinct"]
}
Each slide has 2 points. Use 3 to 5 hashtags."""

COMMENTARY = (
    "highlight", "underscore", "signal", "reveal", "stakes", "raises questions",
    "sheds light", "paints a picture", "crucial", "significant", "the clash",
)

def clean_copy(data):
    for key in ("category", "hook", "cover_headline", "caption", "why_it_matters", "cta"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing field: {key}")
        data[key] = data[key].strip()
    slides = []
    for s in data.get("slides") or []:
        title = str(s.get("title", "")).strip()[:30]
        points = [str(p).strip()[:170] for p in (s.get("points") or []) if str(p).strip()][:3]
        if title and points:
            slides.append({"title": title, "points": points})
    if not slides:
        raise ValueError("No usable slides")
    data["slides"] = slides[:3]
    tags = data.get("hashtags") or []
    tags = [t if t.startswith("#") else "#" + t for t in tags if isinstance(t, str)]
    data["hashtags"] = tags[:5] or ["#USPolitics", "#DailyPrecinct"]
    return data

def invented_names(copy, source_text, headline):
    ref = (source_text + " " + headline).lower()
    chunks = [copy["cover_headline"], copy["caption"], copy["why_it_matters"]]
    chunks += [p for s in copy["slides"] for p in s["points"]]
    bad = set()
    for chunk in chunks:
        for sent in re.split(r"(?<=[.!?])\s+", chunk):
            for w in sent.split()[1:]:
                w2 = re.sub(r"[^A-Za-z'-]", "", w)
                if len(w2) > 2 and w2[0].isupper():
                    base = re.sub(r"'s?$", "", w2).lower()
                    if base not in ref and w2.lower() not in ref:
                        bad.add(w2)
    return sorted(bad)

def commentary_hits(copy):
    text = " ".join(
        [copy["cover_headline"], copy["caption"], copy["why_it_matters"]]
        + [p for s in copy["slides"] for p in s["points"]]
    ).lower()
    return [w for w in COMMENTARY if w in text]

def write_carousel(headline, outlets, source_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    base_user = f"Headline: {headline}\nReported by: {outlets}\n\nSOURCE TEXT:\n{source_text}"
    user = base_user
    last_error = None
    last_copy = None
    last_bad = []
    last_comment = []

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                temperature=0.2,
            )
            copy = clean_copy(parse_json(resp.choices[0].message.content))
        except Exception as e:
            last_error = e
            continue

        last_copy = copy
        bad = invented_names(copy, source_text, headline)
        comment = commentary_hits(copy)
        last_bad = bad
        last_comment = comment

        if not bad and not comment:
            return copy

        notes = []
        if bad: notes.append("names NOT in SOURCE: " + ", ".join(bad))
        if comment: notes.append("commentary words: " + ", ".join(comment))
        user = base_user + "\n\nYour last draft had problems: " + "; ".join(notes) + ". Rewrite and fix."

    raise RuntimeError(f"Carousel copy failed. Invented: {last_bad}. Commentary: {last_comment}.")
