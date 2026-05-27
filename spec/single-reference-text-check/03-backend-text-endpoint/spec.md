# Step 03 — Backend Text Endpoint

## Scope

This step specifies the FastAPI endpoint that creates a text-mode job. It covers:
- Endpoint contract (method, path, request, response)
- Validation rules
- Database insertion behavior
- Response shape (must mirror the file-mode endpoint for frontend reuse)
- Error handling

This step does NOT cover:
- The worker pipeline that processes the job (Step 04)
- The Next.js gateway that forwards requests to this endpoint (Step 05)
- The frontend UI that calls the gateway (Step 06)

## Context

The existing endpoint `POST /api/analysis/start` (`apps/backend/app/api/controllers/analysis/start.py`) accepts a file-backed payload (`storage`, `integrity`, `document`), downloads the file from Supabase, verifies its SHA-256, and inserts an `analysis_jobs` row with `input_kind='file'` (after Step 02). The text endpoint is a sibling route that accepts a much smaller payload (no file), inserts a row with `input_kind='text'`, and returns the same response shape so the frontend's polling code is unchanged.

## Requirements

### 1) Endpoint

- **Method:** `POST`
- **Path:** `/api/analysis/start-text`
- **Content-Type:** `application/json`

### 2) Request Body

```
{
  "requestId": string (required, UUID format),
  "reference": {
    "rawText": string (required, 20–2000 chars after trim)
  },
  "locale": "es" | "pt" | "en" (optional, default "es")
}
```

The endpoint MUST define a Pydantic model `VerifyTextReferenceRequest` (or equivalent) in `apps/backend/app/schemas/analysis.py`:

```python
class TextReferencePayload(BaseModel):
    rawText: str = Field(..., min_length=20, max_length=2000)

class VerifyTextReferenceRequest(BaseModel):
    requestId: UUID
    reference: TextReferencePayload
    locale: Locale = Field(default="es")
```

### 3) Validation Rules

| Rule | Constraint |
|------|------------|
| `requestId` | Valid UUID v4; same format as the file endpoint |
| `reference.rawText` | After `.strip()`: length between 20 and 2000 characters inclusive |
| `reference.rawText` | MUST NOT be all whitespace |
| `reference.rawText` | MUST NOT contain null bytes (`\x00`) |
| `reference.rawText` | MUST NOT contain ASCII control characters U+0001–U+001F **except** `\t` (U+0009), `\n` (U+000A), `\r` (U+000D); enforce via a Pydantic `@field_validator` that pre-strips or rejects control chars |
| `locale` | One of `'es'`, `'pt'`, `'en'`; same constraint as the file endpoint |

The endpoint MUST trim leading/trailing whitespace from `rawText` BEFORE the length check (i.e., the 20-char minimum applies to trimmed length).

The endpoint MUST NOT perform any LLM-based pre-validation, citation-style detection, or normalization at this stage. All such logic happens in the worker.

### 4) Database Insertion

On successful validation, the endpoint MUST:

1. Generate `poll_status_token = secrets.token_urlsafe(32)` (same as file endpoint)
2. Compute `poll_status_token_expires_at = now() + 1 hour` (same as file endpoint)
3. Insert into `analysis_jobs`:
   - `status` = `queued`
   - `stage` = `created`
   - `input_kind` = `'text'`
   - `raw_reference_text` = trimmed `rawText`
   - `bucket`, `path`, `sha256`, `source_type` = `NULL` (CHECK constraint enforces this)
   - `poll_status_token`, `poll_status_token_expires_at`
   - `locale`
4. Return the inserted `id` as `jobId`

### 5) Repository Reuse

The endpoint MUST reuse `create_analysis_job` from `apps/backend/app/services/analysis_jobs_repo.py`. **Ownership of the repo extension is assigned to this step (Step 03), not Step 02.** The implementer MUST extend `create_analysis_job` here to accept the new optional fields `input_kind` and `raw_reference_text`, and to leave the file fields unset when they are absent from the input dict. The `AnalysisJob` Pydantic / dataclass model in the same file MUST also gain the new fields with the four file fields marked optional, in this same step.

### 6) Response Shape

The endpoint MUST return the existing `VerifyAuthenticityResponse` model — same schema as `POST /api/analysis/start`. This guarantees the frontend can treat both flows uniformly:

**Success (200):**
```
{
  "success": true,
  "message": "Analysis started successfully",
  "jobId": string (UUID),
  "status": "queued",
  "jobToken": string (poll_status_token)
}
```

**Validation failure (422):**
Standard FastAPI 422 with the field-level details (Pydantic).

**Database failure (500):**
Use the existing `problem_response` helper with code `analysis_job_create_failed`.

### 7) Worker Notification

After successfully inserting the row, the endpoint MAY (but is not required to) trigger any notification mechanism that wakes the worker. Currently, the file endpoint relies on the worker's 5-second polling loop and adds no explicit notification (see the `# TODO: Call worker` comment in `start.py`). This endpoint MUST follow the same convention (no notification) for consistency.

### 8) Locale Handling

The endpoint MUST accept `locale` from the request body and persist it to `analysis_jobs.locale`. If `locale` is omitted, default to `'es'`. The Next.js gateway (Step 05) is responsible for sourcing locale from the cookie and adding it to the body before forwarding; the backend trusts the value it receives.

### 9) Authentication / Rate Limiting

No authentication is added in this step. The endpoint is public, mirroring the file endpoint. Rate limiting is OUT OF SCOPE for this step but MAY be added in a future iteration. The risk note in Step 01 § Constraints is the canonical reference.

### 10) Logging

The endpoint MUST emit at minimum the following structured log events (using `structlog`, consistent with the file endpoint):

| Event | Fields |
|-------|--------|
| `analysis_text_start_requested` | `requestId`, `locale`, `text_length` (trimmed length) |
| `analysis_text_job_created` | `job_id`, `requestId` |
| `analysis_text_repo_error` | `error_code`, `error_detail` |

The `text_length` is logged but the `rawText` content itself MUST NOT be logged (privacy and PII reasons; the text may contain author names).

### 11) Router Registration

The new endpoint MUST be registered in the analysis router aggregator (typically `apps/backend/app/api/__init__.py` or equivalent). It MUST appear under the same `/api/analysis` prefix as the file endpoint.

## Acceptance Criteria

- `POST /api/analysis/start-text` with a valid 50-char reference and `locale='es'` returns 200 with `jobId`, `status='queued'`, and `jobToken`
- The inserted row has `input_kind='text'`, `raw_reference_text=<trimmed text>`, `bucket=NULL`, `path=NULL`, `sha256=NULL`, `source_type=NULL`
- A 19-char trimmed reference returns 422 (too short)
- A 2001-char reference returns 422 (too long)
- A reference of `"   "` (only whitespace) returns 422 (effectively empty after trim)
- A request without `requestId` returns 422
- A request with `locale='fr'` returns 422
- A request with `locale='es-ES'` returns 422 (region suffixes not normalized)
- The response shape exactly matches `VerifyAuthenticityResponse` (same fields as file endpoint)
- Logs do NOT contain the contents of `rawText`
- Two simultaneous valid requests with different `requestId` produce two distinct rows with distinct `jobId` and `poll_status_token`

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Reference contains a real DOI (e.g., `https://doi.org/...`) | Accepted; the worker's `normalize_references` extracts the DOI |
| Reference is in a language other than the `locale` | Accepted; worker handles language mismatch via existing logic |
| Reference contains line breaks (`\n`) | Accepted; counted toward the 2000-char limit |
| Reference is the same text as a previous submission | Accepted; treated as an independent job (no deduplication) |
| Reference contains potentially malicious payload (SQL fragments, prompt injection) | Accepted at the endpoint; downstream defenses (Pydantic strict types, parameterized queries, OpenAlex/arXiv input sanitization) are responsible. **Note:** the security findings in `enhanced-search-strategies` MUST be remediated before this endpoint ships |
| Database insert fails (constraint violation, connection error) | Return 500 via `problem_response`; log `analysis_text_repo_error` |
| Locale cookie missing on the gateway side | Gateway sends `locale='es'`; endpoint accepts |

## Integration Points

- Step 02 (Database Schema) — provides `input_kind`, `raw_reference_text`, nullable file fields, and CHECK constraint
- Step 04 (Worker Text Mode) — reads the inserted row and processes it
- Step 05 (Frontend Gateway) — calls this endpoint with the locale-augmented body
- `apps/backend/app/api/controllers/analysis/start.py` — sibling controller; same response model
- `apps/backend/app/schemas/analysis.py` — extend with `TextReferencePayload`, `VerifyTextReferenceRequest`
- `apps/backend/app/services/analysis_jobs_repo.py` — extend `create_analysis_job` to accept the new fields

## Dependencies

- Step 02 (Database Schema)
