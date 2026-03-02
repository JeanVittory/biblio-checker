# Step 10 — Retry and Recovery

## Scope

- Define the complete retry strategy: which errors are retried, how many times, and what happens when retries are exhausted
- Define the crash recovery mechanism via lease expiry
- Define the error classification table
- Define the end-to-end failure scenarios and expected outcomes

**Out of scope:** Implementation of new code (this step describes behavior already implemented across Steps 02–09). Alerting and monitoring (future work).

## Context

The retry and recovery behavior is distributed across several components:
- The RPC function (Step 02) handles attempt tracking and lease-based reclaiming
- The pipeline runner (Step 05) classifies errors and decides between requeue and permanent failure
- The repository (Step 04) executes the requeue or failure DB writes
- The polling loop (Step 09) provides the natural retry interval

This spec consolidates all retry behavior in one place for clarity and serves as the verification reference for end-to-end testing.

## Requirements

### 1. Error Classification

Every error that can occur during job processing falls into one of three categories:

| Category | Exception type | `transient` | Retry? | Example |
|----------|---------------|-------------|--------|---------|
| **Terminal** | `TerminalJobError` | N/A | Never | SHA-256 mismatch, result schema validation failure |
| **Transient** | `StageError(transient=True)` | `True` | Yes, if attempts remain | Storage download timeout, LangGraph API error |
| **Non-transient** | `StageError(transient=False)` | `False` | Never | (Reserved for future use) |
| **Unexpected** | Any other `Exception` | N/A | Yes, if attempts remain | Bugs, unhandled exceptions |

### 2. Complete Error Code Reference

| Error code | Raised by | Category | Description |
|------------|-----------|----------|-------------|
| `storage_download_failed` | Extract stage | Transient | Supabase Storage download failed |
| `integrity_sha_mismatch` | Extract stage | Terminal | SHA-256 of downloaded file does not match stored hash |
| `langgraph_flow_failed` | LangGraph stage | Transient | The analysis flow raised an exception |
| `result_persist_failed` | Persist stage | Transient | Could not write result_json to database |
| `unexpected_worker_error` | Pipeline runner | Unexpected | Catch-all for unhandled exceptions |
| `claim_failed` | Repository | N/A (not retried at stage level) | RPC call to claim_analysis_job failed |
| `stage_update_failed` | Repository | N/A (propagates as unexpected) | Could not update the stage column |
| `mark_succeeded_failed` | Repository | N/A (propagates as unexpected) | Could not mark job as succeeded |
| `mark_failed_failed` | Repository | N/A (logged at CRITICAL) | Could not mark job as failed |
| `db_unauthorized` | Repository | N/A (not retried at stage level) | Supabase returned 401/403 |

### 3. Retry Decision Logic

The pipeline runner (Step 05) applies this logic when an error occurs:

```
IF error is TerminalJobError:
    mark_failed(requeue=False)    # permanent failure, always

ELIF error is StageError:
    IF error.transient AND job.attempts < job.max_attempts:
        mark_failed(requeue=True)  # retry
    ELSE:
        mark_failed(requeue=False) # permanent failure

ELIF error is Exception (unexpected):
    IF job.attempts < job.max_attempts:
        mark_failed(requeue=True)  # retry (assume transient)
    ELSE:
        mark_failed(requeue=False) # permanent failure
```

### 4. Attempt Tracking

- `attempts` is incremented atomically at **claim time** by the RPC (Step 02)
- This means the current processing run is attempt number `job.attempts`
- A crash that prevents any error reporting still counts as an attempt (because the increment already happened)
- `max_attempts` defaults to 3 (DB column default). A job gets at most 3 full processing attempts.
- After `attempts = max_attempts`, the job is never returned by the claim RPC (the guard `attempts < max_attempts` excludes it)

**Attempt lifecycle example (max_attempts = 3):**

| Event | attempts | status | stage | Outcome |
|-------|----------|--------|-------|---------|
| Job created by backend | 0 | queued | created | Waiting |
| Worker A claims | 1 | running | created | Processing |
| Worker A fails (transient) | 1 | queued | created | Requeued |
| Worker B claims | 2 | running | created | Processing |
| Worker B crashes | 2 | running | created | Lease expires |
| Worker C claims (after lease expiry) | 3 | running | created | Processing (last attempt) |
| Worker C fails (transient) | 3 | failed | created | Permanent failure (3 >= 3) |

### 5. Crash Recovery via Lease Expiry

**Scenario:** A worker claims a job and crashes (process killed, OOM, hardware failure, network partition) before calling `mark_succeeded` or `mark_failed`.

**What happens:**
1. The job stays at `status = 'running'` with the crashed worker's `job_token` and `token_expires_at`
2. After `token_expires_at` passes (default: 5 minutes), the lease is expired
3. On the next poll cycle, any worker calling `claim_analysis_job` will match this job because `token_expires_at < now()` is true
4. The new worker claims the job: sets a new token, increments `attempts`, resets `stage = 'created'`
5. Processing restarts from scratch

**Key properties:**
- No external coordination needed (no distributed lock service, no health checks)
- The lease TTL (`job_lease_seconds`, default 300s) must be longer than the expected processing time to avoid premature reclaiming
- If the original worker "revives" after its lease expired and tries to continue, the token guard on `update_stage` and `mark_succeeded` will reject its writes (zero rows updated), and the pipeline runner will log the failure

### 6. Requeue Behavior (v1)

When a job is requeued (`mark_failed(requeue=True)`):
- `status` is set back to `"queued"`
- `stage` is reset to `"created"` (restart from scratch)
- `error_code` and `error_detail` are written (reflecting the most recent failure)
- `job_token` and `token_expires_at` are cleared
- `attempts` remains at its current value (already incremented at claim time)

The job is immediately eligible for claiming on the next poll cycle. There is no explicit backoff timer. The natural poll interval (5 seconds) provides a minimum delay between attempts.

### 7. Permanent Failure

When a job fails permanently (`mark_failed(requeue=False)`):
- `status` is set to `"failed"`
- `stage` is preserved at its current value (for debugging)
- `error_code` and `error_detail` are populated
- `job_token` and `token_expires_at` are cleared
- The job is a sink state: no automatic recovery. Manual intervention is required to reprocess.

### 8. Double-Failure Scenario

If `mark_failed` itself raises `JobRepoError` (e.g., DB is down, token already expired):
- The pipeline runner logs at CRITICAL level
- The job remains at `status = 'running'` with the worker's token
- When the lease expires, another worker will reclaim the job
- This counts as another attempt (the failed attempt's increment already happened)

This is the worst case for the retry system. The job may "waste" an attempt (the processing failed, the failure report failed, but the attempt was already counted). With `max_attempts = 3`, this means one effective processing run is lost. Acceptable for v1.

## Acceptance Criteria

- Terminal errors (`TerminalJobError`) always result in permanent failure, regardless of remaining attempts
- Transient errors (`StageError(transient=True)`) result in requeue when `attempts < max_attempts`
- Transient errors result in permanent failure when `attempts >= max_attempts`
- Unexpected exceptions are treated as transient with requeue based on remaining attempts
- Crashed workers' jobs are reclaimed after lease expiry
- Requeued jobs restart from `stage = created`
- Failed jobs preserve their last stage for debugging
- `attempts` is incremented at claim time, not at failure time
- `error_code` and `error_detail` are always populated on failure (both requeue and permanent)
- A job with `attempts = max_attempts` is never returned by the claim RPC

## End-to-End Verification Scenarios

### Scenario A: Happy Path
1. Insert a job with `status=queued`, `stage=created`
2. Start the worker
3. Worker claims job, processes all stages (stubs), marks succeeded
4. Verify: `status=succeeded`, `stage=done`, `result_json` is populated, `job_token` is null

### Scenario B: Transient Error with Retry
1. Insert a job with `status=queued`, `max_attempts=3`
2. Configure the extract stage to fail with `StageError(transient=True)` on first attempt
3. Worker claims (attempt 1), fails, requeues
4. Worker claims (attempt 2), succeeds
5. Verify: `status=succeeded`, `attempts=2`

### Scenario C: Max Attempts Exhausted
1. Insert a job with `status=queued`, `max_attempts=2`
2. Configure all stages to fail with `StageError(transient=True)`
3. Worker claims (attempt 1), fails, requeues
4. Worker claims (attempt 2), fails, permanent failure
5. Verify: `status=failed`, `attempts=2`, `error_code` populated

### Scenario D: Terminal Error
1. Insert a job with `status=queued`, `max_attempts=3`
2. Configure extract stage to raise `TerminalJobError(code="integrity_sha_mismatch")`
3. Worker claims (attempt 1), fails permanently on first attempt
4. Verify: `status=failed`, `attempts=1`, `error_code=integrity_sha_mismatch`

### Scenario E: Crash Recovery
1. Insert a job with `status=queued`, `max_attempts=3`
2. Worker A claims the job (attempt 1)
3. Kill Worker A before it completes
4. Wait for lease to expire (5 minutes, or use a short lease for testing)
5. Worker B claims the job (attempt 2)
6. Worker B succeeds
7. Verify: `status=succeeded`, `attempts=2`

### Scenario F: Concurrent Workers
1. Insert 1 job with `status=queued`
2. Start 3 workers simultaneously
3. Exactly 1 worker claims the job; the other 2 get no job
4. Verify: job processed exactly once

## Integration Points

- **Step 02:** The claim RPC enforces `attempts < max_attempts` and handles lease expiry
- **Step 04:** `mark_failed(requeue=True/False)` implements the requeue/fail writes
- **Step 05:** The pipeline runner implements the error classification logic
- **Steps 06–08:** Stages raise the specific error types listed in the classification table

## Dependencies

- **Depends on:** All previous steps (this step describes emergent behavior)
- **Informs:** Future monitoring/alerting spec, future resume-from-stage migration
