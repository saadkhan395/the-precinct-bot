"""Groq-based scoring for content, compliance, and engagement."""
import os
import json
from groq import Groq
from generate.groq_client import pick_model

SYSTEM = """You are a Senior QA Engineer and Editorial Director for a US political news brand.
Evaluate the provided post (headline, caption, sources) and return ONLY a JSON object:
{
  "design_issues": [],
  "factuality_score": 0-100,
  "compliance_score": 0-100,
  "engagement_score": 0-100,
  "tone": "neutral|biased",
  "spelling_errors": [],
  "compliance_flags": [],
  "reasoning": "Brief explanation of scores"
}
RULES:
- factuality: 100 means every claim is supported by the source. 0 means hallucinations.
- compliance: 100 means perfectly safe for Meta. 0 means disallowed content.
- engagement: 100 means highly compelling hook, clear CTA, and excellent contextual 'why it matters'.
- tone MUST be neutral.
- Penalize if 'why_it_matters' invents implications not present in the source text.
"""

def score_post(headline, caption, source_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    user = f"HEADLINE: {headline}\nCAPTION: {caption}\nSOURCE: {source_text[:2000]}"
    
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"AI Scoring failed: {e}")
        return {
            "design_issues": ["AI Error"], 
            "factuality_score": 0, 
            "compliance_score": 0, 
            "engagement_score": 0, 
            "tone": "unknown", 
            "spelling_errors": [], 
            "compliance_flags": [], 
            "reasoning": str(e)
        }
