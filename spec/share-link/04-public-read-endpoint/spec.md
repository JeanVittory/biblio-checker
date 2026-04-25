# Step 04 — Public Read Endpoint

## Scope

This step specifies the backend endpoint that serves analysis results to anyone with a valid share token. It covers:
- Endpoint contract (method, path, params, response)
- No-auth access model
- Response format
- Expiry and error handling

This step does NOT cover:
- Token generation (see Step 03)
- Frontend rendering (see Step 06)
- Database schema (see Step 02)

## Context

The public read endpoint is the backend counterpart to the share page. When a recipient opens `/r/<token>`, the frontend fetches results from this endpoint. Unlike the status endpoint, it requires no `jobId` or `jobToken` — only the share token.

## Requirements

### 1) Endpoint

- **Method:** `GET`
- **Path:** `/api/analysis/shared/{shareToken}`
- **Path parameter:** `shareToken` (string, the share token from the URL)

### 2) No Authentication

This endpoint MUST NOT require any authentication headers, cookies, or tokens beyond the `shareToken` path parameter. It is publicly accessible.

### 3) Token Validation

The endpoint MUST:
1. Validate `shareToken` length (max 64 characters); reject longer values with 404
2. Look up the job row by `share_token` using a new repo function `get_analysis_job_by_share_token(share_token: str) -> dict | None`
3. Verify `share_token_expires_at` has not passed
4. Verify job `status` is `succeeded`

### 3.1) New Repository Function

A new function MUST be added to `apps/backend/app/services/analysis_jobs_repo.py`:

```
get_analysis_job_by_share_token(share_token: str) -> dict | None
```

- Queries `analysis_jobs` WHERE `share_token = <param>` using the UNIQUE index
- Returns the row as a dict (same columns as `get_analysis_job_by_id`) or `None` if not found
- MUST NOT expose `poll_status_token`, `job_token`, `bucket`, `path`, or `sha256` in the returned dict (exclude from SELECT)
- Follows the same error handling pattern as `get_analysis_job_by_id` (raises `AnalysisJobsRepoError` on DB errors)

### 4) Response — Success (200)

When the token is valid:

```
{
  "success": true,
  "jobId": string,
  "status": "succeeded",
  "result": ResultsV1,
  "completedAt": string (ISO 8601),
  "fileName": string | null,
  "expiresAt": string (ISO 8601, the share token expiry)
}
```

- `result` MUST be the validated `ResultsV1` payload (same validation as the status endpoint)
- If `ResultsV1` validation fails, `result` MUST be `null` (graceful degradation, same as status endpoint)
- `fileName` MUST NOT be derived from the `path` column (which exposes internal Supabase bucket structure). Instead, `fileName` MUST be sourced from a user-supplied value stored at job creation time. If no such value is available, `fileName` MUST be `null`. A future migration MAY add an `original_file_name` column to `analysis_jobs`; until then, `fileName` is `null`.

### 5) Response — Not Found (404)

Return a generic 404 for ALL error conditions:
- Share token does not exist
- Share token has expired
- Job status is not `succeeded`
- Job row was deleted

The response MUST be identical for all cases (enumeration-resistant):

```
{
  "success": false,
  "error": "not_found",
  "message": "Shared analysis not found or expired"
}
```

### 6) No Side Effects

This endpoint MUST be idempotent and read-only. It MUST NOT:
- Modify the job row
- Extend the share token expiry
- Log the access in any auditable way (future enhancement)
- Create any new database records

### 7) Rate Limiting

Rate limiting is NOT specified in this version. The endpoint inherits whatever rate limiting exists at the infrastructure level (Supabase, CDN, or reverse proxy).

### 8) CORS

The endpoint MUST be accessible from the same origin as the frontend. Since the frontend proxies through Next.js API routes, CORS headers follow the existing backend CORS configuration. No changes needed.

## Acceptance Criteria

- `GET /api/analysis/shared/<valid_token>` returns 200 with ResultsV1 data
- `GET /api/analysis/shared/<expired_token>` returns 404
- `GET /api/analysis/shared/<nonexistent_token>` returns 404
- `GET /api/analysis/shared/<token_for_failed_job>` returns 404
- Response format matches the specification above
- No authentication is required
- The endpoint does not modify any database state
- Invalid or expired tokens produce identical 404 responses

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Token exists but job was deleted by cleanup | 404 (row gone, lookup returns nothing) |
| Token valid but `result_json` fails validation | 200 with `result: null` |
| Token valid, job succeeded, result_json is null | 200 with `result: null` |
| Very long or malformed shareToken path param | 404 (no match in DB) |
| Concurrent requests with same token | Both return identical 200 (read-only) |

## Integration Points

- Step 02 (Database Schema) — reads `share_token`, `share_token_expires_at`, `result_json`
- Step 05 (Frontend Proxy) — proxied through Next.js API route
- Step 06 (Share Page) — consumed by the share page to render results
- Reuses `ResultsV1.model_validate()` from `apps/backend/app/schemas/results.py`

## Dependencies

- Step 02 (Database Schema) — share token columns must exist
