# Momento Wow Feature — Specification Suite

This directory contains a complete Spec-Driven Development (SDD) specification for the "Momento Wow" feature set of Biblio Checker. The suite covers three interconnected capabilities that together create a compelling first-use experience.

## Quick Start

1. **Start here:** Read `INDEX.md` for an overview and navigation guide
2. **Full specs:** Open any numbered folder (01-10) to read the detailed functional specification
3. **For implementation:** Begin with steps in the order recommended in `INDEX.md`

## What's Included

10 numbered specification directories, each containing a single `spec.md`:

- `01-overview` — Feature overview, scope, and value proposition
- `02-authenticity-score-formula` — Score computation algorithm, weights, bands
- `03-authenticity-score-component` — Frontend score display component
- `04-sample-document` — Sample PDF with curated reference mix
- `05-sample-document-integration` — "Try with example" button wiring
- `06-export-csv` — CSV generation and download
- `07-export-pdf` — PDF report generation
- `08-export-buttons-integration` — Export UI buttons and placement
- `09-i18n-catalog` — i18n keys for all three features across ES/PT/EN
- `10-acceptance-and-validation` — End-to-end acceptance criteria and testing

## Key Features Specified

- **Authenticity Score** — A single 0-100 number with color semaphore summarizing document bibliography quality
- **Sample Document** — One-click "Try with example" for zero-friction first use
- **Export PDF/CSV** — Downloadable, shareable reports for professors and reviewers

## Important Notes

**These specs contain:**
- Functional requirements (what the system does)
- Score formula and classification weights
- User flows and interactions
- Acceptance criteria (how to verify it works)
- Edge cases and error states
- Component contracts (props, behavior)
- i18n key catalog

**These specs do NOT contain:**
- Code (Python, TypeScript, CSS, etc.)
- Implementation details or architecture
- Technology choices (specific libraries or frameworks)
- Styling details (exact colors, fonts, spacing)
- Git workflows or deployment procedures

## Using These Specs

### For Frontend Engineers
- Priority: All steps (01-10) — this is a frontend-only feature set
- Start with Step 02 (score formula) and Step 04 (sample doc) as they have no dependencies
- Steps 07-08 (export PDF/buttons) are the most complex

### For QA/Testing
- Reference Step 10 for end-to-end acceptance criteria
- Each spec's "Acceptance Criteria" section is a testable checklist
- Edge cases are documented per feature

### For Product/Design
- Read Step 01 for scope and value
- Steps 03, 05, 08 describe user-facing UI and interactions

## Specification Statistics

| Metric | Value |
|--------|-------|
| Total Specifications | 10 |
| Format | Markdown |
| Estimated Read Time | 1.5-2 hours (full) or 20 min (focused) |

## Dependency Flow

```
01 (Overview)
├── 02 (Score Formula) [Foundation]
│   └── 03 (Score Component)
├── 04 (Sample Document) [Foundation]
│   └── 05 (Sample Integration)
├── 06 (Export CSV) [Independent]
├── 02 ──> 07 (Export PDF) [Depends on score formula]
│   └── 08 (Export Buttons)
│       ├── 06 (Export CSV)
│       └── 07 (Export PDF)
└── 09 (i18n Catalog) [Cross-cutting, do first]
    └── 03, 05, 08 (all UI components consume i18n)
10 (Acceptance) [Depends on all]
```

## Implementation Phases

Recommended phases for development:

| Phase | Steps | Deliverable | Can Parallelize |
|-------|-------|-------------|-----------------|
| 1A | 09, 02 | i18n keys + score utility | Yes (independent) |
| 1B | 04 | Sample PDF file | Yes (independent) |
| 2A | 03 | Score component integrated in UI | After 1A |
| 2B | 05 | Sample button integrated in dropzone | After 1B + 09 |
| 2C | 06 | CSV export utility | After 1A (needs i18n) |
| 3 | 07, 08 | PDF export + buttons in UI | After 2A + 2C |
| 4 | 10 | End-to-end validation | After all |

Phases 1A, 1B can run in parallel. Phases 2A, 2B, 2C can run in parallel.

## Cross-Suite Dependencies

This suite depends on the following existing suites:

- **results-contract-v1** — The `ResultsV1` schema, `countsByClassification`, classification enums, and confidence bands are the data source for the score and export features.
- **recent-analyses** — The `ExpandedDetail`, `JobRow`, `FileDropzone`, and `StoredJob` components/types are the integration points for all three features.
- **i18n-multilingual-support** — The existing i18n infrastructure (next-intl, message files) is extended with new keys.

---

**Status:** Complete and Ready for Implementation
**Last Updated:** April 15, 2026
**For:** Biblio Checker — Momento Wow Feature Set
