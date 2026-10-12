"""Headline clustering and multi-source verification.

BUG-1 v2: thresholds retuned after v1 was too strict. Added proper-noun
overlap check which prevents topic collisions. v1's jaccard=0.45 rejected
genuine multi-outlet matches; v2 uses 0.35 with name overlap required.
"""
import hashlib
import re

# Generic political vocabulary that must NOT be treated as a distinguishing
# signal on its own.
STOP = {
    "the", "and", "for", "that", "with", "this", "from", "have", "has",
    "are", "was", "were", "will", "after", "over", "into", "says", "say",
    "said", "new", "his", "her", "its", "their", "about", "than", "but",
    "not", "who", "what", "how", "why", "you", "your", "can", "could",
    "would", "should", "more", "amid", "out", "off", "all", "one", "two",
    # Generic political terms.
    "democrat", "democrats", "republican", "republicans", "senate", "house",
    "congress", "president", "trump", "biden", "white", "state", "states",
    "law", "bill", "vote", "votes", "election", "elections", "poll", "polls",
    "campaign", "administration", "government", "official", "officials",
    "report", "reports", "reported", "according", "deal", "plan",
    "plans", "news", "update", "updates", "today", "week", "year",
}

SENTENCE_STARTERS = {
    "the", "a", "an", "this", "that", "these", "those", "it", "its",
    "his", "her", "their", "there", "here", "what", "when", "where",
    "why", "how", "who", "which", "as", "at", "by", "for", "from",
    "in", "of", "on", "to", "with", "and", "but", "or", "so", "yet",
}


def tokens(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP}


def proper_nouns(text):
    """Capitalized words that appear mid-sentence."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    names = set()
    for sent in sentences:
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", sent)
        for w in words[1:]:
            if len(w) < 3:
                continue
            if w.lower() in SENTENCE_STARTERS:
                continue
            if w[0].isupper():
                names.add(w.lower())
    return names


def similar(a_tokens, b_tokens, a_names, b_names, min_jaccard, min_shared, min_name_overlap):
    shared = a_tokens & b_tokens
    if len(shared) < min_shared:
        return False
    jac = len(shared) / len(a_tokens | b_tokens)
    if jac < min_jaccard:
        return False
    # If both have proper nouns, require overlap.
    # If either has none, allow the match (short headlines often lack them).
    if a_names and b_names:
        if len(a_names & b_names) < min_name_overlap:
            return False
    return True


def cluster_items(items, min_jaccard=0.35, min_shared=3, min_name_overlap=1):
    """BUG-1 v2: 0.35/3 with proper-noun guard.

    This still blocks the 'Democrats/Paramount' collision because those two
    headlines share no mid-sentence proper nouns.
    """
    clusters = []
    for it in sorted(items, key=lambda x: x["published"]):
        toks = tokens(it["title"])
        names = proper_nouns(it["title"])
        placed = False
        for c in clusters:
            if similar(toks, c["tokens"], names, c["names"],
                       min_jaccard, min_shared, min_name_overlap):
                c["items"].append(it)
                c["tokens"] |= toks
                c["names"] |= names
                placed = True
                break
        if not placed:
            clusters.append({
                "tokens": toks,
                "names": names,
                "items": [it],
            })
    return clusters


def verify_clusters(clusters, min_sources):
    results = []
    for c in clusters:
        items = c["items"]
        by_outlet = {}
        for i in items:
            by_outlet.setdefault(i["source"], i)
        outlets = sorted(by_outlet)
        first, last = items[0], items[-1]
        ok = len(outlets) >= min_sources
        results.append(
            {
                "cluster_id": hashlib.sha1(first["url"].encode()).hexdigest()[:12],
                "status": "Verified" if ok else "Rejected",
                "reason": ""
                if ok
                else f"Only {len(outlets)} outlet(s); need {min_sources}",
                "headline": first["title"],
                "source_count": len(outlets),
                "outlets": ", ".join(outlets),
                "urls": "\n".join(f"{o}: {by_outlet[o]['url']}" for o in outlets),
                "earliest": first["published"].isoformat(timespec="seconds"),
                "latest": last["published"].isoformat(timespec="seconds"),
            }
        )
    return results
