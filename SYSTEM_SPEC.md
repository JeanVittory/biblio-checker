# System Spec (Thin) — Biblio Checker

## Overview

Biblio Checker validates bibliographic references from user-provided academic documents. The system’s intent is **evidence-based verification** against real, open academic sources; it does not generate citations.

Behaviorally, the system is: **UI → signed upload to storage → gateway forwards start request → backend validates + creates job row → worker processes job**. As of today, the worker exists as a polling-loop stub and does not yet advance jobs beyond creation.

This document specifies **behavior and contracts** (endpoints, invariants, job lifecycle, error semantics) rather than implementation details.

## User Journeys

### Happy Path (Primary Flow)

1. User selects a single document (PDF or DOCX).
2. The UI rejects unsupported types and files over 10 MB.
3. The UI requests a signed upload URL (`POST /api/signed-upload`).
4. The UI uploads bytes to Supabase Storage via the signed URL (direct PUT).
5. The UI requests analysis start (`POST /api/analysis-start-gateway`) with `requestId`, document metadata, and the storage locator (`bucket`, `path`).
6. The gateway forwards to the backend (`POST /api/analysis/start`) after computing integrity, and the backend creates an `analysis_jobs` row.
7. Backend returns `jobId` and `status="queued"`. The current UI shows a generic success state and does not persist `jobId`.

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
- **Outcome**: `result_json` on success; `error_code`/`error_detail` on failure.
- **Retries**: `attempts`, `max_attempts`.

### Job Lifecycle (Status + Stage)

**Status** (coarse lifecycle):

- `queued`: created and waiting to be processed.
- `running`: actively being processed by a worker.
- `succeeded`: processing completed successfully; `result_json` is expected.
- `failed`: processing completed unsuccessfully; error fields are expected.

**Stage** (fine-grained progress marker; may change while running). The table constrains `stage` to:

- `created`: job row exists; no processing has started yet.
- `extract_done`: document text was extracted and is ready for verification.
- `langgraph_running`: orchestration flow is running.
- `verifying_references`: reference verification is in progress.
- `persisting_result`: system is persisting the final `result_json`.
- `done`: processing is complete (paired with `succeeded` or `failed`).

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

- Success: `ok: true`, `success: true`, includes backend success payload (with `jobId` and `status="queued"`).
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

- Success: `{success: true, jobId, status: "queued"}`
- Errors:
  - Validation: 422.
  - Operational failures: `application/problem+json` with stable `code`.

## UI Recovery Contract

**As implemented today, the UI is ephemeral.** A page reload does not restore progress, does not re-attach to an existing `jobId`, and does not offer a resume view. The user must re-upload and restart.

Implication: jobs may exist server-side after a successful start, but they are not user-recoverable through the current UI. If recovery is required later, a read API and UI persistence mechanism must be defined.

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
- The worker does not yet persist `result_json`, so “result retention” is not defined by runtime behavior.

**Target policy (not yet implemented)**

- Uploaded files and results should be retained for **7 days** and then removed.
- Enforcing this requires a scheduled cleanup mechanism and a decision on whether `result_json` may outlive the underlying file bytes.

## Assumptions and Pending Decisions

- **Final report contract**: the structure of `result_json` is not yet defined. A stable, minimal schema is required before the frontend can render results beyond “started/success”.
- **Job retrieval contract**: there is currently no API contract to fetch job status or results by `jobId`. If `jobId` is to be used as a public opaque identifier, a read endpoint and matching access controls (e.g., RLS policy intent) must be defined.
- **Worker semantics**: polling selection criteria, concurrency, idempotency, transitions for `status`/`stage`, and retry behavior (`attempts`, `max_attempts`) are not implemented yet.
- **Retention enforcement**: 7-day retention is a target, but cleanup scheduling and the authoritative deletion source (storage vs. DB vs. both) remain to be implemented.
- **Verification Logic**: TBD — will be formalized in a dedicated domain spec once LangGraph orchestration is stabilized.