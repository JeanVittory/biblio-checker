# Step 06 — Error Definitions and Handling

## Scope

This step catalogues all error states and edge conditions in the Recent Analyses feature, and specifies the expected user-facing behavior for each. It covers:
- Error types and their causes
- HTTP status codes and error messages
- User experience for each error (what the user sees)
- Recovery strategies

This step does NOT cover:
- Implementation of error handlers (backend exception classes or frontend error boundaries)
- Retry logic or exponential backoff algorithms
- Logging, metrics, or observability details
- User support processes or escalation

## Context

The Recent Analyses feature spans the frontend and backend. Errors can occur at multiple points:
- Token validation failure (Step 02, 05)
- Database unavailability (Step 03, 05)
- Network failures (frontend)
- Storage quota exceeded (frontend localStorage)
- Malformed responses (frontend)
- Job processing failures (worker)

This step centralizes the expected behavior for all error conditions.

## Error Categories and Handling

### Category 1: Token/Authorization Errors

**Error: Invalid Token**
- Cause: User provides a token that does not match the stored token for the given job ID
- HTTP Status: 401 Unauthorized (or 404 Not Found; see Step 02)
- Error Message: "Invalid or expired token" (indistinguishable from expired token)
- User Experience: Row shows status `expired` with a gray badge and message "Token invalid or expired"
- Recovery: User cannot recover; job is no longer accessible. Row can be removed manually.

**Error: Expired Token**
- Cause: Job was created more than 1 hour ago; token has passed its expiry timestamp
- HTTP Status: 401 Unauthorized
- Error Message: "Invalid or expired token" (same as invalid token)
- User Experience: Row shows status `expired` with a gray badge and message "Token expired (1 hour limit)"
- Recovery: User cannot recover; job is no longer accessible. Row can be removed manually.

**Error: Job Not Found**
- Cause: Job ID does not exist in the database (or was deleted)
- HTTP Status: 404 Not Found (same message as invalid token, per Step 02)
- Error Message: "Invalid or expired token" (indistinguishable from authorization failures)
- User Experience: Row shows status `expired` with a gray badge and message "Job not found"
- Recovery: User cannot recover; row can be removed manually.

### Category 2: Network and Server Errors

**Error: Backend Service Unavailable**
- Cause: Backend API is down, unreachable, or overloaded
- HTTP Status: 502 Bad Gateway or 503 Service Unavailable
- Error Message: "Service temporarily unavailable" or "Unable to reach analysis service"
- User Experience: Row shows a loading/retry spinner with message "Checking status..." or "Service unavailable (will retry)"
- Recovery: Frontend automatically retries every 4 seconds until service recovers. User does not need to intervene.

**Error: Network Timeout**
- Cause: Request to backend takes longer than the timeout threshold (e.g., 30 seconds)
- HTTP Status: N/A (client-side timeout)
- Error Message: "Request timed out"
- User Experience: Row shows a loading spinner with message "Taking longer than expected..." or similar
- Recovery: Frontend automatically retries on the next polling interval. User can manually refresh if they wish.

**Error: Network Connection Lost**
- Cause: Frontend loses internet connectivity
- HTTP Status: N/A (network error)
- Error Message: Browser/network error (e.g., "NetworkError: Failed to fetch")
- User Experience: Row shows a warning badge or spinner with message "Offline (will resume when connected)"
- Recovery: Frontend resumes polling when connection is restored. Jobs remain in localStorage.

### Category 3: Frontend Data and Storage Errors

**Error: localStorage Quota Exceeded**
- Cause: Browser has less than ~5-10 MB free storage (varies by browser), and frontend tries to store a new job
- HTTP Status: N/A (browser API error)
- Error Message: "localStorage full" or similar
- User Experience: User cannot add new jobs to the table. Existing jobs remain visible. A warning message appears: "Storage full. Please clear browser data or remove old jobs."
- Recovery: User removes rows from the Recent Analyses table to free space, or clears browser data manually

**Error: localStorage Data Corrupted**
- Cause: Browser data was corrupted (rare), or data format changed between app versions
- HTTP Status: N/A (application error)
- Error Message: "Failed to read job history"
- User Experience: Recent Analyses table shows empty, with a message "Unable to load job history. Data may be corrupted."
- Recovery: User clears browser data (cookies, cache, localStorage) and starts fresh

**Error: Malformed Response from Backend**
- Cause: Backend returns valid HTTP status but invalid or missing JSON body
- HTTP Status: 200 (but payload is invalid)
- Error Message: "Failed to parse job status"
- User Experience: Row shows a warning badge with message "Unable to load status"
- Recovery: Frontend retries on the next polling interval

### Category 4: Job Processing Errors

**Error: Job Failed During Processing**
- Cause: Worker encountered an error while processing the document (e.g., file corruption, invalid format)
- HTTP Status: 200 (query succeeds; error is in job status)
- Job Status: `failed`
- Error Message: Backend returns a descriptive error (e.g., "Unable to parse PDF: corrupted file")
- User Experience: Row shows status `failed` with a red badge. Expanded row displays the error message.
- Recovery: User can remove the row or re-upload the document. No retry mechanism for the same job.

**Error: Job Timeout**
- Cause: Job is still processing after a long time (e.g., very large document)
- HTTP Status: 200 (query succeeds; job status is still `running`)
- Job Status: `running` (no timeout on the backend side, but job may run indefinitely)
- Error Message: N/A (no error, just prolonged processing)
- User Experience: Row shows status `running` with a blue spinner and message "Processing... (started Xm ago)"
- Recovery: User can wait for the job to complete, or remove the row if they no longer care

### Category 5: Frontend Integration Errors

**Error: Upload Fails to Return jobId or jobToken**
- Cause: Upload response is missing one or both required fields
- HTTP Status: 200 (but response is incomplete)
- Error Message: "Upload succeeded but job tracking failed"
- User Experience: Upload shows success message, but no row is added to the Recent Analyses table. A warning message appears: "Job uploaded but could not be tracked. Refresh the page to see it."
- Recovery: User refreshes the page (jobs are not persisted for this session). Alternatively, accept that job is untracked.

## Error Message Guidelines

Error messages displayed to users should be:
- Brief and non-technical (avoid stack traces, internal error codes)
- Action-oriented when possible (e.g., "Storage full. Please remove old jobs to continue.")
- Consistent across the application
- Displayed in the context where the error occurred (e.g., in the row or a toast notification)

## Recovery and Resilience

The system is designed to be resilient:
1. Network errors are transient; automatic retries recover without user action
2. Authorization errors are permanent; user must remove the row or accept that the job is no longer accessible
3. Storage errors block new jobs but preserve existing data; user can free space or clear data
4. Job processing errors are visible in the job row; no automatic recovery, but user can retry by uploading again

## Acceptance Criteria

- Token expiry returns HTTP 401 and a generic error message indistinguishable from invalid token
- Non-existent job returns HTTP 404 with the same generic error message as token errors
- Service unavailable returns HTTP 502 with a user-friendly message
- Network timeouts do not crash the frontend; polling resumes on the next interval
- localStorage quota errors prevent new jobs from being stored but do not affect display of existing jobs
- Malformed responses from the backend do not crash the frontend; row shows a warning state
- Job processing errors are displayed in the expanded row detail
- All user-facing error messages are non-technical and actionable

## Dependencies

- Depends on Steps 02, 04, 05 (error conditions are defined there)
- Informs Step 07 (Frontend Data Model) about error state types
- Informs Step 08 (Frontend Polling) about retry and recovery behavior
- Informs Step 10 (Frontend UI) about how to display error states
