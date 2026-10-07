from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

from verify.cluster import tokens

ET = ZoneInfo("America/New_York")
DQUOTES = ('"', "\u201c", "\u201d")


def pct(count, total):
    return round(100 * count / total) if total else 0


def analyze(items):
    by_outlet = defaultdict(list)
    for it in items:
        by_outlet[it["source"]].append(it)

    rows = []
    all_kw = Counter()
    for outlet in sorted(by_outlet):
        its = by_outlet[outlet]
        n = len(its)
        titles = [i["title"] for i in its]
        kw = Counter()
        for t in titles:
            kw.update(tokens(t))
        all_kw.update(kw)
        hours = Counter(i["published"].astimezone(ET).hour for i in its)
        times = [i["published"] for i in its]
        span_days = max(1, (max(times) - min(times)).days + 1)
        rows.append(
            [
                outlet,
                n,
                round(sum(len(t.split()) for t in titles) / n, 1),
                pct(sum("?" in t for t in titles), n),
                pct(sum(any(c.isdigit() for c in t) for t in titles), n),
                pct(sum(any(q in t for q in DQUOTES) for t in titles), n),
                pct(sum(":" in t for t in titles), n),
                ", ".join(w for w, _ in kw.most_common(8)),
                ", ".join(f"{h:02d}:00" for h, _ in hours.most_common(3)),
                round(n / span_days, 1),
            ]
        )
    rows.append(
        [
            "ALL OUTLETS",
            len(items),
            "",
            "",
            "",
            "",
            "",
            ", ".join(w for w, _ in all_kw.most_common(12)),
            "",
            "",
        ]
    )
    return rows
