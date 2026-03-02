# Step 04 — Job Repository

## Scope

- Define the repository module that performs all database operations for the worker
- Four public functions: `claim_one_job`, `update_stage`, `mark_succeeded`, `mark_failed`
- Error handling pattern matching the backend convention

**Out of scope:** The Postgres RPC itself (see Step 02). Pipeline stages that call these functions (see Steps 06–08).

## Context

The worker needs a repository layer that encapsulates all Supabase table operations. The backend already has this pattern in `apps/backend/app/services/analysis_jobs_repo.py`: synchronous Supabase calls wrapped in error handling that catches `APIError` and bare `Exception`, re-raising as typed `JobRepoError`.

Key difference: the backend uses `anyio.to_thread.run_sync()` because FastAPI is async. The worker is fully synchronous (simple polling loop), so all functions are plain synchronous functions — no async, no thread wrapping.

### Supabase client call pattern (from backend)

```
resp = supabase.table("analysis_jobs").update({...}).eq("id", job_id).execute()
data = getattr(resp, "data", None)
if not isinstance(data, list) or not data:
    raise JobRepoError(code="...", detail="...")
```

The worker's repo MUST follow this exact pattern for consistency.

## Requirements

### 1. Module Location

**File:** `apps/worker/biblio_checker_worker/jobs/repo.py`

All functions receive a `supabase: Client` parameter (injected by the caller, not created internally). This enables testing with mock clients.

### 2. `claim_one_job`

**Signature:** `claim_one_job(supabase: Client, *, token: str, lease_seconds: int) -> AnalysisJob | None`

**Behavior:**
1. Call the RPC: `supabase.rpc("claim_analysis_job", {"p_token": token, "p_lease_secs": lease_seconds}).execute()`
2. Extract `resp.data` (expected: list with 0 or 1 dicts)
3. If empty list: return `None` (no job available)
4. If one dict: return `AnalysisJob.from_row(resp.data[0])`

**Errors:**
- `APIError` with code 401/403 -> `JobRepoError(code="db_unauthorized")`
- `APIError` other -> `JobRepoError(code="claim_failed")`
- Any other `Exception` -> `JobRepoError(code="claim_failed")`

### 3. `update_stage`

**Signature:** `update_stage(supabase: Client, *, job_id: str, stage: JobStage, token: str) -> None`

**Behavior:**
1. Update the row: `supabase.table("analysis_jobs").update({"stage": stage.value, "updated_at": "now()"}).eq("id", job_id).eq("job_token", token).execute()`
2. Verify that `resp.data` contains exactly one updated row
3. If no rows updated (token mismatch or job not found): raise `JobRepoError(code="stage_update_failed", detail="No matching row — possible lease expiry or token mismatch")`

**Why token guard:** The `eq("job_token", token)` clause ensures that a worker can only update a job it currently holds. If the lease expired and another worker reclaimed the job (writing a new token), this update will match zero rows, preventing a stale worker from overwriting the new owner's progress.

**Errors:**
- Zero rows updated -> `JobRepoError(code="stage_update_failed")`
- `APIError` -> `JobRepoError(code="stage_update_failed")`
- Any other `Exception` -> `JobRepoError(code="stage_update_failed")`

### 4. `mark_succeeded`

**Signature:** `mark_succeeded(supabase: Client, *, job_id: str, result_json: dict, token: str) -> None`

**Behavior:**
1. Update the row with:
   - `status` = `"succeeded"`
   - `stage` = `"done"`
   - `result_json` = the provided dict
   - `job_token` = `None` (clear lease)
   - `token_expires_at` = `None` (clear expiry)
   - `updated_at` = `"now()"`
2. Guard with `eq("id", job_id)` and `eq("job_token", token)`
3. Verify exactly one row was updated

**Errors:**
- Zero rows updated -> `JobRepoError(code="mark_succeeded_failed")`
- `APIError` -> `JobRepoError(code="mark_succeeded_failed")`
- Any other `Exception` -> `JobRepoError(code="mark_succeeded_failed")`

### 5. `mark_failed`

**Signature:** `mark_failed(supabase: Client, *, job_id: str, error_code: str, error_detail: str | None, requeue: bool, token: str) -> None`

**Behavior depends on `requeue`:**

**When `requeue = True` (retryable failure):**
1. Update the row with:
   - `status` = `"queued"`
   - `stage` = `"created"` (reset to beginning — v1 restart-from-scratch)
   - `error_code` = the provided error code
   - `error_detail` = the provided detail
   - `job_token` = `None` (release lease so another worker can claim)
   - `token_expires_at` = `None`
   - `updated_at` = `"now()"`

**When `requeue = False` (permanent failure):**
1. Update the row with:
   - `status` = `"failed"`
   - (stage is NOT modified — preserved for debugging, per Step 01 transition T8)
   - `error_code` = the provided error code
   - `error_detail` = the provided detail
   - `job_token` = `None`
   - `token_expires_at` = `None`
   - `updated_at` = `"now()"`

Both paths guard with `eq("id", job_id)` and `eq("job_token", token)`.

**Errors:**
- Zero rows updated -> `JobRepoError(code="mark_failed_failed")`
- `APIError` -> `JobRepoError(code="mark_failed_failed")`
- Any other `Exception` -> `JobRepoError(code="mark_failed_failed")`

### 6. Error Handling Pattern

Every function MUST follow this structure:

```
try:
    # supabase call
except JobRepoError:
    raise  # don't double-wrap
except APIError as exc:
    code = str(exc.code or "").strip()
    if code in ("401", "403"):
        raise JobRepoError(code="db_unauthorized", detail=str(exc)) from exc
    raise JobRepoError(code="<operation>_failed", detail=str(exc) or None) from exc
except Exception as exc:
    raise JobRepoError(code="<operation>_failed", detail=str(exc) or None) from exc
```

This is identical to the backend pattern in `analysis_jobs_repo.py`.

### 7. `updated_at` Handling

All update operations set `updated_at` to the string `"now()"`. When passed through PostgREST, this is interpreted as the Postgres `now()` function, giving the server-side timestamp. This avoids clock skew between the worker and the database.

## Acceptance Criteria

- `claim_one_job` calls the correct RPC with token and lease_seconds parameters
- `claim_one_job` returns `None` when the RPC returns an empty list
- `claim_one_job` returns an `AnalysisJob` when the RPC returns one row
- `update_stage` includes the token guard (`eq("job_token", token)`)
- `update_stage` raises `JobRepoError` when zero rows are updated (stale lease)
- `mark_succeeded` sets status to `succeeded`, stage to `done`, writes `result_json`, and clears the token
- `mark_failed` with `requeue=True` sets status to `queued`, stage to `created`, and clears the token
- `mark_failed` with `requeue=False` sets status to `failed`, preserves the current stage, and clears the token
- All functions catch `APIError` and wrap in `JobRepoError`
- All functions catch bare `Exception` and wrap in `JobRepoError`
- No function creates its own Supabase client — all receive `supabase: Client` as a parameter

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `claim_one_job` RPC returns more than 1 row | Should not happen (RPC uses `LIMIT 1`), but if it does, use only the first row |
| `update_stage` called after lease expired (another worker reclaimed) | Token mismatch -> zero rows updated -> `JobRepoError(code="stage_update_failed")` |
| `mark_succeeded` called but job was already marked failed by another process | Token mismatch -> zero rows updated -> `JobRepoError(code="mark_succeeded_failed")` |
| `mark_failed` with `requeue=True` but job is already in `failed` status | Token was cleared when it was marked failed, so token mismatch -> zero rows -> error. The caller (pipeline runner) logs and moves on. |
| Supabase client raises a non-APIError exception (e.g., network timeout) | Caught by bare `except Exception`, wrapped in `JobRepoError` |

## Integration Points

- **Step 02:** `claim_one_job` calls the RPC defined in Step 02
- **Step 03:** Uses `AnalysisJob.from_row()`, `JobRepoError`, `JobStage` from the domain layer
- **Step 05:** The pipeline runner calls `mark_succeeded` and `mark_failed`
- **Steps 06–08:** Each stage calls `update_stage` to advance the stage
- **Step 09:** The polling loop calls `claim_one_job`

## Dependencies

- **Depends on:** Step 02 (RPC must exist), Step 03 (domain types must exist)
- **Informs:** Steps 05–09 (all use repo functions)
