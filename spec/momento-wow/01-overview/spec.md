# Step 01 — Overview and Scope

## Overview

The **Momento Wow** feature set transforms Biblio Checker from a functional tool into a compelling product that captures users on first contact. It addresses three critical gaps in the current experience:

1. **No instant verdict** — Users see a table of individual reference classifications but no single, clear answer to "is this bibliography trustworthy?"
2. **High first-use friction** — A visitor must have a PDF ready and upload it before seeing any value
3. **No shareability** — A professor who validates a student's work cannot share or download the verdict

The goal is a user journey that takes under 60 seconds from arrival to a shareable result:

```
Arrive → Click "Try with example" → See Authenticity Score (0-100, color semaphore)
→ Explore per-reference details → Export PDF/CSV → Share with colleague
```

## Scope (In-Scope)

This feature set encompasses:

- A weighted Authenticity Score (0-100) computed from `ResultsV1.summary.countsByClassification`
- A three-band color semaphore (green/yellow/red) displayed prominently in the expanded result panel
- A pre-built sample PDF containing ~8 curated references with a deliberate mix of classifications
- A "Try with example" button in the file dropzone that triggers the standard upload flow
- Client-side CSV export with one row per reference and RFC 4180 escaping
- Client-side PDF export with branded header, score, summary, and per-reference details
- Export buttons (PDF + CSV) visible when a job has succeeded
- i18n keys for all user-facing strings in EN, ES, and PT
- Unit tests for the score computation and CSV generation utilities

## Non-Scope (Out-of-Scope)

Explicitly excluded from this feature set:

- Backend changes (all features are client-side only)
- New API endpoints (export is generated in the browser)
- Changes to the `ResultsV1` contract or classification enums
- Server-side PDF generation
- Authentication or user accounts
- Share links (URL-based sharing is a separate future feature)
- Batch export (multiple jobs at once)
- Custom score weights (weights are fixed in this version)
- Score history or trends over time
- PDF viewer with in-document reference highlighting
- Changes to the worker pipeline or classification logic

## Context

**Current State:**
Biblio Checker has a complete analysis pipeline (extract → parse → normalize → verify → classify → report) and a polished frontend with i18n (ES/PT/EN), dark mode, and accessibility. When a job succeeds, the user sees an expanded panel with:
- Detected/analyzed counts
- Classification breakdown table
- Per-reference cards with evidence

**Problem Addressed:**
The current results display requires cognitive effort to interpret. There is no single number or visual indicator that answers "how trustworthy is this bibliography?" Additionally, a first-time visitor must bring their own PDF, and results cannot be exported or shared.

**Solution Design:**
Three frontend-only features that layer onto the existing `ExpandedDetail` component and `FileDropzone` without modifying backend or worker code:
1. A computed score derived from existing classification counts (no new data needed)
2. A static sample PDF served from `/public/samples/` (no new endpoint needed)
3. Client-side CSV/PDF generation from existing `ResultsV1` data (no server roundtrip)

## User Personas

**Primary: First-time Visitor**
- Arrives via link or search, curious about the product
- Has no PDF ready; wants to see value before investing effort
- Needs an instant, clear verdict to decide if the tool is worth using

**Secondary: Academic Professor/Reviewer**
- Validates student bibliographies regularly
- Needs a downloadable report to attach to evaluations or share with students
- Values a single score for quick triage across multiple submissions

**Tertiary: Student/Author**
- Self-checks bibliography before submission
- Wants reassurance (green score) or warnings (yellow/red) about specific references
- May share the report with advisor for discussion

## Success Metrics

A user can:
1. Arrive on the page and click "Try with example" without uploading a file
2. See the sample analysis complete and display an Authenticity Score with color semaphore
3. Understand the score meaning without explanation (high = green = good)
4. Expand reference details to see why specific references are flagged
5. Export the results as a PDF report or CSV spreadsheet
6. Share the exported file with a colleague via email or messaging

## Constraints & Assumptions

- The `ResultsV1` contract (from `spec/results-contract-v1/`) is stable and will not change
- The existing i18n infrastructure (next-intl with `messages/{en,es,pt}.json`) is used
- All three message catalogs MUST have identical key sets (enforced by existing tests)
- The sample PDF MUST produce a range of classifications when processed by the current pipeline
- Export is client-side only; no new backend dependencies are introduced
- The score formula weights are fixed for v1; tuning is out of scope
- The PDF export library MUST support React 19 (current frontend version)

## Dependencies

- None (this is the entry point for the suite)
