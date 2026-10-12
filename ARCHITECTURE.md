# ARCHITECTURE.md — The Daily Precinct Bot

## Purpose

Autonomous social media content factory for The Daily Precinct — a US political
news brand. Publishes to Facebook and Instagram:
- 1 image post / day
- 3 carousel posts / week
- 2 reels / week

## Intended pipeline

Discover news → Collect sources → Verify claims → Select story →
Analyze competitors → Choose format → Develop concept → Generate copy →
Produce visuals → Run QC → Repair recoverable failures → Revalidate →
Schedule → Publish → Record → Analyze → Improve.

## Actual pipeline (as built today)

## Module map

### src/research/
- fetch_news.py — RSS fetch (9 feeds), freshness filter
- run_research.py — orchestrate fetch → cluster → verify → write to Sheets

### src/verify/
- cluster.py — tokenize headlines, cluster by Jaccard similarity, verify by source count

### src/competitors/
- feed_patterns.py — extract headline patterns per outlet
- run_competitors.py — orchestrate + write CompetitorInsights tab

### src/generate/
- groq_client.py — Groq wrapper, pick_model, write_copy (image post)
- carousel_copy.py — carousel-specific copy with anti-hallucination guard
- story_text.py — fetch article summaries from RSS feeds
- make_image_post.py — orchestrator for image format
- make_carousel_post.py — orchestrator for carousel format
- make_reel_post.py — orchestrator for reel format

### src/media/
- render_image.py — Pillow renderer; 3 brand styles; font, wrap, fit_text
- render_carousel.py — slide types: cover, points, sources, CTA
- render_reel.py — vertical frame renderer; PACING variants
- build_video.py — FFmpeg concat + zoompan + fade; probe() via ffprobe

### src/qc/
- checks.py — deterministic checks: text, sources, media, duplicate
- ai_review.py — Groq-based fact-check + policy review
- auto_retry.py — retry logic for Rejected drafts
- run_qc.py — orchestrator

### src/scheduling/
- schedule_content.py — assign Approved rows to future slots; respects timezone

### src/utils/
- test_groq.py / test_meta.py / test_sheets.py — connection smoke tests

## Data flow

**Google Sheet tabs (source of truth):**
- Research — one row per verified story cluster
- Content — one row per content item
  (Draft → Approved/Rejected → Scheduled → Published)
- ReviewQueue — one row per rejected item for human review
- CompetitorInsights — weekly pattern analysis

**Content ID scheme:**
- IMG-{cluster_id} — image post
- CAR-{cluster_id} — carousel
- REEL-{cluster_id} — reel

**Media storage:** committed to repo under output/.

## External integrations

| Service | Purpose | Env vars | Status |
|---|---|---|---|
| Groq | Text gen + AI review | GROQ_API_KEY | OK |
| Google Sheets | Data store | GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON | OK |
| Meta Graph API | Publish | META_PAGE_ID, META_PAGE_ACCESS_TOKEN, IG_BUSINESS_ACCOUNT_ID | naming broken |
| RSS feeds | News source | (in config/sources.yaml) | 8/9 work |

## Testing strategy

Currently: 3 manual smoke tests. To be replaced by pytest suite (Phase A.7).

## Deployment

GitHub Actions. Free tier. Scheduled workflows: 2. Manual workflows: 9.
