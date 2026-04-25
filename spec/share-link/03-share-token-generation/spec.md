# Step 03 — Share Token Generation

## Scope

This step specifies the backend endpoint that generates a share token for a completed job. It covers:
- Endpoint contract (method, path, params, response)
- Authentication and authorization
- Token generation logic
- Idempotency behavior (re-sharing an already-shared job)

This step does NOT cover:
- Database schema (see Step 02)
- Public read access (see Step 04)
- Frontend UI (see Step 07)

## Context

Share tokens are generated on demand when the user clicks "Share" in the UI. The endpoint is authenticated via the existing `poll_status_token` to ensure only the original uploader can share a job. The generated token is stored on the `analysis_jobs` row and returned to the frontend, which constructs the public URL.

## Requirements

### 1) Endpoint

- **Method:** `POST`
- **Path:** `/api/analysis/share`
- **Content-Type:** `application/json`

### 2) Request Body

```
{
  "jobId": string (required, UUID format),
  "jobToken": string (required, the poll_status_token)
}
```

### 3) Authentication

The endpoint MUST validate the request using the same validation logic as the status endpoint (token matching + expiry check), but note that the transport differs: this endpoint reads `jobId` and `jobToken` from the **JSON request body** (POST), whereas the status endpoint reads them from **query parameters** (GET). The validation rules are identical; only the source of the values differs.
1. Fetch the job row by `jobId`
2. Verify `jobToken` matches the stored `poll_status_token`
3. Verify `poll_status_token_expires_at` has not passed
4. If any check fails, return the same generic error as the status endpoint (prevent enumeration)

### 4) Authorization

The endpoint MUST reject the request if the job status is NOT `succeeded`. Only completed jobs can be shared. If the job is `queued`, `running`, or `failed`, return an error.

### 5) Token Generation

When the job is valid and authorized:
1. Generate a URL-safe token using `secrets.token_urlsafe(24)` (produces 32 characters)
2. Compute expiry: `NOW() + INTERVAL '7 days'`
3. Update the job row: set `share_token` and `share_token_expires_at`

### 6) Idempotency

If the job already has a `share_token` that has NOT expired:
- Return the existing token (do NOT generate a new one)
- Return the existing `share_token_expires_at`

If the job has a `share_token` that HAS expired:
- Generate a new token (overwrite the old one)
- Set a new expiry

### 7) Response

**Success (200):**
```
{
  "success": true,
  "shareToken": string,
  "expiresAt": string (ISO 8601)
}
```

**Auth failure (401):**
Same generic error response as the status endpoint.

**Job not succeeded (409):**
```
{
  "success": false,
  "error": "job_not_completed",
  "message": "Only completed jobs can be shared"
}
```

**Job not found (404):**
Same generic error response as the status endpoint (enumeration-resistant).

### 8) Token Uniqueness

If the generated token collides with an existing one (UNIQUE constraint violation), the endpoint MUST retry with a new token up to 3 times. If all retries fail, return a 500 error.

### 9) Revoke Sharing

A separate mechanism for revoking share access is NOT required in this version. However, the schema supports it (set `share_token = NULL`). This MAY be added in a future iteration.

## Acceptance Criteria

- `POST /api/analysis/share` with valid `jobId` and `jobToken` returns a `shareToken`
- The same `jobId` + `jobToken` called again returns the same token (idempotent)
- Invalid `jobToken` returns 401 (same as status endpoint)
- Non-existent `jobId` returns 404 (same as status endpoint)
- Job with status `queued`/`running`/`failed` returns 409
- Token is 32 characters, URL-safe
- `share_token_expires_at` is set to ~7 days from now
- Expired share token is replaced with a new one on re-share
- Token collision triggers retry (up to 3 times)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Job succeeded but `poll_status_token` expired | 401 — user can no longer generate share link |
| Job already shared, token still valid | Return existing token (no new generation) |
| Job already shared, token expired | Generate new token, overwrite old one |
| Two simultaneous share requests for same job | Both return the same token (idempotent due to DB check) |
| Token collision (extremely unlikely) | Retry up to 3 times with new token |
| Job deleted between auth check and token write | Update returns 0 rows; return 404 |

### 10) Required Repository Changes

The implementation MUST update `get_analysis_job_by_id()` in `apps/backend/app/services/analysis_jobs_repo.py` to include `share_token` and `share_token_expires_at` in its SELECT column list. Without this change, the idempotency check (Section 6) cannot read the existing share token.

### 11) Token Comparison

All token comparisons (`poll_status_token` matching) MUST use `hmac.compare_digest()` for constant-time comparison, preventing timing side-channel attacks.

## Integration Points

- Step 02 (Database Schema) — writes to `share_token` and `share_token_expires_at` columns
- Step 07 (Share Button) — frontend calls this endpoint through a Next.js proxy route (see Step 05b below)
- Uses same auth validation logic as `apps/backend/app/api/controllers/analysis/status.py` (but reads from JSON body, not query params)

## Dependencies

- Step 02 (Database Schema) — columns must exist
