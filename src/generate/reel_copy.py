import os
import json
from groq import Groq
from generate.groq_client import pick_model

SYSTEM = """You are a senior broadcast news editor for a US political news brand.
Write a 60-second video script based ONLY on the source text.

STRUCTURE (Total length must be 125-145 words):
- Scene 1 (0-3s): Strong verified hook. Max 10 words.
- Scene 2 (3-9s): What happened? Max 15 words.
- Scene 3 (9-18s): Background and context. Max 25 words.
- Scene 4 (18-30s): Evidence and important facts. Max 30 words.
- Scene 5 (30-42s): Consequences and impact. Max 25 words.
- Scene 6 (42-52s): What happens next? Max 20 words.
- Scene 7 (52-60s): "Follow The Daily Precinct for clear updates on the stories shaping America."

STRICT RULES:
- Neutral, authoritative tone.
- No repetitive words (e.g., "today recently").
- No medical speculation or sensational phrasing.
- No slow introductions.

Return ONLY a JSON object:
{
  "scene_1_hook": "...",
  "scene_2_context": "...",
  "scene_3_main": "...",
  "scene_4_details": "...",
  "scene_5_impact": "...",
  "scene_6_next": "...",
  "scene_7_cta": "...",
  "category": "Conflict|Controversy|Tragedy|Positive|Economy|Elections|Science|Breaking",
  "caption": "2 short sentences.",
  "why_it_matters": "1-2 sentences.",
  "hashtags": ["#USPolitics", "#PoliticsNews"]
}"""

def clean(data):
    for key in ["scene_1_hook", "scene_2_context", "scene_3_main", "scene_4_details", "scene_5_impact", "scene_6_next", "scene_7_cta", "category", "caption", "why_it_matters"]:
        if not data.get(key): raise ValueError(f"Missing {key}")
    return data

def write_reel_script(headline, outlets, source_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    user = f"Headline: {headline}\nReported by: {outlets}\n\nSOURCE:\n{source_text[:3000]}"
    
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                temperature=0.3, response_format={"type": "json_object"}
            )
            data = clean(json.loads(resp.choices[0].message.content))
            data["voiceover_script"] = " ".join([
                data["scene_1_hook"], data["scene_2_context"], data["scene_3_main"],
                data["scene_4_details"], data["scene_5_impact"], data["scene_6_next"], data["scene_7_cta"]
            ])
            return data
        except Exception as e:
            print(f"Attempt failed: {e}")
    raise RuntimeError("Failed to generate script.")
