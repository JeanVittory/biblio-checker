# Step 05 — Backend Audit Repository

## Scope

**In scope:**

- Async repository module for writing audit events from the FastAPI backend
- `JobEventType` enum for the backend
- Error handling strategy (fire-and-forget)
- Unit tests

**Out of scope:**

- Integrating the repo into existing controllers (Step 07)
- Read/query methods for audit data (future admin endpoints)
- Reference audit writes (worker-only, Step 06)

## Context

The backend currently writes to `analysis_jobs` via `apps/backend/app/services/analysis_jobs_repo.py`. That module uses `anyio.to_thread.run_sync` to wrap synchronous Supabase client calls, raises `AnalysisJobsRepoError` on failures, and obtains the client via `get_supabase_admin_client()`.

The audit repo follows the same patterns but with one critical difference: it never raises exceptions to callers. All errors are caught internally and logged as warnings.

## Requirements

### R1 — JobEventType enum

**File:** `apps/backend/app/schemas/audit_events.py`

```python
from __future__ import annotations

import enum


class JobEventType(enum.StrEnum):
    JOB_CREATED = "job_created"
    JOB_CLAIMED = "job_claimed"
    STAGE_CHANGED = "stage_changed"
    JOB_SUCCEEDED = "job_succeeded"
    JOB_FAILED = "job_failed"
    JOB_REQUEUED = "job_requeued"
```

The values must exactly match the CHECK constraint on `job_events.event_type` (Step 02).

### R2 — Audit repository module

**File:** `apps/backend/app/services/audit_repo.py`

**Dependencies:**
- `anyio.to_thread.run_sync` (existing pattern)
- `app.core.supabase_client.get_supabase_admin_client` (existing)
- `logging` (stdlib)

### R3 — `insert_job_event` function

```python
async def insert_job_event(
    *,
    job_id: str,
    event_type: str,
    stage: str | None = None,
    status: str | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
    attempt: int | None = None,
    metadata: dict | None = None,
) -> None:
```

**Behavior:**

1. Obtain the Supabase admin client via `get_supabase_admin_client()`
2. Build a row dict from the parameters (use `{}` if `metadata` is None)
3. Truncate `error_detail` to 200 characters (same limit as `analysis_jobs`)
4. Call `supabase.table("job_events").insert(row).execute()` via `run_sync`
5. On ANY exception (including `SupabaseClientError`, `APIError`, or unexpected errors): log at WARNING level with the job_id and exception, then return normally
6. Never re-raise exceptions — this is the fire-and-forget contract

**Logging format:**

```
WARNING audit_repo: Failed to insert job event [event_type=%s, job_id=%s]: %s
```

### R4 — Unit tests

**File:** `apps/backend/tests/test_audit_repo.py`

| Test | Description |
|---|---|
| `test_insert_job_event_success` | Mock Supabase client; verify `.table("job_events").insert(row).execute()` is called with correct payload |
| `test_insert_job_event_truncates_error_detail` | Verify `error_detail` longer than 200 chars is truncated |
| `test_insert_job_event_swallows_api_error` | Mock Supabase to raise `APIError`; verify no exception propagates and WARNING is logged |
| `test_insert_job_event_swallows_client_error` | Mock `get_supabase_admin_client` to raise `SupabaseClientError`; verify no exception propagates |
| `test_insert_job_event_default_metadata` | Verify `metadata` defaults to `{}` when None |

## Acceptance Criteria

- [ ] `apps/backend/app/schemas/audit_events.py` exists with `JobEventType` enum matching the DB CHECK constraint
- [ ] `apps/backend/app/services/audit_repo.py` exists with `insert_job_event`
- [ ] `insert_job_event` never raises exceptions to callers
- [ ] `insert_job_event` logs WARNING on any failure
- [ ] `error_detail` is truncated to 200 characters before DB write
- [ ] `metadata` defaults to `{}` when not provided
- [ ] All tests in `apps/backend/tests/test_audit_repo.py` pass
- [ ] `pnpm lint:backend` passes with no new warnings

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `get_supabase_admin_client()` raises `SupabaseClientError` | Caught, logged as WARNING, function returns None |
| Supabase returns a non-list response | Ignored (fire-and-forget; we don't check the insert response) |
| `event_type` value not in CHECK constraint | Insert fails at DB level; caught and logged as WARNING |
| `error_detail` is exactly 200 chars | Not truncated |
| `error_detail` is 201 chars | Truncated to 200 |
| `metadata` contains non-serializable values | Supabase client raises; caught and logged as WARNING |

## Integration Points

- **Step 02 (Job Events Schema):** this repo writes to `public.job_events`
- **Step 07 (Integration Points):** describes where `insert_job_event` will be called from in the backend controllers
- **Existing module:** follows patterns from `apps/backend/app/services/analysis_jobs_repo.py`

## Dependencies

- **Step 02** must be implemented first (table must exist)
- **No dependency on** Steps 03, 04, or 06
