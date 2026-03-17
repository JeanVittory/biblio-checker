# Step 07 — Worker Logging Migration

## Scope

**In scope:**

- Wire `setup_logging()` into the worker entry point
- Remove the old `_configure_logging()` function
- Migrate all existing stdlib `logging` calls (5 files, ~15 calls) to structlog
- Bind `job_id` to contextvars in the pipeline runner

**Out of scope:**

- Adding logging to files that currently have none (Step 08)
- Backend changes (Steps 05-06)

## Context

The worker has the most mature logging of the three apps — 5 files with ~15 logging calls using stdlib `logging`. The migration replaces:
1. `logging.getLogger("name")` → `structlog.stdlib.get_logger("name")`
2. Format-string log calls → event name + keyword args
3. `logging.basicConfig()` → `setup_logging()` from Step 04
4. Manual context (passing `job_id` in every call) → `structlog.contextvars.bind_contextvars(job_id=...)`

### Key Benefit of contextvars

Currently, `pipeline/runner.py` passes `job_id` in every log call manually. With structlog's contextvars, `job_id` is bound once at the start of `process_job()` and automatically appears in every log line made during that job's processing — including logs in stage functions, audit repo, and LangGraph flow.

## Requirements

### R1 — Wire `setup_logging()` in `main.py`

**File:** `apps/worker/biblio_checker_worker/main.py`

**Remove** the existing `_configure_logging()` function:
```python
# DELETE this entire function:
def _configure_logging() -> None:
    level_name = (settings.log_level or "INFO").upper().strip()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
```

**Replace** with:
```python
import structlog
from biblio_checker_worker.core.logging import setup_logging

logger = structlog.stdlib.get_logger("biblio_checker_worker")
```

**Update `main()`:**
```python
def main() -> None:
    setup_logging()
    logger.info(
        "worker_starting",
        environment=settings.environment,
        table=settings.supabase_table,
        poll_interval=settings.poll_interval_seconds,
    )
    # ... existing polling loop ...
```

**Update the KeyboardInterrupt handler:**
```python
except KeyboardInterrupt:
    logger.info("worker_stopped")
```

**Remove** `import logging` if no longer used.

### R2 — Migrate `polling/runner.py`

**File:** `apps/worker/biblio_checker_worker/polling/runner.py`

**Current (5 calls):**
```python
import logging
logger = logging.getLogger("biblio_checker_worker.polling")
```

**Replace with:**
```python
import structlog
logger = structlog.stdlib.get_logger("biblio_checker_worker.polling")
```

**Important:** `run_forever()` at line 40 has a local re-assignment `logger = logging.getLogger("biblio_checker_worker.polling")` that shadows the module-level logger. This local re-assignment must be **removed entirely** — the module-level structlog logger should be used instead.

**Migrate each call:**

| Current | New |
|---|---|
| `logger.error("Failed to claim ... code=%s detail=%s", exc.code, exc.detail)` | `logger.error("claim_failed", code=exc.code, detail=exc.detail)` |
| `logger.debug("No jobs available ...")` | `logger.debug("no_jobs_available")` |
| `logger.info("Claimed job %s (attempt %d/%d)", job.id, job.attempts, job.max_attempts)` | `logger.info("job_claimed", job_id=str(job.id), attempt=job.attempts, max_attempts=job.max_attempts)` |
| `logger.info("Polling loop started")` | `logger.info("polling_loop_started")` |

(Verify exact call signatures against current source — line numbers may have shifted.)

### R3 — Migrate `pipeline/runner.py`

**File:** `apps/worker/biblio_checker_worker/pipeline/runner.py`

**Current (7 calls):**
```python
import logging
logger = logging.getLogger("biblio_checker_worker.pipeline")
```

**Replace with:**
```python
import structlog
logger = structlog.stdlib.get_logger("biblio_checker_worker.pipeline")
```

**Add contextvars binding at the top of `process_job()`:**

The actual function signature is synchronous and takes `supabase` as first argument:
```python
def process_job(supabase: Client, job: AnalysisJob) -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(job_id=str(job.id))
    # ... rest of function
```

Note: `structlog.contextvars` works identically in sync and async code (contextvars are thread-local in synchronous code).

This means `job_id` no longer needs to be passed explicitly in each log call within `process_job` and all functions it calls (including `_safe_mark_failed`).

**Migrate each call:**

| Current | New |
|---|---|
| `logger.info("Processing job %s (attempt %d/%d) ...", job.id, ...)` | `logger.info("job_processing", attempt=job.attempts, max_attempts=job.max_attempts)` |
| `logger.error("Unexpected error ...", exc_info=True)` | `logger.exception("job_unexpected_error")` |
| `logger.info("Job id=%s succeeded", job.id)` | `logger.info("job_succeeded")` |

**Inside `_safe_mark_failed()` (lines 99-144)** — these calls are in a separate helper function, not in `process_job()`. Since `job_id` is bound to contextvars at the start of `process_job()`, it propagates automatically:

| Current | New |
|---|---|
| `logger.warning("Job id=%s requeued ...", job.id, ...)` | `logger.warning("job_requeued", error_code=error_code, attempt=job.attempts, max_attempts=job.max_attempts)` |
| `logger.error("Job id=%s failed permanently ...", job.id, ...)` | `logger.error("job_failed_permanently", error_code=error_code)` |
| `logger.critical("Job id=%s mark_failed raised ...", job.id, ...)` | `logger.critical("mark_failed_error", error_code=exc.code)` |

**Note:** `logger.exception("job_unexpected_error")` replaces `logger.error("...", exc_info=True)` — structlog's `exception()` method includes the traceback automatically.

### R4 — Migrate `langgraph/flow.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/flow.py`

**Current (1 call):**
```python
import logging
logger = logging.getLogger("biblio_checker_worker.langgraph")
```

**Replace with:**
```python
import structlog
logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph")
```

**Migrate:**

| Current | New |
|---|---|
| `logger.info("Invoking LangGraph flow for job %s (%d bytes)", job.id, len(file_bytes))` | `logger.info("langgraph_flow_invoked", file_bytes=len(file_bytes))` |

`job_id` is inherited from contextvars (bound in `process_job`).

### R5 — Migrate `jobs/audit_repo.py`

**File:** `apps/worker/biblio_checker_worker/jobs/audit_repo.py`

**Current (2 calls):**
```python
import logging
logger = logging.getLogger(__name__)
```

**Replace with:**
```python
import structlog
logger = structlog.stdlib.get_logger(__name__)
```

**Migrate:**

| Current | New |
|---|---|
| `logger.warning("Failed to insert job event ... %s", exc)` | `logger.warning("job_event_insert_failed", event_type=event_type, job_id=job_id, error=str(exc))` |
| `logger.warning("Failed to insert reference audit batch ... %s", exc)` | `logger.warning("reference_audit_batch_insert_failed", job_id=job_id, count=len(entries), error=str(exc))` |

## Event Naming Convention

All events follow `snake_case` naming. The worker uses short, descriptive event names:
- Operations: `worker_starting`, `polling_loop_started`, `job_claimed`, `job_processing`
- Outcomes: `job_succeeded`, `job_failed_permanently`, `job_requeued`
- Errors: `claim_failed`, `job_unexpected_error`, `mark_failed_error`

## Acceptance Criteria

- [ ] `_configure_logging()` function is removed from `main.py`
- [ ] `setup_logging()` from `core/logging.py` is called at worker startup
- [ ] All 5 files use `structlog.stdlib.get_logger()` instead of `logging.getLogger()`
- [ ] All ~15 logging calls use event name + keyword args (no format strings)
- [ ] `job_id` is bound to contextvars at the start of `process_job()` and cleared at the start of each new job
- [ ] `import logging` is removed from all 5 files (unless used for `logging.WARNING` constant, which is unlikely)
- [ ] `pnpm lint:worker` passes
- [ ] `pnpm test:worker` passes
- [ ] Existing error handling behavior is unchanged — only the logging mechanism changes

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `process_job` called without `clear_contextvars` | Previous job's `job_id` leaks into new job's logs — this is why `clear_contextvars()` is required at the top |
| `logger.exception()` called outside an exception handler | Logs the event without a traceback (structlog handles gracefully) |
| Test mocks `logging.getLogger` | Tests must be updated to mock `structlog.stdlib.get_logger` instead |
| `exc_info=True` passed to structlog | Works identically to stdlib — structlog's BoundLogger supports it |

## Dependencies

- **Step 04** must be implemented first (`setup_logging()` and `core/logging.py` must exist)
- **No dependency on** frontend or backend steps
