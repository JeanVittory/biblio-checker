# Step 08 — Frontend Polling Behavior

## Scope

This step specifies the polling mechanism that keeps job statuses up-to-date. It covers:
- Polling interval (4 seconds)
- Which jobs are polled (active jobs only)
- Polling lifecycle (start, pause, resume, cleanup)
- When polling starts and stops
- How polling handles errors and retries
- Coordination across multiple active jobs

This step does NOT cover:
- React hooks or component implementation details (only the logical behavior)
- Network request construction (see Step 09 — Frontend Proxy Route)
- localStorage updates (see Step 07 — Frontend Data Model)
- UI refresh or re-rendering (see Step 10 — Frontend UI)
- Specific polling libraries or algorithms

## Context

The Recent Analyses table must show real-time job status without requiring the user to refresh the page. The frontend achieves this by polling the job status endpoint every 4 seconds for all active jobs (queued and running). When a job completes (succeeded or failed) or becomes inaccessible (expired), polling for that job stops.

## Requirements

1. Polling must occur at a fixed 4-second interval (4000 milliseconds) for each active job.

2. A job is considered **active** if its status is `queued` or `running`. Jobs with status `succeeded`, `failed`, or `expired` are no longer polled.

3. Polling for a specific job starts when:
   - A new job is added to the Recent Analyses list (via upload), OR
   - The page loads and localStorage contains active jobs

4. Polling for a specific job stops when:
   - The job status changes to `succeeded` (job completed successfully), OR
   - The job status changes to `failed` (job completed with error), OR
   - The job status changes to `expired` (token expired or job not found), OR
   - The user removes the job from the table, OR
   - The page unloads or the component unmounts

5. Each active job must have its own independent polling interval (no shared timers). This allows jobs to be polled concurrently without blocking each other.

6. Polling must resume automatically when the page loads (reads localStorage, resumes polling for all active jobs).

7. If a status query fails (network error, server error, malformed response):
   - The polling interval continues normally
   - The job status is not updated
   - Polling retries on the next 4-second interval
   - No exponential backoff is applied (always 4 seconds)
   - If polling fails multiple times (e.g., 3 consecutive failures), a warning badge is shown on the row (Step 06 — Error Definitions describes the user experience)

8. If a status query succeeds (HTTP 200):
   - The job's status, stage, result, error, and completedAt are updated in localStorage
   - If status changes to `succeeded`, `failed`, or `expired`, polling for that job stops
   - If status remains `queued` or `running`, polling continues on the next 4-second interval

9. If a status query fails with HTTP 401 or 404 (token invalid or expired, or job not found):
   - The job status is updated to `expired` in localStorage
   - Polling for that job stops immediately
   - The row shows the `expired` status badge

10. The polling mechanism must handle the case where multiple jobs are active simultaneously (e.g., user uploads 5 documents in a row). Each job polls independently without interfering with others.

11. Polling must not issue more than one request per job per 4-second interval, even if the interval completes while a previous request is still pending.

12. Page visibility can be considered (if the page is hidden, polling can be paused and resumed when visible), but this is optional for correctness.

## Polling Lifecycle

### Initialization (Page Load)

1. Read localStorage to get the list of stored jobs
2. For each job with status `queued` or `running`:
   - Start a new polling interval for that job
3. Set up a listener to resume polling if the page becomes visible (optional)

### Adding a New Job (Upload Success)

1. A new job is added to localStorage with status `queued`
2. Start a polling interval for the new job immediately
3. The first polling request occurs approximately 4 seconds after the job is added (not immediately)

### Polling Tick (Every 4 Seconds)

1. For each active job (status is `queued` or `running`):
   - Call the status endpoint with jobId and jobToken
   - If successful: update the job in localStorage and stop polling if status changed to terminal state
   - If failed: do not update the job; continue polling on the next interval

### Job Completion

1. Status query returns `succeeded` or `failed`
2. Job is updated in localStorage
3. Polling interval is cleared for that job
4. No further requests are issued for that job

### Job Expiration

1. Status query returns HTTP 401 or 404
2. Job status is set to `expired` in localStorage
3. Polling interval is cleared for that job
4. No further requests are issued for that job

### Cleanup (Page Unload or Component Unmount)

1. All active polling intervals are cleared
2. No requests are issued after unmounting

## Error Handling and Retries

**Transient Failures (Network, Timeout, 502, 503):**
- Polling continues on the next 4-second interval
- Job status is not updated
- User sees a loading/retry state in the UI (Step 06, 10)

**Authorization Failures (401, 404):**
- Job status is updated to `expired` immediately
- Polling stops for that job
- User sees an expired badge

**Malformed Response (Invalid JSON, Missing Fields):**
- Polling continues on the next 4-second interval
- Job status is not updated
- User sees a warning state (Step 06, 10)

**localStorage Errors (Quota Exceeded):**
- Polling can continue, but updates cannot be persisted
- User is warned about storage (Step 06)
- On next page load, non-persisted updates are lost

## Acceptance Criteria

- Polling starts immediately (within ~4 seconds) after a job is added to the table
- Polling occurs every 4 seconds (±500ms tolerance) for active jobs
- Polling stops when a job reaches a terminal state (succeeded, failed, expired)
- Polling stops when a user removes a job from the table
- Polling resumes for active jobs when the page is reloaded
- A failed status query does not stop polling; polling retries on the next interval
- A 401 or 404 response stops polling and updates job status to `expired`
- Multiple active jobs are polled concurrently without interfering
- No more than one request per job per polling interval is issued
- Polling cleanup occurs on page unload or component unmount (no memory leaks)
- Page visibility changes do not break polling (polling resumes correctly)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| User uploads a job and immediately refreshes the page | Job remains in localStorage; polling resumes for the active job |
| User uploads 5 jobs in rapid succession | All 5 jobs are polled concurrently at their own 4-second intervals |
| Polling request takes 3.5 seconds to complete | Next polling request is issued ~4 seconds after the previous one started (not after it completed) |
| Network connection is lost mid-polling | Request fails; polling retries on the next interval when connection may be restored |
| Job completes while a polling request is in flight | Response shows succeeded status; job is updated; polling stops |
| Tab is hidden for 10 minutes, then becomes visible | Polling resumes (or continues if never paused); job status may be out-of-date but will update on next poll |
| localStorage quota is exceeded during a status update | Polling continues, but update is not persisted; user is warned; data loss occurs on next page load |
| User removes a job while polling is in flight | Active polling interval is cleared; in-flight request is ignored or abandoned |
| Polling interval fires after component unmounts | Timer is cleared; no request is issued (cleanup occurred on unmount) |
| All jobs have completed or expired | No active polling intervals remain; CPU and network usage return to baseline |

## Performance Considerations

- **Concurrency:** With < 50 jobs, < 13 requests per second (50 jobs ÷ 4 seconds) is acceptable
- **Resource Usage:** Each active polling job uses minimal memory (one interval timer per job)
- **UI Updates:** Status changes trigger minimal re-renders (see Step 10 — Frontend UI)
- **Network Impact:** Regular, predictable polling interval is better than event-driven updates for backend load balancing

## Integration Points

- Reads job list from localStorage (Step 07 — Frontend Data Model)
- Calls the status endpoint via the proxy route (Step 09 — Frontend Proxy Route)
- Updates job status via `updateJob()` helper (Step 07)
- Triggers UI updates when job status changes (Step 10 — Frontend UI)
- Respects user-initiated row removal (Step 10)

## Dependencies

- Depends on Step 04 (Job Creation Endpoint) for jobId and jobToken
- Depends on Step 05 (Job Status Endpoint) for the status response format
- Depends on Step 07 (Frontend Data Model) for reading and updating jobs
- Depends on Step 09 (Frontend Proxy Route) for the status endpoint call
- Informs Step 10 (Frontend UI) about when to re-render based on polling updates
