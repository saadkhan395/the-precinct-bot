import hashlib
import re

STOP = {
    "the", "and", "for", "that", "with", "this", "from", "have", "has",
    "are", "was", "were", "will", "after", "over", "into", "says", "say",
    "said", "new", "his", "her", "its", "their", "about", "than", "but",
    "not", "who", "what", "how", "why", "you", "your", "can", "could",
    "would", "should", "more", "amid", "out", "off", "all", "one", "two",
}


def tokens(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP}


def similar(a, b, min_jaccard, min_shared):
    shared = a & b
    if len(shared) < min_shared:
        return False
    return len(shared) / len(a | b) >= min_jaccard


def cluster_items(items, min_jaccard=0.3, min_shared=3):
    clusters = []
    for it in sorted(items, key=lambda x: x["published"]):
        toks = tokens(it["title"])
        placed = False
        for c in clusters:
            if similar(toks, c["tokens"], min_jaccard, min_shared):
                c["items"].append(it)
                placed = True
                break
        if not placed:
            clusters.append({"tokens": toks, "items": [it]})
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
