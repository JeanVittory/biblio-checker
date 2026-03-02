# Step 05 — Pipeline Framework

## Scope

- Define the `JobContext` dataclass that carries data through the pipeline
- Define the stage function contract (signature, error protocol)
- Define the pipeline runner that orchestrates stages and handles errors
- Define the package structure for `pipeline/`

**Out of scope:** Individual stage implementations (see Steps 06–08). Polling loop integration (see Step 09).

## Context

The worker processes a job by running it through a sequence of stages: extract, langgraph, persist. Each stage reads from and writes to a shared context object. The pipeline runner orchestrates the stage sequence and handles all error outcomes by delegating to the repository layer.

The runner is the central error boundary: stages raise `StageError` or `TerminalJobError`, and the runner translates these into the correct repository calls (`mark_failed` with `requeue=True` or `requeue=False`).

## Requirements

### 1. JobContext — `pipeline/context.py`

**File:** `apps/worker/biblio_checker_worker/pipeline/context.py`

A mutable dataclass that carries accumulated data through the stage pipeline:

| Field | Type | Default | Written by |
|-------|------|---------|------------|
| `job` | `AnalysisJob` | (required) | Set at construction by the runner |
| `file_bytes` | `bytes` | `b""` | Extract stage |
| `extracted_text` | `str` | `""` | Extract stage (future — currently unused) |
| `result_json` | `dict` | `{}` | LangGraph stage |

The context is NOT frozen — stages mutate it in place. Only the `job` field is set at construction; all others start at their defaults and are populated as stages complete.

### 2. Stage Function Contract

Every stage function MUST have this signature:

```
def stage_name(*, supabase: Client, ctx: JobContext) -> None
```

**Rules:**
- Receives `supabase` (for DB operations) and `ctx` (shared context) as keyword-only arguments
- Returns `None` on success
- Raises `StageError` for recoverable or non-recoverable processing errors
- Raises `TerminalJobError` for errors that must never be retried
- MUST NOT catch `StageError` or `TerminalJobError` internally — these bubble up to the runner
- MAY catch other exceptions and wrap them in `StageError` or `TerminalJobError`
- MUST call `repo.update_stage()` to advance the stage in the DB before doing the actual work of that stage (this ensures the DB reflects where the job is if the worker crashes)

### 3. Pipeline Runner — `pipeline/runner.py`

**File:** `apps/worker/biblio_checker_worker/pipeline/runner.py`

**Single public function:**

`process_job(supabase: Client, job: AnalysisJob) -> None`

**Behavior:**

1. Create a `JobContext` with the provided `job`
2. Define the ordered stage list: `[extract_stage, run_langgraph_stage, persist_stage]`
3. Iterate through stages, calling each one sequentially
4. Handle outcomes:

**On success (all stages complete without exception):**
- Nothing to do — the persist stage already called `mark_succeeded` (see Step 08)

**On `TerminalJobError`:**
- Call `repo.mark_failed(supabase, job_id=job.id, error_code=exc.code, error_detail=exc.detail, requeue=False, token=job.job_token)`
- Log the error at ERROR level

**On `StageError`:**
- Determine requeue eligibility: `requeue = exc.transient and job.attempts < job.max_attempts`
- Call `repo.mark_failed(supabase, job_id=job.id, error_code=exc.code, error_detail=exc.detail, requeue=requeue, token=job.job_token)`
- Log at WARNING level if requeued, ERROR level if permanent failure

**On unexpected `Exception`:**
- Treat as transient: `requeue = job.attempts < job.max_attempts`
- Call `repo.mark_failed(supabase, job_id=job.id, error_code="unexpected_worker_error", error_detail=str(exc) or None, requeue=requeue, token=job.job_token)`
- Log at ERROR level with full traceback

**On `JobRepoError` during mark_failed itself:**
- Log at CRITICAL level. The job is now in an inconsistent state (still `running` with an active lease). The lease will eventually expire, and another worker will reclaim it. No further action needed.

### 4. Logging

The runner MUST log:
- INFO: `"Processing job id=%s attempt=%d/%d"` at start
- INFO: `"Job id=%s succeeded"` on success
- WARNING: `"Job id=%s requeued (code=%s, attempt=%d/%d)"` on transient retry
- ERROR: `"Job id=%s failed permanently (code=%s)"` on terminal failure
- CRITICAL: `"Job id=%s mark_failed raised (code=%s) — lease will expire"` if the mark_failed call itself fails

Logger name: `"biblio_checker_worker.pipeline"`

### 5. Package Structure

```
apps/worker/biblio_checker_worker/pipeline/
  __init__.py            # empty
  context.py             # JobContext
  runner.py              # process_job
  stages/
    __init__.py          # empty
    extract.py           # see Step 06
    run_langgraph.py     # see Step 07
    persist.py           # see Step 08
```

## Acceptance Criteria

- `JobContext` is a mutable dataclass with `job`, `file_bytes`, `extracted_text`, `result_json`
- `process_job` calls stages in order: extract -> langgraph -> persist
- `TerminalJobError` results in `mark_failed(requeue=False)` regardless of remaining attempts
- `StageError(transient=True)` with remaining attempts results in `mark_failed(requeue=True)`
- `StageError(transient=True)` with no remaining attempts results in `mark_failed(requeue=False)`
- `StageError(transient=False)` results in `mark_failed(requeue=False)` regardless of remaining attempts
- Unexpected `Exception` is treated as transient with requeue based on remaining attempts
- If `mark_failed` itself raises `JobRepoError`, the error is logged but not re-raised (the polling loop continues)
- The `job.job_token` is passed as the `token` parameter to all repo calls (for the token guard)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| First stage raises `TerminalJobError` | Remaining stages are skipped. `mark_failed(requeue=False)` is called. |
| Second stage raises `StageError(transient=True)` | Third stage is skipped. `mark_failed(requeue=True)` if attempts remain. |
| All stages succeed but `mark_succeeded` inside persist stage raises `JobRepoError` | The `JobRepoError` propagates up to the runner as an unexpected `Exception`. Runner calls `mark_failed`. If that also fails, logged at CRITICAL and lease expires naturally. |
| `job.attempts = job.max_attempts` and a `StageError(transient=True)` is raised | `requeue = True and (3 < 3)` = `False`. The job is permanently failed. |
| Stage raises `KeyboardInterrupt` or `SystemExit` | These are NOT caught by `except Exception`. They propagate up, killing the worker. The lease expires and another worker reclaims. This is correct behavior. |

## Integration Points

- **Step 03:** Uses `AnalysisJob`, `StageError`, `TerminalJobError`, `JobRepoError`
- **Step 04:** Calls `repo.mark_failed` for error outcomes
- **Steps 06–08:** Defines the contract that stages must follow
- **Step 09:** The polling loop calls `process_job` after claiming

## Dependencies

- **Depends on:** Step 03 (domain types), Step 04 (repo functions)
- **Informs:** Steps 06–08 (stages implement this contract), Step 09 (polling calls process_job)
