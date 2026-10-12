# DECISIONS.md — Architecture Decision Log

## ADR-001 — Evidence-based status only
- Date: 2026-10-12
- Status: Accepted
- Context: Prior assistant fabricated an audit of an unseen repo.
- Decision: All status must cite file evidence. "UNKNOWN" is valid.
- Consequences: Slower; every claim traceable.

## ADR-002 — Audit before modification
- Status: Accepted
- Decision: No production code changes until this audit is complete.

## ADR-003 — Keep GitHub Actions as orchestrator for Phase A
- Status: Accepted
- Context: User asked to consider n8n. Current system uses GH Actions.
- Decision: Phase A stays on GitHub Actions. Reconsider n8n in Phase B only
  if measured pain justifies it.

## ADR-004 — Content IDs: prefix + cluster_id
- Status: Accepted (already implemented)
- Decision: IMG-{id}, CAR-{id}, REEL-{id}. Prevents overlap.

## ADR-005 — Clustering thresholds must tighten
- Status: Proposed, not yet applied
- Context: BUG-1 shows topic collision at jaccard=0.3.
- Proposed: min_jaccard=0.45, min_shared=4, plus named-entity overlap check.

## ADR-006 — QC must run commentary check
- Status: Proposed
- Context: BUG-2, BUG-3 — bad drafts ship.
- Proposed: run_qc.py imports and runs commentary_hits().

## ADR-007 — Publish path design (Step 13)
- Status: Pending
- Open question: FB and IG publish independently or atomic?
- Requirement: FB failure must not mark IG as failed, and vice versa.

## ADR-008 — Env var naming
- Status: Proposed
- Context: BUG-4.
- Decision: Canonical names:
  META_PAGE_ID, META_PAGE_ACCESS_TOKEN, META_IG_USER_ID,
  META_APP_ID, META_APP_SECRET.
