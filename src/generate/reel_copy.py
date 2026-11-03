import os
import json
from groq import Groq
from generate.groq_client import pick_model

SYSTEM = """You are a senior professional news-video editor and scriptwriter for a US political news brand.
Your task is to write a 60-second broadcast-quality news script based ONLY on the provided source text.

STRUCTURE (Total length must be between 125 and 145 words):
- Scene 1 (Hook): 00:00-00:04. Compelling question or major development. Max 10 words.
- Scene 2 (Context): 00:04-00:11. What happened, who is involved. Max 15 words.
- Scene 3 (Main Dev): 00:11-00:24. The core event. Max 25 words.
- Scene 4 (Details): 00:24-00:38. Specific verified facts, dates, numbers. Max 30 words.
- Scene 5 (Impact): 00:38-00:49. What could happen next, broader significance. Max 25 words.
- Scene 6 (Next): 00:49-00:56. What remains uncertain or the next confirmed event. Max 20 words.
- Scene 7 (CTA): 00:56-01:00. "Follow The Daily Precinct for clear updates on the stories shaping America."

STRICT RULES:
- Sound like a credible, authoritative news presenter.
- Hook Rule: Do NOT use repetitive words (e.g., "today recently"). Do NOT speculate on medical conditions or use sensational tabloid phrasing (e.g., "just suffered a stroke"). State the factual reality (e.g., "A hospitalization has put Senator X's health in the spotlight").
- Neutral, non-partisan tone.
- No slow introductions. Start immediately with the hook.

Return ONLY a JSON object with exactly these keys:
{
  "scene_1_hook": "Text for scene 1",
  "scene_2_context": "Text for scene 2",
  "scene_3_main": "Text for scene 3",
  "scene_4_details": "Text for scene 4",
  "scene_5_impact": "Text for scene 5",
  "scene_6_next": "Text for scene 6",
  "scene_7_cta": "Follow The Daily Precinct for clear updates on the stories shaping America.",
  "category": "Select one: Conflict, Controversy, Breaking, Tragedy, Positive, Economy, Elections, Science",
  "caption": "2 short sentences summarizing the story.",
  "why_it_matters": "1-2 sentences explaining the political significance.",
  "hashtags": ["#USPolitics", "#PoliticsNews", "#DailyPrecinct"]
}"""

def clean(data):
    required_keys = [
        "scene_1_hook", "scene_2_context", "scene_3_main", 
        "scene_4_details", "scene_5_impact", "scene_6_next", "scene_7_cta",
        "category", "caption", "why_it_matters"
    ]
    for key in required_keys:
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Missing field: {key}")
        data[key] = data[key].strip()
        
    tags = data.get("hashtags") or []
    tags = [t if t.startswith("#") else "#" + t for t in tags if isinstance(t, str)]
    data["hashtags"] = tags[:5]
    return data

def write_reel_script(headline, outlets, source_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    
    user = f"Headline: {headline}\nReported by: {outlets}\n\nSOURCE TEXT:\n{source_text[:3000]}"
    
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            text = resp.choices[0].message.content
            data = json.loads(text)
            clean_data = clean(data)
            
            # Combine into one script for edge-tts
            full_script = " ".join([
                clean_data["scene_1_hook"],
                clean_data["scene_2_context"],
                clean_data["scene_3_main"],
                clean_data["scene_4_details"],
                clean_data["scene_5_impact"],
                clean_data["scene_6_next"],
                clean_data["scene_7_cta"]
            ])
            
            # Check word count (target: 125-145)
            word_count = len(full_script.split())
            print(f"Script generated. Word count: {word_count} (Target: 125-145)")
            
            clean_data["voiceover_script"] = full_script
            return clean_data
            
        except Exception as e:
            print(f"Script generation attempt {attempt+1} failed: {e}")
            continue
            
    raise RuntimeError("Failed to generate Reel script after 3 attempts.")
