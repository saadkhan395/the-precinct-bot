import os

from groq import Groq

from generate.groq_client import parse_json, pick_model

SYSTEM = """You are a strict fact-checking and compliance editor for a US political news brand's social posts.
You receive SOURCE TEXT from news outlets and a DRAFT POST (headline, caption, alt text).
Check:
1. Every factual claim in the draft must be supported by the SOURCE TEXT. List any claim that is not.
2. Spelling and grammar problems.
3. The tone must be neutral and non-partisan.
4. Policy flags: hate or harassment, incitement to violence, false or misleading election information, personal data, graphic violence, impersonation, medical misinformation.
Return ONLY a JSON object, nothing else:
{"unsupported_claims": [], "spelling_grammar_issues": [], "neutral_tone": true, "policy_flags": [], "verdict": "pass"}
Use "fail" as the verdict if there is any unsupported claim, policy flag or non-neutral tone. Use empty lists when there are no problems. Do not fail a post for wording that simply restates the source."""


def review(headline, source_text, caption, alt_text):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = pick_model(client)
    user = (
        f"SOURCE HEADLINE: {headline}\n\nSOURCE TEXT:\n{source_text or '(none, headline only)'}\n\n"
        f"DRAFT CAPTION:\n{caption}\n\nDRAFT ALT TEXT:\n{alt_text}"
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
                temperature=0,
            )
            data = parse_json(resp.choices[0].message.content)
            return {
                "unsupported_claims": list(data.get("unsupported_claims") or []),
                "spelling_grammar_issues": list(data.get("spelling_grammar_issues") or []),
                "neutral_tone": bool(data.get("neutral_tone", False)),
                "policy_flags": list(data.get("policy_flags") or []),
                "verdict": str(data.get("verdict", "fail")).lower(),
            }
        except Exception as e:
            last = e
    return {"error": str(last)[:200]}


def to_checks(r):
    if "error" in r:
        return [{"check": "ai_review", "ok": False, "detail": "AI review failed: " + r["error"]}]
    return [
        {"check": "factual_support", "ok": not r["unsupported_claims"] and r["verdict"] == "pass",
         "detail": "; ".join(map(str, r["unsupported_claims"]))[:300]},
        {"check": "spelling_grammar", "ok": not r["spelling_grammar_issues"],
         "detail": "; ".join(map(str, r["spelling_grammar_issues"]))[:300]},
        {"check": "neutral_tone", "ok": r["neutral_tone"], "detail": ""},
        {"check": "policy_flags", "ok": not r["policy_flags"],
         "detail": "; ".join(map(str, r["policy_flags"]))[:300]},
    ]
