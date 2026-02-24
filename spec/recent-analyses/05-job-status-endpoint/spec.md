# Step 05 — Job Status Endpoint

## Scope

This step defines a new backend endpoint for querying job status. It covers:
- Endpoint purpose and authorization model (token validation)
- Request format and required parameters
- Response format and data structure
- Success and error conditions
- Status and stage value definitions

This step does NOT cover:
- Frontend request construction (see Step 09 — Frontend Proxy Route)
- Frontend response handling (see Step 08 — Frontend Polling)
- Job creation or execution logic (separate concern)
- Results computation or formatting (assume results exist in database at job completion)
- Advanced filtering or list operations (only single job status queries)

## Context

The job status endpoint is the heart of the Recent Analyses feature. Every 4 seconds, the frontend calls this endpoint to learn whether a job is still running, has completed, or has failed. The endpoint must validate the token before returning any information.

## Requirements

1. The endpoint must accept two required parameters:
   - `jobId`: The unique job identifier
   - `jobToken`: The secret token for authorization

2. The endpoint must validate the token using the rules from Step 02:
   - Token must match the stored token for the job
   - Token must not be expired
   - If validation fails, return a generic 404 with no indication of whether the job exists

3. If validation succeeds, the endpoint must return the current state of the job:
   - `jobId`: Echo back the requested job ID
   - `status`: Current job status (one of: `queued`, `running`, `succeeded`, `failed`)
   - `stage`: Current processing stage (if applicable and non-null)
   - `result`: The analysis result (only if status is `succeeded`; null otherwise)
   - `error`: Error message (only if status is `failed`; null otherwise)
   - `submittedAt`: Timestamp when the job was created
   - `completedAt`: Timestamp when the job finished (only if status is `succeeded` or `failed`; null otherwise)

4. The response must use consistent, semantic HTTP status codes:
   - 200: Token is valid and job state is returned
   - 401: Token is invalid or expired
   - 404: Job not found (same message as 401 for security)
   - 502: Backend service unavailable or unable to query database

5. The endpoint must not expose the token or any other security-sensitive data in the response.

6. The endpoint must be fast and cacheable in principle (though caching strategy is a backend concern).

7. The endpoint must return the same response for both "job not found" and "invalid/expired token" to prevent job ID enumeration (Step 02).

## Request Format

The request must include parameters (via query string, JSON body, or headers as determined by backend design):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `jobId` | String | Yes | The unique identifier of the job to query |
| `jobToken` | String | Yes | The secret token for authorization |

## Response Format (Success, HTTP 200)

| Field | Type | Condition | Description |
|-------|------|-----------|-------------|
| `jobId` | String | Always | The queried job ID (echo-back for verification) |
| `status` | String | Always | One of: `queued`, `running`, `succeeded`, `failed` |
| `stage` | String or Null | Always | Current processing stage (e.g., "parsing", "validation") or null if N/A |
| `result` | Object or Null | Always | Analysis result payload if `status` is `succeeded`; null otherwise |
| `error` | String or Null | Always | Error message if `status` is `failed`; null otherwise |
| `submittedAt` | Timestamp | Always | ISO 8601 timestamp of job creation |
| `completedAt` | Timestamp or Null | Always | ISO 8601 timestamp of job completion (null if running/queued) |

## Status and Stage Values

**Status Values:**
- `queued`: Job has been created but not yet picked up by the worker
- `running`: Worker is actively processing the job
- `succeeded`: Job completed successfully; results are available
- `failed`: Job encountered an error and did not complete

**Stage Values (examples, not exhaustive):**
- `parsing`: Extracting text and references from the document
- `validation`: Cross-checking references against available sources
- `formatting`: Checking citation format consistency
- null: No meaningful stage information (e.g., job is queued or not yet started)

## Error Response Format

| HTTP Status | Error Message | Reason |
|-------------|---------------|--------|
| 401 | "Invalid or expired token" (or identical message to 404) | Token validation failed or token expired |
| 404 | "Invalid or expired token" (or identical message to 401) | Job not found OR invalid token (indistinguishable) |
| 502 | "Service temporarily unavailable" | Backend cannot query database or worker service |

## Acceptance Criteria

- A valid token returns HTTP 200 with job status
- An invalid token returns 401 (or 404) with a generic error message
- An expired token returns 401 (or 404) with the same error message as invalid token
- A non-existent job returns 404 (or 401) with the same error message as invalid token
- The response includes all required fields (status, stage, result, error, timestamps)
- The response does not include the job token
- A queued job returns `status: "queued"` and `null` completedAt
- A running job returns `status: "running"` and `null` result/error/completedAt
- A succeeded job returns `status: "succeeded"`, a non-null result, and a completedAt timestamp
- A failed job returns `status: "failed"`, a non-null error message, and a completedAt timestamp
- Timestamps are in ISO 8601 format (RFC 3339) or consistent with frontend expectations (see Step 09)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Job status changes between two queries (e.g., running → succeeded) | The endpoint returns the updated status; no caching issues |
| Querying a job immediately after creation | Status is `queued` (or `running` if worker is fast); stage may be null |
| Querying a job 55 minutes after creation (token still valid) | Full status is returned with no warnings |
| Querying a job 61 minutes after creation (token expired) | 401 or 404 is returned |
| Job status query during database maintenance | 502 error is returned |
| Result payload is very large (e.g., 10 MB) | Backend returns it fully; frontend handles efficiently (see Step 08 — Frontend Polling) |
| Stage value is missing from database | null is returned (handled gracefully) |
| Timestamps are at timezone boundaries | Stored and returned consistently in UTC |

## Integration Points

- Called by the frontend polling mechanism (Step 08 — Frontend Polling) every 4 seconds
- Accessed via the Next.js proxy route (Step 09 — Frontend Proxy Route)
- Response parsed and stored in frontend state (Step 07 — Frontend Data Model)

## Dependencies

- Depends on Step 02 (Job Access Model) for token validation rules
- Depends on Step 03 (Database Schema) to query `job_token` and `token_expires_at`
- Depends on Step 04 (Job Creation Endpoint) to ensure jobs are created with tokens
- Must be implemented in the backend FastAPI application
