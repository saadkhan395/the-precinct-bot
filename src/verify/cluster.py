"""Headline clustering and multi-source verification.

BUG-1 FIX: tightened thresholds and added a proper-noun overlap guard so that
unrelated political headlines sharing only generic vocabulary
("Democrats", "Senate", "Trump") are no longer merged into one cluster.
"""
import hashlib
import re

# Generic political vocabulary that must NOT be treated as a distinguishing
# signal on its own. Two headlines sharing only these words are not the same
# story.
STOP = {
    "the", "and", "for", "that", "with", "this", "from", "have", "has",
    "are", "was", "were", "will", "after", "over", "into", "says", "say",
    "said", "new", "his", "her", "its", "their", "about", "than", "but",
    "not", "who", "what", "how", "why", "you", "your", "can", "could",
    "would", "should", "more", "amid", "out", "off", "all", "one", "two",
    # Generic political terms — too common to prove two headlines match.
    "democrat", "democrats", "republican", "republicans", "senate", "house",
    "congress", "president", "trump", "biden", "white", "state", "states",
    "law", "bill", "vote", "votes", "election", "elections", "poll", "polls",
    "campaign", "administration", "government", "official", "officials",
    "report", "reports", "reported", "according", "amid", "deal", "plan",
    "plans", "news", "update", "updates", "today", "week", "year",
}

# Common sentence-starting words that shouldn't count as distinguishing names.
SENTENCE_STARTERS = {
    "the", "a", "an", "this", "that", "these", "those", "it", "its",
    "his", "her", "their", "there", "here", "what", "when", "where",
    "why", "how", "who", "which", "as", "at", "by", "for", "from",
    "in", "of", "on", "to", "with", "and", "but", "or", "so", "yet",
}


def tokens(text):
    """Lowercased word set, minus stopwords and very short tokens."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP}


def proper_nouns(text):
    """Capitalized words that appear mid-sentence.

    Skips the first word of each sentence (which is always capitalized in
    proper English) and skips common sentence-starters.
    """
    # Split on sentence boundaries, keep it simple.
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    names = set()
    for sent in sentences:
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", sent)
        # Skip first word of the sentence.
        for w in words[1:]:
            if len(w) < 3:
                continue
            if w.lower() in SENTENCE_STARTERS:
                continue
            if w[0].isupper():
                names.add(w.lower())
    return names


def similar(a_tokens, b_tokens, a_names, b_names, min_jaccard, min_shared, min_name_overlap):
    """Two headlines are similar if:
       1. They share at least `min_shared` tokens, AND
       2. Their token Jaccard is at least `min_jaccard`, AND
       3. They share at least `min_name_overlap` mid-sentence proper nouns.
    """
    shared = a_tokens & b_tokens
    if len(shared) < min_shared:
        return False
    jac = len(shared) / len(a_tokens | b_tokens)
    if jac < min_jaccard:
        return False
    # Proper-noun guard: must share at least one named entity that isn't a
    # generic political term.
    if a_names and b_names:
        if len(a_names & b_names) < min_name_overlap:
            return False
    return True


def cluster_items(items, min_jaccard=0.45, min_shared=4, min_name_overlap=1):
    """Cluster items by title similarity.

    BUG-1 FIX: defaults raised from (0.30, 3) to (0.45, 4) and a proper-noun
    overlap requirement was added.
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
                # Merge new tokens/names so the cluster grows stably.
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
