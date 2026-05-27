# Step 01 — Overview and Scope

## Overview

The **Single Reference Text Check** feature lets a user paste a single bibliographic reference as plain text and obtain the same authenticity verdict that the existing file-upload flow produces. It is a parallel entry point to the document-upload pipeline: no file, no Supabase Storage, no extraction stage — the reference goes straight from the user's keyboard to OpenAlex / SciELO / arXiv verification.

The user journey:

```
User opens /app → Switches to "Pegar cita" tab → Pastes a reference (20–2000 chars)
→ Clicks "Verificar" → Job appears in Recent Analyses with "Texto" badge
→ Status polls queued → running → succeeded → User opens ExpandedDetail
→ Sees classification, confidence, evidence — same shape as a file-mode job
```

## Scope (In-Scope)

- A new `input_kind` column on `analysis_jobs` (`file` | `text`) and a `raw_reference_text` column for text input
- Migration that makes `bucket`, `path`, `sha256`, `source_type` nullable and adds a CHECK constraint enforcing per-mode field presence
- A new backend endpoint `POST /api/analysis/start-text` accepting `{requestId, reference: {rawText}, locale}`
- Worker pipeline branch for `input_kind='text'`: skip `extract_stage`, call a new langgraph entrypoint that initializes state with the pasted text and starts at `normalize_references`
- A new Next.js gateway `POST /api/analysis-text-gateway` proxying to the backend
- A new `SingleReferenceForm` UI component with a textarea, character counter, and submit button
- A tabs refactor of `apps/frontend/app/app/AppClient.tsx` exposing two modes ("Subir documento" / "Pegar cita")
- An input-kind badge in `RecentAnalyses` (`Texto` / `PDF` / `DOCX`)
- A `displayName` heuristic for text-mode jobs (first 60 chars of pasted text + ellipsis)
- i18n keys for ES, PT, EN covering tabs, paste form, validation messages, and badges

## Non-Scope (Out-of-Scope)

- Multi-paste / batch (more than one reference per submission) — single-reference only
- Pasted file content (e.g., copying the bibliography section from a Word doc) — out of scope; users with multiple references must continue using file upload
- A separate database table for text jobs — explicitly rejected; we reuse `analysis_jobs`
- A synchronous "instant verdict" endpoint — explicitly rejected; we reuse the async polling model
- Changes to `ResultsV1` schema, `useRecentAnalysesPolling`, `/api/jobs/status` proxy, `parseResultsV1`, `ExpandedDetail`, or the share-link feature
- Authentication, rate limiting beyond what already exists — addressed only as a risk note (see § Constraints)
- Saving drafts of pasted text in localStorage
- Detecting and parsing common citation styles (APA, MLA, Vancouver) before verification — that already happens inside `normalize_references`

## Context

**Current State:**
The only entry point to the analysis pipeline is the file-upload flow (`FileDropzone` → signed Supabase URL → `/api/analysis-start-gateway` → `POST /api/analysis/start`). Every `analysis_jobs` row has a `bucket`, `path`, `sha256`, and `source_type`, all NOT NULL. The worker `extract_stage` always downloads the file; the LangGraph graph always runs `extract_text` and `parse_references` before `normalize_references`.

**Problem Addressed:**
A user with a single citation in hand (e.g., a peer reviewer questioning one entry of a manuscript, a student double-checking a single source before submitting) has no way to use Biblio Checker without first wrapping that citation in a PDF or DOCX. This is unnecessary friction. The verification engine already operates on individual references (`verify_single_reference()` is a pure function); we are just exposing a thinner entry path to it.

**Solution Design:**
Add a parallel input mode that shares the existing job lifecycle. A new column `input_kind` on `analysis_jobs` (default `'file'` so existing rows are valid) discriminates between the two modes. Text-mode rows store the raw pasted text in `raw_reference_text` and leave the file fields NULL; a CHECK constraint enforces consistency. The worker reads `input_kind` from the claimed job and branches: file-mode runs the current pipeline unchanged; text-mode skips `extract_stage` and calls a new langgraph entrypoint that injects the text directly into the graph state and starts at `normalize_references`. The frontend exposes both modes as tabs and reuses the polling/storage/rendering machinery without modification beyond adding an input-kind badge.

## User Personas

**Primary: Quick-check Reviewer**
- Holds a single reference in clipboard or memory
- Wants a verdict in under a minute, no file preparation
- May be on mobile, may be on a low-bandwidth connection

**Secondary: Returning Power User**
- Uses the file-upload flow regularly for full bibliographies
- Occasionally needs to re-check a single reference without re-uploading the whole document
- Expects both modes to feel like the same product (shared history, same result UI)

## Success Metrics

1. User pastes a reference and clicks "Verificar"; a job appears in Recent Analyses within 1 second
2. The job reaches `succeeded` in the same wall-clock time as a single-reference file job (typically 5–30 seconds depending on external API latency), without the file-upload overhead
3. The result shown in `ExpandedDetail` is indistinguishable from a file-mode result for the same reference
4. Both tabs are visible and switchable without page reload, with no state leakage between them
5. The `Texto` badge in Recent Analyses correctly reflects the input mode for new and existing jobs

## Constraints & Assumptions

- The user runs Supabase migrations manually (delivery: SQL files only, never auto-applied)
- The existing dual-token model (`poll_status_token` + `job_token`) is unchanged for text-mode jobs
- The existing `claim_analysis_job` RPC works without modification, **assuming** it returns all columns of `analysis_jobs`. If the RPC enumerates columns explicitly, a sub-migration is required (see Step 04)
- The existing `i18n-multilingual-support` setup (locale cookie, worker i18n catalog) is reused; the locale propagates from cookie → gateway → backend → DB → worker exactly as in the file flow
- The existing `enhanced-search-strategies` security findings (OpenAlex filter injection, arXiv query injection — see project memory `security_findings_search_strategies`) MUST be remediated before this feature ships, because the text input shortens the path from raw user content to external API queries
- A single reference body fits in 20–2000 characters; values outside this range are rejected at the gateway and again at the backend
- The `displayName` shown in `RecentAnalyses` for text jobs is derived client-side from the first 60 characters of the pasted text (not stored separately on the server)

## Dependencies

- None within this suite (this is the entry point)
- External: results-contract-v1, recent-analyses, worker-framework, langgraph-reference-analysis, i18n-multilingual-support
