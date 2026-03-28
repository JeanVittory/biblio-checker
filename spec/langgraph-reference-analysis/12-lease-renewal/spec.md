# Step 12 — Lease Renewal

## Scope

- Define and implement the `renew_analysis_job_lease` Postgres RPC
- Implement `repo.renew_lease()` in the worker repository layer
- Define a renewal utility for use within graph nodes
- Define when and how lease renewal is triggered during graph execution

**Out of scope:** Initial job claiming (see `spec/worker-framework/02-atomic-job-claiming/`). Lease expiry and crash recovery (see `spec/worker-framework/10-retry-and-recovery/`).

## Context

The worker claims a job with a lease (default 300 seconds / 5 minutes). If the graph takes longer than 5 minutes (likely for documents with many references — LLM calls + 3 API lookups per reference), the lease expires and another worker may reclaim the job.

To prevent this, the graph periodically renews the lease before expensive operations (LLM calls, API verification batches). This ensures the lease stays fresh as long as the worker is actively processing.

## Requirements

### 1. Postgres RPC — `renew_analysis_job_lease`

**Migration file:** `supabase/migrations/XXXXXXXX_create_renew_lease_rpc.sql`

```sql
CREATE OR REPLACE FUNCTION public.renew_analysis_job_lease(
    p_job_id   uuid,
    p_token    text,
    p_lease_secs int DEFAULT 300
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    rows_updated int;
BEGIN
    UPDATE analysis_jobs
    SET
        job_token_expires_at = now() + (p_lease_secs || ' seconds')::interval,
        updated_at = now()
    WHERE id = p_job_id
      AND job_token = p_token
      AND status = 'running';

    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated > 0;
END;
$$;

-- Permission model: same as claim_analysis_job
REVOKE EXECUTE ON FUNCTION public.renew_analysis_job_lease(uuid, text, int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.renew_analysis_job_lease(uuid, text, int) TO service_role;
```

**Behavior:**
- Extends `job_token_expires_at` by `p_lease_secs` from `now()`
- Requires the current `job_token` to match (token guard)
- Only operates on `status='running'` jobs (a succeeded/failed job cannot be renewed)
- Returns `true` if the update was applied, `false` if no matching row was found

### 2. Repository Function — `repo.renew_lease()`

**File:** `apps/worker/biblio_checker_worker/jobs/repo.py`

Add to the existing repo module:

```python
def renew_lease(
    supabase: Client,
    *,
    job_id: str,
    token: str,
    lease_seconds: int,
) -> bool:
    """Renew the worker lease for a running job.

    Returns True if the lease was renewed, False if the job was not found
    or the token didn't match (e.g., the job was reclaimed by another worker).
    """
```

**Note:** `job_id` is typed as `str` (not `uuid.UUID`) to match the existing worker repo conventions. The Supabase RPC accepts the UUID as a string without conversion.

**Implementation:**
1. Call `supabase.rpc("renew_analysis_job_lease", {"p_job_id": job_id, "p_token": token, "p_lease_secs": lease_seconds})`
2. Parse the response: the RPC returns a boolean
3. Log the result
4. Return the boolean

**Error handling:**
- If the RPC call fails (network, Supabase error), log at WARNING level and return `False`
- Do NOT raise — lease renewal failure should not crash the pipeline

### 3. Renewal Utility — `langgraph/lease.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/lease.py`

This module provides a convenient function for nodes to call:

```python
import contextvars

# ContextVar-based state (safe across async tasks and thread pool executors)
_lease_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "lease_ctx", default=None
)


def init_lease_context(*, supabase: Client, job_id: str, token: str, lease_seconds: int) -> None:
    """Initialize lease renewal context. Called once before graph invocation."""
    _lease_ctx.set({
        "supabase": supabase,
        "job_id": job_id,
        "token": token,
        "lease_seconds": lease_seconds,
    })


def renew_lease_if_needed() -> bool:
    """Renew the lease if context is initialized. Returns True if renewed.

    Safe to call even if context is not initialized (returns False).
    """
    ctx = _lease_ctx.get(None)
    if ctx is None:
        return False
    return repo.renew_lease(
        ctx["supabase"],
        job_id=ctx["job_id"],
        token=ctx["token"],
        lease_seconds=ctx["lease_seconds"],
    )


def clear_lease_context() -> None:
    """Clear the lease context after graph execution."""
    _lease_ctx.set(None)
```

**Design rationale:** Using `contextvars.ContextVar` rather than a plain module-level variable avoids threading the Supabase client and lease info through the `GraphState` (which would add non-serializable objects to the state), while also being safe across async tasks and thread pool executors used by LangGraph's `Send()` fan-out. The context is initialized once by `flow.py` before invocation and cleared after.

### 4. Renewal Points in the Graph

Nodes that MUST call `renew_lease_if_needed()` before their expensive operations:

| Node | When | Why |
|------|------|-----|
| `parse_references` | Before LLM call | LLM calls can take 10-30 seconds |
| `normalize_references` | Before LLM call | LLM calls can take 10-30 seconds |
| `verify_single_reference` | Before API calls | 3 API calls with 30s timeout each = up to 90s |
| `assemble_report` | Before Pydantic validation | Validation of large payloads may take time |

### 5. Logging

Logger name: `"biblio_checker_worker.langgraph.lease"`

- DEBUG: `"lease_renewed"` with `job_id` (on success)
- WARNING: `"lease_renewal_failed"` with `job_id`, `error` (on failure)
- DEBUG: `"lease_context_not_initialized"` if called without init

## Acceptance Criteria

- [ ] The `renew_analysis_job_lease` RPC is created in a Supabase migration
- [ ] The RPC requires `job_token` match (token guard)
- [ ] The RPC only operates on `status='running'` jobs
- [ ] The RPC returns `boolean` (true if updated, false otherwise)
- [ ] The RPC is callable only by `service_role`
- [ ] `repo.renew_lease()` accepts `job_id: str` (not `uuid.UUID`)
- [ ] `repo.renew_lease()` calls the RPC with `"p_job_id": job_id` (no `str()` conversion needed)
- [ ] `repo.renew_lease()` returns a boolean
- [ ] `repo.renew_lease()` does NOT raise on failure — returns `False`
- [ ] `renew_lease_if_needed()` takes no parameters
- [ ] `renew_lease_if_needed()` is callable from any graph node
- [ ] `renew_lease_if_needed()` is safe to call when context is not initialized
- [ ] `init_lease_context()` accepts `job_id: str` (not `uuid.UUID`)
- [ ] `init_lease_context()`, `renew_lease_if_needed()`, and `clear_lease_context()` use `contextvars.ContextVar` (not module-level `global` variable)
- [ ] Unit tests cover: successful renewal, token mismatch, RPC failure, uninitialized context

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Job was already reclaimed by another worker (token mismatch) | RPC returns `false`. `renew_lease()` returns `False`. Node continues anyway — it will fail at the next `repo.update_stage()` call with a token guard error. |
| Job was already marked `succeeded` or `failed` | RPC returns `false` (WHERE clause excludes non-running jobs). No side effects. |
| Supabase is temporarily unreachable | `renew_lease()` logs WARNING, returns `False`. Node continues. If the lease actually expires, another worker may reclaim. |
| `renew_lease_if_needed()` called before `init_lease_context()` | Returns `False` immediately. No error. |
| Multiple graph nodes call `renew_lease_if_needed()` concurrently | Module-level state is shared. Each call extends the lease. No conflict. |

## Integration Points

- **Step 10:** `verify_single_reference` calls `renew_lease_if_needed()` before API calls
- **Step 14:** `flow.py` calls `init_lease_context()` before and `clear_lease_context()` after graph invocation
- **Worker framework:** `pipeline/stages/run_langgraph.py` provides the Supabase client and token

## Dependencies

- **Depends on:** existing config field `job_lease_seconds` (default: 300) in the existing `Settings` class; existing worker framework (repo layer, Supabase client)
- **Informs:** Step 10 (verify node uses renewal), Step 14 (flow.py initializes context)
