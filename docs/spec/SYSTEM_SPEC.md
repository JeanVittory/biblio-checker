# System Spec (Thin) — Biblio Checker

## Overview

Biblio Checker validates bibliographic references from user-provided academic documents. The system’s intent is **evidence-based verification** against real, open academic sources; it does not generate citations.

Behaviorally, the system is: **UI → signed upload to storage → gateway forwards start request → backend validates + creates job row → UI tracks the job and polls for status → worker (future) processes job**. As of today, the worker exists as a polling-loop stub and may not advance jobs beyond creation.

This document specifies **behavior and contracts** (endpoints, invariants, job lifecycle, error semantics) rather than implementation details.

## User Journeys

### Happy Path (Primary Flow)

1. User selects a single document (PDF or DOCX).
2. The UI rejects unsupported types and files over 10 MB.
3. The UI requests a signed upload URL (`POST /api/signed-upload`).
4. The UI uploads bytes to Supabase Storage via the signed URL (direct PUT).
5. The UI requests analysis start (`POST /api/analysis-start-gateway`) with `requestId`, document metadata, and the storage locator (`bucket`, `path`).
6. The gateway forwards to the backend (`POST /api/analysis/start`) after computing integrity, and the backend creates an `analysis_jobs` row.
7. Backend returns `jobId`, `status="queued"`, and a short-lived `jobToken` (1-hour TTL).
8. The UI stores the job in localStorage (“Recent Analyses”) and starts polling for status every 4 seconds.

### Relevant Failure Flows

- **Invalid file type / MIME mismatch**: rejected client-side or by `POST /api/signed-upload` (400). No upload occurs, so cleanup is not needed.
- **File too large**: rejected client-side; may also be rejected by backend during download (413).
- **Signed URL failure**: `POST /api/signed-upload` fails (gateway error); upload cannot proceed.
- **Upload PUT failure**: the UI reports upload failure; cleanup may be attempted if `bucket/path` is known.
- **Gateway download failure**: `POST /api/analysis-start-gateway` fails; the gateway attempts best-effort deletion of the object.
- **Backend validation/operational failure**: gateway forwards, backend rejects (422 or `application/problem+json`); gateway attempts best-effort deletion of the object.

## Domain Model

### Analysis Job

An Analysis Job is a durable record (row in `analysis_jobs`) tying an uploaded document to an asynchronous verification process.

Key behavioral fields:

- **Identity**: `id` (exposed as `jobId`).
- **Lifecycle**: `status`, `stage`.
- **Input reference**: `bucket`, `path`, `sha256`.
- **Outcome**: `results` (DB) / `result` (API) on success; `error` on failure.
- **Retries**: `attempts`, `max_attempts`.

### Job Lifecycle (Status + Stage)

**Status** (coarse lifecycle):

- `queued`: created and waiting to be processed.
- `running`: actively being processed by a worker.
- `succeeded`: processing completed successfully; `results` is expected.
- `failed`: processing completed unsuccessfully; error fields are expected.

**Stage** (fine-grained progress marker; may change while running). The table constrains `stage` to:

- `created`: job row exists; no processing has started yet.
- `langgraph_running`: orchestration flow is running.
- `verifying_references`: reference verification is in progress.
- `persisting_result`: system is persisting the final `results`.

**Current system behavior**: backend creates jobs with `status="queued"` and `stage="created"`. Worker-driven transitions are not implemented yet.

## External Contracts

This section describes the minimum endpoints and semantics the system relies on.

### Frontend Gateway API (Next.js)

#### `POST /api/signed-upload`

Purpose: issue a signed upload URL for a single file.

Request semantics:

- Inputs: `fileName`, `contentType` (PDF or DOCX only).
- The server generates `requestId` and a storage `path` that includes it.

Response semantics:

- Success: `success: true` and includes `signedUrl`, `bucket`, `path` (or `filePath`), `requestId`, plus a short client expiry hint.
- Failure: `success: false` (400 for invalid input; 5xx/502 for upstream/storage issues).

#### `POST /api/analysis-start-gateway`

Purpose: validate a storage locator and request backend job creation.

Request semantics (minimum):

- Inputs: `requestId`, `document {sourceType,fileName,mimeType}`, `storage {provider,bucket,path}`.
- Bucket must match the expected uploads bucket; otherwise 400.

Response semantics:

- Success: `ok: true`, `success: true`, includes backend success payload (with `jobId`, `status="queued"`, and `jobToken`).
- Failure: `ok: false`, `success: false`. On gateway-detected failure or backend failure, the system attempts best-effort deletion of the uploaded object.

#### `POST /api/cleanup-upload`

Purpose: best-effort deletion of an uploaded object.

Semantics:

- Rejects unexpected buckets (400).
- Deletion is attempted, but the endpoint does not guarantee deletion success.

### Backend API (FastAPI)

#### `POST /api/analysis/start`

Purpose: validate the referenced upload and create an analysis job row.

Request invariants (enforced):

- `storage.path` is safe (no traversal/absolute path/backslash/null byte).
- `storage.path` contains `requestId` and its filename equals `document.fileName`.
- `storage.bucket` is allowlisted.
- `document.sourceType`, `document.mimeType`, and filename extension are consistent.
- Stored bytes match `integrity.sha256`.
- Text extraction is feasible and within configured size limits.

Response semantics:

- Success: `{success: true, jobId, status: "queued", jobToken}`
- Errors:
  - Validation: 422.
  - Operational failures: `application/problem+json` with stable `code`.

#### `GET /api/analysis/status`

Purpose: retrieve job status (and result/error when available) using `jobId` + `jobToken`.

Request semantics (minimum):

- Query params: `jobId`, `jobToken` (required).
- Token checks:
  - Token must match the stored token for the job.
  - Token must not be expired (current TTL is 1 hour).
- Enumeration-resistant behavior:
  - If the job does not exist OR the token is invalid/expired, the backend responds with a generic message.

Response semantics:

- Success (200): `{ jobId, status, stage?, result?, error?, submittedAt, completedAt? }`
- Notes:
  - The backend stores the success payload in a `results` column and returns it as `result` in the status response.
  - `result` is meaningful only when `status="succeeded"`:
    - If `status != "succeeded"`, `result` MUST be `null` or absent.
    - If `status="succeeded"` and the stored payload does not validate as Results Contract v1, `result` MUST be returned as `null` (backward compatibility; the job `status` MUST NOT change).
- Invalid/expired token: 401 with `{ error: "Invalid or expired token" }`
- Job not found (or treated as not found): 404 with `{ error: "Invalid or expired token" }`
- Transient service failure: 502 with `{ error: "Service temporarily unavailable" }`

### Result Payload Contract (Results Contract v1)

The system has a **strict, versioned** contract for the analysis success payload:

- DB column name (typical): `analysis_jobs.results`
- API field name: `result` (returned by `GET /api/analysis/status` on success)

**Source of truth (as implemented):**

- Backend (authoritative validation model): `apps/backend/app/schemas/results.py`
- Frontend (authoritative TS contract): `apps/frontend/types/results.ts`
- Frontend (authoritative runtime validator): `apps/frontend/lib/validation/resultsV1.ts`

**Coherence rule (normative):**

- Any change to the `result` contract MUST be applied to **both** backend and frontend sources of truth above (and their tests) in the same change set.
  - If you update the backend model, you MUST update the frontend types + Zod validator to match.
  - If you update the frontend types, you MUST update the backend model to match.

Note: `spec/results-contract-v1/` documents the v1 contract snapshot used for this feature, but it may be superseded by future specs; the code-level schemas/types above are the authoritative contract for the running system.

#### Presence / absence rules

- `result` MUST be treated as defined only when `status="succeeded"`.
- When `status != "succeeded"`, `result` MUST be `null` or absent.
- When `status="succeeded"`:
  - If stored `results` validates as Results Contract v1, the backend returns it as `result`.
  - If stored `results` is missing/legacy/invalid, the backend returns `result=null` (backward compatibility; it MUST NOT crash and MUST NOT change job status).

#### Root object shape (ResultsV1, `schemaVersion="1.0"`)

`result` is a JSON object with **required** fields:

- `schemaVersion`: string, MUST equal `"1.0"`.
- `reportLanguage`: string, MUST equal `"es"`.
- `pipeline`: object, required:
  - `name`: string, required, non-empty.
  - `version`: string, required, non-empty.
- `summary`: object, required (see below).
- `references`: array of `ReferenceResult`, required (may be empty).
- `warnings`: array of `Warning`, required (may be empty).

#### `summary`

Required fields:

- `totalReferencesDetected`: integer, `>= 0`.
- `totalReferencesAnalyzed`: integer, `>= 0`.
- `countsByClassification`: object with **all** classification keys exactly once, values are integers `>= 0`:
  - `verified`, `likely_verified`, `ambiguous`, `not_found`, `suspicious`, `processing_error`

#### `references[]` items (`ReferenceResult`)

Each item is an object with **required** fields:

- `referenceId`: string, required, non-empty; MUST be unique within the report.
- `rawText`: string, required, non-empty.
- `normalized`: object, required:
  - `title`: string or `null`
  - `authors`: array of strings (may be empty)
  - `year`: integer or `null`
  - `venue`: string or `null`
  - `doi`: string or `null`
  - `arxivId`: string or `null`
- `classification`: `classification` enum (closed; see below).
- `confidenceScore`: number in `[0.0, 1.0]` or `null` (see matrix/nullability rules below).
- `confidenceBand`: `confidenceBand` enum or `null` (see matrix/nullability rules below).
- `manualReviewRequired`: boolean (forced by classification; see below).
- `reasonCode`: `reasonCode` enum (closed; see below).
- `decisionReason`: string, required, non-empty; user-facing Spanish explanation.
- `evidence`: array of `EvidenceItem`, required (may be empty).

#### `evidence[]` items (`EvidenceItem`)

Each evidence item is an object with **required** fields:

- `source`: string, required, non-empty.
- `matchType`: string, required, non-empty.
- `score`: number, required, MUST be in `[0.0, 1.0]`.
- `matchedRecord`: object, required:
  - `externalId`: string, required, non-empty.
  - `title`: string or `null`
  - `year`: integer or `null`
  - `doi`: string or `null`
  - `url`: string or `null`

#### `warnings[]` items (`Warning`)

Each warning is an object with **required** fields:

- `code`: string, required, non-empty (stable identifier).
- `message`: string, required, non-empty; user-facing Spanish explanation.
- `referenceId`: string or `null` (when warning applies to a specific reference).
- `details`: object or `null` (free-form diagnostic payload).

#### Closed enums (v1)

- `classification`:
  - `verified`, `likely_verified`, `ambiguous`, `not_found`, `suspicious`, `processing_error`
- `confidenceBand`:
  - `very_high`, `high`, `medium`, `low`, `very_low`
- `reasonCode`:
  - `exact_doi_match`
  - `exact_identifier_match`
  - `strong_metadata_match`
  - `multiple_plausible_candidates`
  - `insufficient_metadata`
  - `no_match_any_source`
  - `strong_doi_conflict`
  - `cross_source_metadata_conflict`
  - `source_timeout_partial`
  - `reference_processing_failure`

#### Compatibility matrix + forced nullability (v1)

For each `ReferenceResult`, the pair (`classification`, `confidenceBand`) MUST satisfy:

- `verified` → `confidenceBand ∈ { high, very_high }`
- `likely_verified` → `confidenceBand ∈ { medium, high }`
- `ambiguous` → `confidenceBand ∈ { low, medium }`
- `not_found` → `confidenceBand ∈ { very_low, low }`
- `suspicious` → `confidenceBand ∈ { medium, high, very_high }`
- `processing_error` → `confidenceBand = null`

If `classification = "processing_error"` then:

- `confidenceBand` MUST be `null`
- `confidenceScore` MUST be `null`
- `manualReviewRequired` MUST be `true`

`manualReviewRequired` MUST be:

- `false` for `classification ∈ { verified, likely_verified }`
- `true` for `classification ∈ { ambiguous, not_found, suspicious, processing_error }`

#### Cross-field invariants (v1)

The report MUST satisfy:

- `references.length == summary.totalReferencesAnalyzed`
- `sum(summary.countsByClassification[*]) == summary.totalReferencesAnalyzed`
- `summary.totalReferencesAnalyzed <= summary.totalReferencesDetected`
- `referenceId` values MUST be unique within `references[]`

### Frontend Status Proxy + Polling (Recent Analyses)

The UI uses a server-side proxy endpoint to poll the backend without exposing internal service URLs in the browser.

#### `GET /api/jobs/status`

- Purpose: proxy to backend `GET /api/analysis/status`.
- Query params: `jobId`, `jobToken` (required).
- Timeout: upstream request has a hard timeout (30 seconds).

Polling behavior (as implemented):

- Interval: every **4 seconds** per active job.
- Polling active statuses: `queued`, `running`.
- Terminal statuses: `succeeded`, `failed` (polling stops automatically).
- If the proxy returns **401** or **404**, the UI marks the job as **`expired`** (frontend-only state) and stops polling.
- Transient failures (network errors, 502): silently retried on the next interval.
- Persistence: jobs are stored in browser localStorage and polling resumes on page load for `queued`/`running` jobs.

## UI Recovery Contract

**As implemented today, the UI persists Recent Analyses state in localStorage.** A page reload restores the job list and resumes polling for any jobs still in `queued` or `running` status (per stored data).

Implication: jobs are recoverable on the same browser/device as long as localStorage is retained and the job token has not expired.

## Error Taxonomy

### User Errors (Client-Correctable)

- Invalid file type / MIME mismatch.
- File too large (exceeds max allowed size).
- Invalid request payload shape.
- Integrity mismatch (declared SHA-256 does not match stored bytes).
- Invalid storage locator (bucket not allowed, unsafe path, requestId/path mismatch).

### System Errors (Not User-Correctable Without Retry)

- Storage not found/unauthorized/download failures.
- Server misconfiguration.
- Text extraction unavailable (missing dependencies) or extraction failure.
- Database authorization failure or job insert failure.

### Stable Error Codes (Backend)

Backend operational errors use `application/problem+json` with a stable `code`, including:

- `integrity_sha_mismatch`
- `storage_not_found`, `storage_unauthorized`, `storage_download_failed`
- `file_too_large`
- `server_misconfigured`
- `text_extraction_unavailable`, `text_extraction_failed`, `extracted_text_too_large`
- `db_unauthorized`, `analysis_job_create_failed`

## Retention and Cleanup

**Inferred current behavior**

- Uploaded file cleanup is **best-effort** and primarily triggered on gateway-detected failures (download failure, backend failure, unexpected errors).
- On successful analysis start, there is **no automatic deletion** of the uploaded document.
- The worker does not yet persist `results`, so “result retention” is not defined by runtime behavior.

**Target policy (not yet implemented)**

- Uploaded files and results should be retained for **7 days** and then removed.
- Enforcing this requires a scheduled cleanup mechanism and a decision on whether `results` may outlive the underlying file bytes.

## Assumptions and Pending Decisions

- **Final report contract**: The authoritative `result` contract is the code-level schema/types (`apps/backend/app/schemas/results.py`, `apps/frontend/types/results.ts`, `apps/frontend/lib/validation/resultsV1.ts`). Feature specs may be superseded over time.
- **Worker semantics**: selection criteria, concurrency, idempotency, transitions for `status`/`stage`, and retry behavior (`attempts`, `max_attempts`) are not implemented yet.
- **Retention enforcement**: 7-day retention is a target, but cleanup scheduling and the authoritative deletion source (storage vs. DB vs. both) remain to be implemented.
- **Verification Logic**: TBD — will be formalized in a dedicated domain spec once LangGraph orchestration is stabilized.
