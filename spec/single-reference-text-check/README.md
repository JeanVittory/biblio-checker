# Single Reference Text Check — Specification Suite

This directory contains a complete Spec-Driven Development (SDD) specification for the **"Single Reference Text Check"** feature of Biblio Checker.

## Quick Start

1. **Start here:** Read `INDEX.md` for an overview and navigation guide
2. **Full specs:** Open any numbered folder (01-09) to read the detailed functional specification
3. **For implementation:** Begin with steps in the order recommended in `INDEX.md`

## What's Included

9 numbered specification directories, each containing a single `spec.md`:

- `01-overview` — Feature overview, scope, and value proposition
- `02-database-schema` — `input_kind`, `raw_reference_text`, NULL file fields, CHECK constraint
- `03-backend-text-endpoint` — `POST /api/analysis/start-text` contract
- `04-worker-text-mode` — Worker pipeline branch for text-only jobs
- `05-frontend-gateway` — Next.js proxy `/api/analysis-text-gateway`
- `06-input-component` — `SingleReferenceForm` component (textarea + submit)
- `07-tabs-and-recent-analyses` — AppClient tabs + RecentAnalyses input-kind badge
- `08-i18n-catalog` — i18n keys for ES/PT/EN
- `09-acceptance-and-validation` — End-to-end acceptance criteria and testing

## Key Features Specified

- **Direct text input** — User pastes a single bibliographic citation in a textarea (20–2000 chars) instead of uploading a PDF/DOCX
- **Same async pipeline** — Reuses `analysis_jobs`, polling, and `ResultsV1` contract; no new tables
- **No file extraction** — Worker skips `extract_stage` and the LangGraph `extract_text` + `parse_references` nodes; jumps straight to `normalize_references` → `verify_single_reference`
- **Tabs UI** — `/app` page exposes a "Subir documento" / "Pegar cita" toggle; both modes coexist
- **Unified history** — Text-mode jobs appear in `RecentAnalyses` alongside file jobs, distinguished by a `Texto`/`PDF`/`DOCX` badge
- **Single canonical reference** — Out of scope: multi-paste / batch; only one citation per submission

## Important Notes

**These specs contain:**
- Functional requirements (what the system does)
- Database schema changes
- API contracts (request/response format)
- User flows and interactions
- Acceptance criteria (how to verify it works)
- Edge cases and error states

**These specs do NOT contain:**
- Code (Python, TypeScript, SQL, etc.)
- Implementation details or architecture beyond the existing stack
- Technology choices beyond what's already in the stack
- Styling details (exact colors, fonts, spacing)

## Using These Specs

### For Backend Engineers
- Priority: Steps 02, 03, 04
- Focus on migration, new endpoint, worker pipeline branch

### For Frontend Engineers
- Priority: Steps 05, 06, 07, 08
- Focus on gateway proxy, input component, tabs, badge, i18n

### For QA/Testing
- Reference Step 09 for end-to-end acceptance criteria
- Each spec's "Acceptance Criteria" section is a testable checklist

## Dependency Flow

```
01 (Overview)
├── 02 (Database Schema) [Foundation]
│   ├── 03 (Backend Text Endpoint)
│   │   └── 04 (Worker Text Mode)
│   │       └── 05 (Frontend Gateway)
│   │           ├── 06 (Input Component)
│   │           │   └── 07 (Tabs & Recent Analyses)
│   │           └── 07
│   └── 04
├── 08 (i18n Catalog) [Cross-cutting]
│   └── 06, 07
└── 09 (Acceptance) [Depends on all]
```

## Implementation Phases

| Phase | Steps | Deliverable | Team |
|-------|-------|-------------|------|
| 1 | 02 | Migration SQL (delivered, applied manually) | Backend |
| 2 | 03, 04 | Backend endpoint + worker branch | Backend |
| 3 | 05, 06, 07, 08 | Gateway, input form, tabs, badge, i18n | Frontend |
| 4 | 09 | End-to-end validation | QA |

Phase 3 sub-steps (05/06/07/08) can run in parallel after Phase 2 ships.

## Cross-Suite Dependencies

- **results-contract-v1** — Text-mode jobs emit a `ResultsV1` payload identical in shape to file-mode jobs (just with a single-element `references[]`)
- **recent-analyses** — Reuses the polling table and `useRecentAnalysesPolling` hook; only the badge column is extended
- **worker-framework** — Reuses the polling/claim loop and pipeline framework; introduces a new entry path inside `run_langgraph` stage
- **langgraph-reference-analysis** — Reuses normalize → verify → classify → assemble nodes; bypasses extract-text and parse-references
- **i18n-multilingual-support** — Extends existing message catalogs for the new UI surface

---

**Status:** Draft — ready for implementation
**Last Updated:** May 3, 2026
**For:** Biblio Checker — Single Reference Text Check Feature
