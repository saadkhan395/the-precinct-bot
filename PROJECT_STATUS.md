# PROJECT_STATUS.md — The Daily Precinct Bot

**Last updated:** 2026-10-12
**Repo:** https://github.com/Saadkhan395/the-precinct-bot
**Main branch:** `main`
**Timezone:** America/New_York
**Current phase:** Phase A — Stabilize

---

## The 19-step plan — verified status

Legend: ✅ Done & tested · 🟡 Done, untested · 🟠 Partial/buggy · 🔴 Broken · ⬜ Missing · 🔒 Blocked

| # | Step | Status | Evidence / Notes |
|---|------|--------|------------------|
| 1 | Architecture | 🟡 | Implicit in code; no ARCHITECTURE.md until now |
| 2 | GitHub repository | ✅ | Clean structure under src/ |
| 3 | Groq setup | ✅ | src/generate/groq_client.py, test-groq.yml works |
| 4 | Google Sheets | ✅ | test-sheets.yml passes; 3 tabs used |
| 5 | Meta/FB/IG setup | 🟠 | Env var name mismatch: INSTAGRAM_ACCESS_TOKEN vs IG_BUSINESS_ACCOUNT_ID |
| 6 | News research | ✅ | 9 RSS feeds, clustering, verification works |
| 7 | Competitor analysis | ✅ | src/competitors/feed_patterns.py |
| 8 | Image post generator | ✅ | output/images/IMG-*.jpg rendered |
| 9 | Carousel generator | 🟠 | 5 carousels rendered; BUG: topic collision |
| 10 | Reel generator | 🟡 | REEL-f486fb72608e.mp4 exists; end-to-end unverified |
| 11 | QC engine | 🟠 | checks.py + ai_review.py + auto_retry.py present; BUG: ships bad drafts |
| 12 | Scheduling | ✅ | schedule-content.yml runs every 15 min |
| 13 | Auto-publish FB + IG | 🔴 | No code, no workflow |
| 14 | Logging & analytics | ⬜ | Nothing |
| 15 | Weekly analysis | ⬜ | Nothing |
| 16 | Creative evolution | ⬜ | Nothing |
| 17 | E2E testing | 🟠 | 3 smoke tests only |
| 18 | Deployment | 🟠 | Only scheduling + auto-retry run on cron |
| 19 | Monitoring | ⬜ | Nothing |

**Verified completion: 10.5 / 19.**

---

## Workflows — actual triggers

| Workflow | Trigger | Automated? |
|---|---|---|
| research.yml | manual | ❌ |
| competitors.yml | manual | ❌ |
| make-image.yml | manual | ❌ |
| make-carousel.yml | manual | ❌ |
| make-reel.yml | manual | ❌ |
| qc.yml | manual | ❌ |
| schedule-content.yml | every 15 min | ✅ |
| auto-retry-rejected.yml | every 30 min | ✅ |
| test-groq.yml | manual | — |
| test-meta.yml | manual | — |
| test-sheets.yml | manual | — |

---

## Known problems (priority order)

1. 🔴 BUG-1 Topic collision in clustering (cluster.py thresholds too loose)
2. 🔴 BUG-2 carousel_copy.py returns last bad draft instead of raising
3. 🔴 BUG-3 run_qc.py never runs commentary_hits()
4. 🔴 BUG-4 Env var name mismatch across test_meta.py / .env.example / workflows
5. 🟠 BUG-5 All content workflows are manual
6. 🟠 BUG-6 requirements.txt incomplete
7. 🟠 BUG-7 README is empty
8. 🟠 BUG-9 ABC News feed URL is HTML, not RSS
9. 🔴 Step 13 missing — no publisher

---

## Exact next step

Phase A.1: Patch cluster.py (BUG-1) — one-file fix.
Then A.2 (carousel_copy raise), A.3 (QC commentary check), A.4 (env var naming),
A.5 (workflows automation), A.6 (publisher).
