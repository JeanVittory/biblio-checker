# Step 08 — Worker Logging Coverage

## Scope

**In scope:**

- Add structlog logging to all worker files that currently have no logging
- Cover job repository, pipeline stages, and Supabase client
- Leverage contextvars `job_id` binding from Step 07

**Out of scope:**

- Modifying pipeline logic or error handling
- Backend logging (Steps 05-06)
- Adding new pipeline stages

## Context

After Step 07, the worker's existing logging is migrated to structlog with `job_id` bound via contextvars. But several files still have no logging:

- `jobs/repo.py` — job claiming, stage updates, mark succeeded/failed (critical operations with no trace)
- `pipeline/stages/extract.py` — file download, SHA verification
- `pipeline/stages/run_langgraph.py` — LangGraph invocation
- `pipeline/stages/persist.py` — result persistence
- `supabase/client.py` — Supabase client initialization

All stage functions are called within the `process_job()` context, so `job_id` is already bound in contextvars and will appear in all log output automatically.

## Requirements

### R1 — `jobs/repo.py`

**File:** `apps/worker/biblio_checker_worker/jobs/repo.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| After successful RPC claim | `job_claimed_rpc` | `info` | `job_id` |
| After stage update | `job_stage_updated` | `info` | `job_id`, `stage` |
| After mark_succeeded | `job_mark_succeeded` | `info` | `job_id` | **(forward-looking — currently not called from pipeline; add logging now so it's ready when the success path is wired)** |
| After mark_failed | `job_mark_failed` | `info` | `job_id`, `requeue` (bool) |
| Claim RPC error | `job_claim_rpc_failed` | `error` | `code`, `detail` |
| Stage update error | `job_stage_update_failed` | `error` | `job_id`, `stage`, `code`, `detail` |
| Mark succeeded error | `job_mark_succeeded_failed` | `error` | `job_id`, `code`, `detail` | **(forward-looking)** |
| Mark failed error | `job_mark_failed_failed` | `error` | `job_id`, `code`, `detail` |

**Note:** `job_id` from contextvars will be present automatically, but including it explicitly in repo methods is acceptable since these methods may be called outside a contextvars-bound context in tests.

### R2 — `pipeline/stages/extract.py`

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/extract.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Before file download | `extract_downloading` | `info` | `bucket`, `path` |
| After download complete | `extract_download_complete` | `info` | `size_bytes=len(file_bytes)` |
| After SHA verified | `extract_sha_verified` | `info` | — |
| After text extraction complete | `extract_text_complete` | `info` | `chars=len(text)` |
| Stage done | `extract_stage_done` | `info` | — |

`job_id` is inherited from contextvars — do not pass explicitly.

### R3 — `pipeline/stages/run_langgraph.py`

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Stage start | `langgraph_stage_starting` | `info` | — |
| Stage complete | `langgraph_stage_complete` | `info` | — |

`job_id` is inherited from contextvars.

### R4 — `pipeline/stages/persist.py`

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/persist.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Stage start | `persist_stage_starting` | `info` | — |
| Stage complete | `persist_stage_complete` | `info` | — |

`job_id` is inherited from contextvars.

### R5 — `supabase/client.py`

**File:** `apps/worker/biblio_checker_worker/supabase/client.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging:

| Location | Event | Level | Fields |
|---|---|---|---|
| Client misconfigured | `supabase_client_misconfigured` | `error` | — |

## contextvars Inheritance Map

This diagram shows how `job_id` flows through the worker without explicit passing:

```
process_job(job)
  ├── bind_contextvars(job_id=job.id)  ← bound once here
  │
  ├── extract_stage()
  │    ├── logger.info("extract_downloading")     ← job_id included automatically
  │    ├── repo.download_file()                    ← job_id included automatically
  │    └── logger.info("extract_stage_done")       ← job_id included automatically
  │
  ├── run_langgraph_stage()
  │    ├── logger.info("langgraph_stage_starting") ← job_id included automatically
  │    └── flow.invoke()                           ← job_id included automatically
  │
  ├── persist_stage()
  │    ├── logger.info("persist_stage_starting")   ← job_id included automatically
  │    └── audit_repo.insert_*()                   ← job_id included automatically
  │
  └── logger.info("job_succeeded")                 ← job_id included automatically
```

## Acceptance Criteria

- [ ] All 5 files listed above have `structlog.stdlib.get_logger(__name__)` at module level
- [ ] `jobs/repo.py` logs every DB operation (success and failure)
- [ ] All 3 pipeline stage files log stage start and completion
- [ ] `supabase/client.py` logs misconfiguration errors
- [ ] No log call explicitly passes `job_id` when it's already bound in contextvars (except in `jobs/repo.py` where explicit is acceptable)
- [ ] No log call includes sensitive data (storage keys, file contents)
- [ ] No error handling behavior is changed — only logging is added
- [ ] `pnpm lint:worker` passes
- [ ] `pnpm test:worker` passes

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `extract_stage` fails mid-download | Exception propagates to `process_job` error handler (Step 07), which logs `job_unexpected_error` with traceback |
| `persist_stage` audit writes fail | Audit repo swallows errors internally (fire-and-forget) and logs `job_event_insert_failed` |
| Stage function called outside `process_job` (in tests) | `job_id` will not be in contextvars — logs work but without correlation |
| Very large file downloaded | `size_bytes` field in `extract_download_complete` shows the actual size — useful for debugging memory issues |

## Dependencies

- **Step 07** must be implemented first (existing logging migrated, contextvars binding in `process_job`)
- **No dependency on** frontend or backend steps
