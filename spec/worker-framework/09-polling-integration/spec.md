# Step 09 — Polling Integration

## Scope

- Modify the existing `poll_once()` function to claim a job and process it
- Wire together the repository layer, pipeline runner, and configuration
- Define the complete flow of a single poll cycle

**Out of scope:** The `run_forever()` loop structure (already implemented, no changes needed). Individual stage behavior (see Steps 06–08).

## Context

The polling loop at `apps/worker/biblio_checker_worker/polling/runner.py` already exists with the correct structure:

```python
def run_forever() -> None:
    supabase = get_supabase_admin_client()
    while True:
        poll_once(supabase=supabase)
        time.sleep(max(1, int(settings.poll_interval_seconds)))
```

The `poll_once()` function is currently a no-op stub (`time.sleep(0.0)`). This step replaces it with the actual claiming and processing logic.

## Requirements

### 1. Module to Modify

**File:** `apps/worker/biblio_checker_worker/polling/runner.py`

### 2. New `poll_once` Implementation

**Signature:** `poll_once(*, supabase: Client) -> None` (unchanged)

**Behavior — single poll cycle:**

**Step 2.1 — Generate lease token**

Generate a unique token: `token = secrets.token_urlsafe(settings.job_token_bytes)`

**Step 2.2 — Attempt to claim a job**

Call: `job = repo.claim_one_job(supabase, token=token, lease_seconds=settings.job_lease_seconds)`

**Step 2.3 — Handle claim result**

- If `job is None`: log at DEBUG level (`"No jobs available."`) and return
- If `job` is not None: log at INFO level (`"Claimed job id=%s attempt=%d/%d"`) and proceed to Step 2.4

**Step 2.4 — Process the job**

Call: `process_job(supabase=supabase, job=job)`

The pipeline runner handles all error outcomes internally (see Step 05). The `poll_once` function does NOT need to handle `StageError`, `TerminalJobError`, or `JobRepoError` — these are all handled inside `process_job`.

**Step 2.5 — Handle claim errors**

If `repo.claim_one_job` raises `JobRepoError`:
- Log at ERROR level: `"Failed to claim job (code=%s): %s"`
- Return (do not crash the polling loop)

### 3. Imports

The modified `poll_once` function requires these new imports:
- `secrets` (standard library)
- `repo` module (from `biblio_checker_worker.jobs`)
- `process_job` (from `biblio_checker_worker.pipeline.runner`)
- `JobRepoError` (from `biblio_checker_worker.jobs.errors`)

### 4. `run_forever` Changes

The `run_forever()` function requires NO changes. It already:
- Creates the Supabase client once
- Loops calling `poll_once(supabase=supabase)`
- Sleeps `poll_interval_seconds` between cycles

### 5. Single-Job-Per-Cycle Design

Each poll cycle claims and processes at most one job. This is intentional:
- Simple to reason about
- Natural backpressure: if processing takes 30 seconds, the effective throughput is 1 job per ~35 seconds (30s processing + 5s sleep)
- For higher throughput, deploy multiple worker instances (horizontal scaling) rather than adding in-process concurrency

### 6. Complete Poll Cycle Flow

```
poll_once() called
  |
  ├── Generate token
  ├── Call claim_one_job()
  |     |
  |     ├── No job? -> log DEBUG, return
  |     └── Job claimed? -> log INFO
  |           |
  |           └── Call process_job()
  |                 |
  |                 ├── extract_stage()
  |                 ├── run_langgraph_stage()
  |                 ├── persist_stage()
  |                 |
  |                 ├── Success: job is now succeeded/done
  |                 ├── StageError: mark_failed (requeue or permanent)
  |                 ├── TerminalJobError: mark_failed (permanent)
  |                 └── Exception: mark_failed (requeue if attempts remain)
  |
  └── return (sleep happens in run_forever)
```

## Acceptance Criteria

- `poll_once` generates a unique token using `secrets.token_urlsafe(settings.job_token_bytes)`
- `poll_once` calls `claim_one_job` with the token and `settings.job_lease_seconds`
- If no job is available, `poll_once` returns without error
- If a job is claimed, `poll_once` calls `process_job` with the supabase client and job
- If `claim_one_job` raises `JobRepoError`, the error is logged and `poll_once` returns (no crash)
- `run_forever` is NOT modified
- The `time.sleep(0.0)` stub in the current `poll_once` is completely removed
- The existing `SupabaseClientError` import remains (used by `run_forever`)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Supabase is temporarily unreachable | `claim_one_job` raises `JobRepoError`. Logged, returned. Next poll in 5 seconds tries again. |
| `process_job` raises an unhandled exception (bug) | This should not happen (process_job has a catch-all). But if it does, the exception propagates to `run_forever`, which does NOT catch it, crashing the worker. This is correct: an unhandled exception in the pipeline runner indicates a bug that must be fixed. |
| Worker starts with no jobs in the table | `poll_once` logs "No jobs available" at DEBUG level every 5 seconds. No errors, no resource waste. |
| Multiple workers running simultaneously | Each calls `claim_one_job` independently. The RPC's `FOR UPDATE SKIP LOCKED` ensures no double-claiming. |

## Integration Points

- **Step 04:** Calls `repo.claim_one_job`
- **Step 05:** Calls `pipeline.runner.process_job`
- **Step 03:** Uses `settings.job_lease_seconds` and `settings.job_token_bytes`

## Dependencies

- **Depends on:** Step 03 (settings), Step 04 (repo), Step 05 (pipeline runner), Steps 06–08 (stages must exist for pipeline to run)
- **Informs:** Step 10 (the poll cycle is the entry point for all retry behavior)
