# Momento Wow Feature — Specification Index

This folder contains a complete Spec-Driven Development (SDD) breakdown of the "Momento Wow" feature set for Biblio Checker. Each specification file is a self-contained functional requirement document suitable for implementation.

## Structure

The specifications are organized into 10 logical steps, numbered 01-10. Each step is a directory containing a single `spec.md` file.

### Reading Order

**Recommended reading order for stakeholders and engineers:**

1. **01-overview** — Start here. High-level overview, scope, value proposition, and user journey.
2. **02-authenticity-score-formula** — Score algorithm, classification weights, band thresholds (foundational for display and export).
3. **03-authenticity-score-component** — Frontend component that renders the score visually.
4. **04-sample-document** — Specification for the curated sample PDF with mixed references.
5. **05-sample-document-integration** — "Try with example" button in the upload dropzone.
6. **06-export-csv** — CSV generation from ResultsV1, escaping rules, download mechanism.
7. **07-export-pdf** — PDF report generation with score, summary, and per-reference details.
8. **08-export-buttons-integration** — Export button placement and loading states in the UI.
9. **09-i18n-catalog** — Complete i18n key catalog for all three features (ES/PT/EN).
10. **10-acceptance-and-validation** — End-to-end acceptance criteria, test matrix, verification plan.

### Dependency Graph

```
01 (Overview)
 ├── 02 (Score Formula) [No deps]
 │    └── 03 (Score Component)
 │         └── 08 (Export Buttons) [partial]
 ├── 04 (Sample Document) [No deps]
 │    └── 05 (Sample Integration)
 ├── 06 (Export CSV) [No deps]
 │    └── 08 (Export Buttons)
 ├── 02 ──> 07 (Export PDF)
 │           └── 08 (Export Buttons)
 ├── 09 (i18n Catalog) [Cross-cutting]
 │    └── 03, 05, 08 (all UI steps consume i18n keys)
 └── 10 (Acceptance) [Depends on all previous steps]
```

### Quick Navigation

| Step | Title | Focus |
|------|-------|-------|
| 01 | Overview | Feature definition, scope, user journey |
| 02 | Authenticity Score Formula | Algorithm, weights, bands, edge cases |
| 03 | Authenticity Score Component | UI display, semaphore, accessibility |
| 04 | Sample Document | Curated PDF, reference mix specification |
| 05 | Sample Document Integration | Button wiring, fetch flow, error handling |
| 06 | Export CSV | CSV format, escaping, column spec, download |
| 07 | Export PDF | PDF layout, sections, styling, generation |
| 08 | Export Buttons Integration | Button placement, loading states, dynamic import |
| 09 | i18n Catalog | Complete key catalog for EN/ES/PT |
| 10 | Acceptance and Validation | End-to-end criteria, test matrix, verification |

## Key Concepts

### Authenticity Score (Steps 02, 03)

A weighted score (0-100) computed from `ResultsV1.summary.countsByClassification` that provides an instant visual verdict on bibliography quality:
- Weights favor positive classifications (`verified`=1.0, `likely_verified`=0.75)
- `processing_error` is excluded from the denominator
- Three-band semaphore: high (green, 80-100), medium (yellow, 50-79), low (red, 0-49)

### Sample Document (Steps 04, 05)

A pre-built PDF containing ~8 curated references with deliberate outcomes:
- Eliminates first-use friction (no need to have a PDF handy)
- Demonstrates the full range of classifications (verified through suspicious)
- Triggers the same upload flow as a real document

### Export (Steps 06, 07, 08)

Client-side generation of shareable reports:
- **CSV:** Tabular data for analysis in spreadsheets
- **PDF:** Branded report with score, summary, and per-reference details
- Both generated in-browser (no backend endpoint needed for MVP)

## Acceptance Criteria by Feature

### Feature: Authenticity Score
- **What:** A single number (0-100) with color semaphore that summarizes bibliography quality
- **How:** Weighted formula applied to classification counts
- **Acceptance:** User sees the score prominently when expanding a succeeded job; score is consistent with reference classifications

### Feature: Sample Document
- **What:** One-click "Try with example" to see the product in action
- **How:** Pre-built PDF served from static assets, fed into existing upload flow
- **Acceptance:** User clicks button → file appears in dropzone → submits → sees results with mixed classifications

### Feature: Export
- **What:** Downloadable PDF and CSV reports of analysis results
- **How:** Client-side generation from ResultsV1 data
- **Acceptance:** User clicks Export CSV/PDF → file downloads with correct content; PDF includes score and branded header

## No Code Zone

All files in this specification are **functional requirements only**. They contain:
- User flows and interactions
- Algorithm specifications (not code)
- Acceptance criteria
- Edge cases and error conditions
- Component contracts (props, behavior)
- i18n key catalogs

They do **NOT** contain:
- Code snippets (TypeScript, CSS, etc.)
- React component code or hooks
- CSS styling or animation code
- Library-specific APIs
- Architecture diagrams or technical design

## Implementation Phases

These specifications can be implemented in three PRs:

**PR 1 — Authenticity Score (Steps 09-partial, 02, 03):**
- i18n keys for score → score utility → score component → integrate in ExpandedDetail

**PR 2 — Sample Document (Steps 09-partial, 04, 05):**
- i18n keys for sample → create sample PDF → integrate button in FileDropzone

**PR 3 — Export (Steps 09-partial, 06, 07, 08):**
- i18n keys for export → CSV utility → PDF document → export buttons → integrate in ExpandedDetail

PRs 1 and 2 can be worked in parallel. PR 3 depends on PR 1 (uses score in PDF).

## Review Checklist

Before implementation begins:

- [ ] Product team has reviewed Step 01 (scope is agreed)
- [ ] Frontend team has reviewed Steps 02-09 (algorithm, components, and i18n are clear)
- [ ] QA team has reviewed Step 10 (acceptance criteria are testable)
- [ ] Score formula weights have been validated against sample data (Step 02)
- [ ] Sample PDF content has been agreed upon (Step 04)

## Cross-Suite Dependencies

| This Suite | Depends On | Relationship |
|------------|------------|-------------|
| Steps 02, 03, 06, 07 | `results-contract-v1` | Consumes `ResultsV1`, `countsByClassification`, classification enums |
| Steps 03, 08 | `recent-analyses` | Integrates into `ExpandedDetail` component |
| Step 05 | `recent-analyses` | Integrates into `FileDropzone` component |
| Step 09 | `i18n-multilingual-support` | Extends existing message catalogs |

---

Generated: April 15, 2026
For: Biblio Checker — Momento Wow Feature Set
