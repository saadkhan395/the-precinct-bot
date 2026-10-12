# The Daily Precinct Bot

Autonomous social media content factory for **The Daily Precinct** — a US
political news brand. Researches news, verifies it, generates content, runs
quality checks, schedules, and (soon) publishes to Facebook and Instagram.

---

## What It Does

Pipeline:

1. Fetches RSS from 9 US-news outlets.
2. Clusters headlines, verifies each story has 2+ independent outlets.
3. Writes verified stories to the `Research` tab of a Google Sheet.
4. Generates image / carousel / reel content on demand.
5. Runs QC (deterministic + AI fact-check) → Approved / Rejected.
6. Assigns Approved content to publishing slots.
7. Publishes to Facebook + Instagram. (Not yet built — Step 13.)

Schedule targets:
- 1 image post / day
- 3 carousel posts / week
- 2 reels / week

---

## Repository Structure
