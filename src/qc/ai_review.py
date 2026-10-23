"""Groq-based scoring for content, compliance, and engagement."""
import os
import json
from groq import Groq
from generate.groq_client import pick_model

SYSTEM = """You are a strict editorial QA engineer for The Daily Precinct.
Evaluate the DRAFT POST against the SOURCE TEXT.
Check:
1. Factuality: Every claim must be supported by the source. List any unsupported claims.
2. Context: Does the "why_it_matters" section provide genuine editorial value without speculation?
3. Classification: Are claims correctly attributed (e.g., "claimed" vs "stated as fact")?
4. Tone: Neutral, authoritative, non-partisan.
5. Policy: No hate speech, incitement, or medical misinformation.
Return ONLY a JSON object:
{"unsupported_claims": [], "spelling_errors": [], "neutral_tone": true, "has_context": true, "policy_flags": [], "reasoning": "brief explanation", "verdict": "pass"}
"""
# (Update the `review` function in ai_review.py to pass `why_it_matters` into the prompt as well).

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
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"AI Scoring failed: {e}")
        return {
            "design_issues": ["AI Error"], "factuality_score": 0, "compliance_score": 0, 
            "engagement_score": 0, "tone": "unknown", "spelling_errors": [], "compliance_flags": [], "reasoning": str(e)
        }
