import os
import json
from groq import Groq
from generate.groq_client import pick_model

SYSTEM = """You are a senior short-form video scriptwriter for a US political news brand.
Your goal is to write a 30-to-45 second Reel script that retains viewer attention.

STRUCTURE REQUIREMENTS:
1. HOOK: A 5-word maximum opening that immediately states the subject.
2. CONTEXT: Why this is happening right now.
3. EVIDENCE: The core fact or quote from the source.
4. CONCLUSION: What happens next or why it matters.

STRICT RULES:
- Use ONLY facts from the SOURCE TEXT.
- No slow introductions, no filler, no repeated statements.
- Keep sentences short and punchy for voiceover.

Return ONLY a JSON object:
{
  "category": "Policy Explainer",
  "hook": "Michigan Senate Showdown",
  "context": "The final debate turned aggressive as El-Sayed and Rogers clashed.",
  "evidence": "El-Sayed told Collins to 'shut up' during a heated exchange.",
  "conclusion": "He refuses to apologize, doubling down on the comment.",
  "voiceover_script": "The final Michigan Senate debate turned explosive. El-Sayed and Rogers clashed aggressively. At one point, El-Sayed told Collins to shut up during a heated exchange. He refuses to apologize, doubling down on the comment.",
  "caption": "The Michigan Senate debate got heated. El-Sayed refuses to back down.",
  "why_it_matters": "This debate highlights the increasing polarization in key swing states.",
  "cta": "Follow for election updates.",
  "hashtags": ["#MichiganSenate", "#Politics", "#DailyPrecinct"]
}"""

def clean(data):
    for key in ("category", "hook", "context", "evidence", "conclusion", "voiceover_script", "caption", "why_it_matters", "cta"):
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
    
    for _ in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
                temperature=0.3,
            )
            text = resp.choices[0].message.content
            start = text.find("{")
            end = text.rfind("}")
            data = json.loads(text[start:end+1])
            return clean(data)
        except Exception as e:
            print(f"Script generation attempt failed: {e}")
            continue
            
    raise RuntimeError("Failed to generate Reel script after 3 attempts.")
