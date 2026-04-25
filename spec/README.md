# Specs (Spec-Driven Development / SDD)

The `spec/` directory contains **feature-level specifications** written in a Spec-Driven Development (SDD) style.

## Structure

Each feature lives in `spec/<feature>/` and typically includes:

- `README.md` — suite overview and how to read it
- `INDEX.md` — navigation + reading order
- `NN-*/spec.md` — one spec per numbered step (functional requirements + acceptance criteria)

## Suites

- `spec/recent-analyses/` — “Recent Analyses” (job tracking + localStorage persistence + status polling).
- `spec/results-contract-v1/` — “Results Contract v1” (normative `results` / `result` JSON schema + enums + validation requirements).
- `spec/worker-framework/` — “Worker Framework” (state machine, atomic job claiming, pipeline framework, retry and recovery).
- `spec/audit-logging/` — “Audit Logging” (job event tracking, reference audit log, data retention cleanup).
- `spec/structured-logging/` — “Structured Logging” (Pino for frontend, structlog for backend/worker, request correlation, JSON output).
- `spec/langgraph-reference-analysis/` — “LangGraph Reference Analysis” (LangGraph graph for bibliographic reference verification: text extraction, LLM parsing/normalization, API verification, classification, report assembly).
- `spec/enhanced-search-strategies/` — “Enhanced Search Strategies” (expand normalized fields with ISSN/volume/issue/pages/publisher, multi-strategy API searches based on bibliographic style metadata, fix broken SciELO title search).
- `spec/ai-enhanced-classification/` — “AI-Enhanced Classification” (LLM-as-Judge for ambiguous references, cross-reference pattern detection, enriched decision reasons, document-level fabrication analysis).
- `spec/i18n-multilingual-support/` — “i18n Multilingual Support” (ES/PT/EN for UI and result payload: `locale` column on `analysis_jobs`, worker i18n catalog for `decisionReason`/`warnings[].message`, `next-intl` setup, language toggle, end-to-end locale propagation).
- `spec/momento-wow/` — “Momento Wow” (Authenticity Score 0-100 with color semaphore, “Try with example” sample document for zero-friction first use, client-side PDF/CSV export for shareable reports).
- `spec/share-link/` — “Share Link” (on-demand public share URLs for completed analyses: share token generation, public read endpoint, `/r/[shareToken]` page, clipboard copy with visual feedback, 7-day TTL).
- `spec/landing-page/` — “Landing Page” (marketing home at `/` with hero, problem, how-it-works, live demo, use cases, and sources sections; route restructure moving uploader to `/app`; `?sample=1` auto-load flow).
