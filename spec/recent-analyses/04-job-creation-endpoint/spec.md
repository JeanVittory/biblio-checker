# Step 04 — Job Creation Endpoint Extended Behavior

## Scope

This step specifies changes to the backend job creation endpoint to support the Recent Analyses feature. It covers:
- New data in the response (job ID and token)
- Timing of token generation (at job creation, before response)
- Response format and structure
- No changes to the existing request format or upload handling

This step does NOT cover:
- File upload mechanics (already handled)
- Job queuing or worker initialization
- Results generation or post-processing
- Frontend parsing of the response (see Step 07 — Frontend Data Model)
- Error handling for upload failures (only the successful submission case)

## Context

The existing job creation endpoint accepts a document (PDF or DOCX), validates it, creates a job in the database, and returns a success response. Currently, the response does not include the `jobId` or a token. The frontend needs both values to track the job in the Recent Analyses table.

## Requirements

1. When a job is successfully created, the backend must generate a unique, secure token before responding to the frontend.

2. The response must include two pieces of data:
   - `jobId`: The unique identifier for the created job
   - `jobToken`: The secret token required to query the job's status

3. Both values must be returned in the HTTP response body (format determined by backend team; likely JSON).

4. The response must clearly indicate success (HTTP 200 or 201) to differentiate from error cases.

5. The job token must be generated and stored in the database at the moment of job creation (not lazily).

6. The token expiry time must be set to exactly 1 hour after the job creation timestamp.

7. If the job creation fails (e.g., invalid file, database error), no token should be generated, and an appropriate error response should be returned (existing error handling applies).

8. The `jobId` must be a valid identifier that can be used immediately in subsequent status queries (Step 05).

9. The response must be serializable (no circular references, no function objects).

10. The endpoint must maintain backward compatibility with any existing frontend code that only reads specific fields (new fields are additive).

## Acceptance Criteria

- A successful document upload returns HTTP 200 or 201 with a JSON response containing `jobId` and `jobToken`
- Both `jobId` and `jobToken` are non-empty strings
- The `jobToken` is different for each job created in sequence
- The job can be queried using the returned `jobId` and `jobToken` immediately after creation (via Step 05 endpoint)
- The job record in the database has both `job_token` and `token_expires_at` populated
- An invalid upload (malformed file, missing file) returns an error without populating token columns
- The response structure matches the format expected by the frontend (to be verified during Step 07 integration)

## Response Format Specification

The successful response must include (at minimum) these fields:

| Field | Type | Description |
|-------|------|-------------|
| `jobId` | String | Unique identifier for the created analysis job |
| `jobToken` | String | Secret token required to authorize status queries |
| `message` (optional) | String | Human-readable success message (optional but recommended) |

Additional fields may be included (e.g., `status: "queued"`), but the above fields are required.

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Two users upload documents simultaneously | Both receive different `jobId` and `jobToken` values |
| User uploads a file, then immediately uploads another | Both jobs are created independently with separate tokens and expiry times |
| Job creation fails mid-process (database down) | No token is stored; error response is returned |
| Response is lost in transit (network failure) | User may retry; if they do, a new job is created with a new token |
| Large document (edge of file size limit) | Token generation still completes normally; file size constraints handled separately |
| Concurrent status queries on a newly created job | All queries succeed if token is valid (no race conditions) |

## Integration Point

- The returned `jobId` and `jobToken` are captured by the frontend upload handler (Step 11 — Upload Flow Integration) and stored in localStorage (Step 07 — Frontend Data Model)
- The token is sent by the frontend to the status endpoint for authorization (Step 05 — Job Status Endpoint)

## Dependencies

- Depends on Step 02 (Job Access Model) for token lifecycle definition
- Depends on Step 03 (Database Schema) for `job_token` and `token_expires_at` columns
- No blocking dependencies; can be implemented in parallel with Step 05
