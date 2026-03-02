# Step 08 — Persist Stage

## Scope

- Define the persist stage: advance to `persisting_result`, then write the result and mark the job as succeeded
- Define error handling for DB write failures

**Out of scope:** ResultsV1 schema validation (deferred to when the real LangGraph flow produces actual results). Retry logic (see Step 10).

## Context

The persist stage is the final stage in the pipeline. It writes the analysis result to the database and transitions the job to its terminal success state. This is the only stage that changes the job's `status` column (from `running` to `succeeded`).

For v1 (stub LangGraph), `ctx.result_json` will be `{}` (empty dict). The persist stage writes whatever is in `ctx.result_json` without validation. ResultsV1 schema validation will be added when the real LangGraph flow is implemented.

## Requirements

### 1. Module Location

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/persist.py`

**Public function:** `persist_stage(*, supabase: Client, ctx: JobContext) -> None`

### 2. Processing Steps

**Step 2.1 — Advance to `persisting_result`**

Call `repo.update_stage(supabase, job_id=ctx.job.id, stage=JobStage.PERSISTING_RESULT, token=ctx.job.job_token)`

**Step 2.2 — Mark succeeded**

Call `repo.mark_succeeded(supabase, job_id=ctx.job.id, result_json=ctx.result_json, token=ctx.job.job_token)`

This single call:
- Sets `status = "succeeded"` and `stage = "done"`
- Writes `ctx.result_json` to the `result_json` column
- Clears `job_token` and `token_expires_at` (releases the lease)
- Sets `updated_at` to server time

### 3. Error Handling

**If `update_stage` fails (`JobRepoError`):**
- Let it propagate to the pipeline runner. The runner treats `JobRepoError` as an unexpected exception and calls `mark_failed` with requeue logic.

**If `mark_succeeded` fails (`JobRepoError`):**
- Let it propagate to the pipeline runner. This is a critical failure: the job was fully processed but the result could not be persisted. The runner will attempt `mark_failed`.

Both errors propagate as `JobRepoError`, which the pipeline runner (Step 05) handles as unexpected exceptions with requeue based on remaining attempts.

### 4. Idempotency

The persist stage is safe to retry:
- `update_stage` to `persisting_result` is idempotent (writing the same stage value twice is a no-op from a data perspective, though the `updated_at` timestamp changes)
- `mark_succeeded` writes the same `result_json` on every attempt (the result is deterministic for a given pipeline run)
- However, note that on requeue (v1), the entire pipeline restarts from scratch, so `ctx.result_json` may differ between attempts if the LangGraph flow is non-deterministic. This is acceptable: each attempt produces an independent result.

### 5. Error Classification

| Error condition | Error type | Code | Transient |
|----------------|------------|------|-----------|
| `update_stage` fails | `JobRepoError` | (from repo) | Treated as unexpected by runner |
| `mark_succeeded` fails | `JobRepoError` | (from repo) | Treated as unexpected by runner |

This stage does NOT raise `StageError` or `TerminalJobError` directly. All errors come from the repository layer.

## Acceptance Criteria

- The stage advances to `persisting_result` before writing the result
- The stage calls `mark_succeeded` with the job ID, result_json, and token
- After `mark_succeeded`, the job's status is `succeeded` and stage is `done`
- After `mark_succeeded`, `job_token` and `token_expires_at` are cleared
- `result_json` contains whatever dict was in `ctx.result_json` (no validation for v1)
- The token guard is passed to all repo calls
- Any `JobRepoError` from repo calls propagates to the pipeline runner unmodified

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `ctx.result_json` is `{}` (stub) | Written as-is. Valid JSONB in Postgres. |
| `mark_succeeded` fails due to network timeout | `JobRepoError` propagates to runner. Runner attempts `mark_failed(requeue=True)`. On next attempt, pipeline re-processes from scratch and tries again. |
| `mark_succeeded` fails because token expired (lease lost) | `JobRepoError` propagates to runner. Runner attempts `mark_failed`, which also fails (same token mismatch). Runner logs at CRITICAL. Lease expires and another worker reclaims. |
| Worker crashes between `update_stage(persisting_result)` and `mark_succeeded` | Job stays at `running/persisting_result`. Lease expires. Another worker reclaims and re-processes from scratch (v1). |

## Integration Points

- **Step 04:** Calls `repo.update_stage` and `repo.mark_succeeded`
- **Step 05:** Follows the stage function contract. This is the final stage in the pipeline.
- **Step 07:** Reads `ctx.result_json` populated by the LangGraph stage

## Dependencies

- **Depends on:** Step 04 (repo.mark_succeeded, repo.update_stage), Step 05 (stage contract), Step 07 (provides result_json)
- **Informs:** Step 09 (completes the pipeline — polling loop can claim next job)
