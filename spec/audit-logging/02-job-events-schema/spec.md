# Step 02 — Job Events Schema

## Scope

**In scope:**

- DDL for the `job_events` table
- Column definitions, types, constraints, and indexes
- Permission model
- Event type vocabulary

**Out of scope:**

- Repository methods that write to this table (Steps 05-06)
- Trigger-based automatic event creation (events are written explicitly by application code)

## Context

The `analysis_jobs` table tracks the current state of each job but has no history. The `job_events` table acts as an append-only event log capturing every significant state transition. It is a child of `analysis_jobs` via foreign key.

The existing `analysis_jobs` table uses `text` columns (not enums) for `status` and `stage`. This table follows the same convention for `event_type` to avoid Postgres enum migration friction when adding new event types.

## Requirements

### R1 — Table definition

**Table:** `public.job_events`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `bigint GENERATED ALWAYS AS IDENTITY` | NOT NULL | auto | Sequential PK; append-only log does not need UUIDs |
| `job_id` | `uuid` | NOT NULL | — | FK to `analysis_jobs(id) ON DELETE CASCADE` |
| `event_type` | `text` | NOT NULL | — | Constrained by CHECK (see R2) |
| `stage` | `text` | YES | `NULL` | Pipeline stage at time of event; NULL when not applicable |
| `status` | `text` | YES | `NULL` | Job status at time of event (queued/running/succeeded/failed) |
| `error_code` | `text` | YES | `NULL` | Machine-readable error code; only set for `job_failed`/`job_requeued` |
| `error_detail` | `text` | YES | `NULL` | Human-readable detail; truncated to 200 chars by application code |
| `attempt` | `int` | YES | `NULL` | Which attempt number triggered this event |
| `metadata` | `jsonb` | NOT NULL | `'{}'` | Extensible context bag |
| `created_at` | `timestamptz` | NOT NULL | `now()` | Event timestamp |

### R2 — Event type vocabulary

The `event_type` column is constrained by a CHECK:

```sql
CHECK (event_type IN (
    'job_created',
    'job_claimed',
    'stage_changed',
    'job_succeeded',
    'job_failed',
    'job_requeued'
))
```

| Event Type | Emitted By | When | Typical metadata |
|---|---|---|---|
| `job_created` | Backend | `POST /api/analysis/start` creates the job row | `{"sha256": "...", "source_type": "pdf", "bucket": "uploads", "path": "..."}` |
| `job_claimed` | Worker | `claim_analysis_job` RPC returns a job | `{"lease_seconds": 300}` |
| `stage_changed` | Worker | `update_stage()` advances the pipeline stage | `{"previous_stage": "created", "new_stage": "extract_done"}` |
| `job_succeeded` | Worker | `mark_succeeded()` finalizes the job | `{"references_count": 42}` |
| `job_failed` | Worker | `mark_failed(requeue=False)` — terminal failure | `{}` (error_code/error_detail in dedicated columns) |
| `job_requeued` | Worker | `mark_failed(requeue=True)` — transient failure, will retry | `{}` (error_code/error_detail in dedicated columns) |

### R3 — Indexes

| Index | Columns | Purpose |
|---|---|---|
| `idx_job_events_job_id` | `job_id` | Fast lookup of all events for a specific job |
| `idx_job_events_created_at` | `created_at` | Efficient retention cleanup (DELETE WHERE created_at < cutoff) |

### R4 — Permissions

```sql
REVOKE ALL ON public.job_events FROM PUBLIC;
GRANT SELECT, INSERT ON public.job_events TO service_role;
GRANT USAGE ON SEQUENCE public.job_events_id_seq TO service_role;
```

- `service_role` only — no direct browser/anon access
- `SELECT` + `INSERT` only — audit rows are immutable (no UPDATE/DELETE by application code)
- Sequence grant required for IDENTITY column inserts

### R5 — Migration file

**File:** `supabase/migrations/20260311000000_create_audit_logging_tables.sql`

This migration creates both `job_events` and `reference_audit_log` (Step 03) in a single file, since they are part of the same feature and have no circular dependencies.

## Acceptance Criteria

- [ ] Table `public.job_events` exists with all columns, types, and defaults as specified
- [ ] CHECK constraint on `event_type` rejects values outside the vocabulary
- [ ] Foreign key to `analysis_jobs(id)` with `ON DELETE CASCADE` is active
- [ ] Both indexes exist
- [ ] Only `service_role` has SELECT/INSERT; PUBLIC has no access
- [ ] Inserting a row with a valid `event_type` succeeds
- [ ] Inserting a row with an invalid `event_type` fails with a constraint violation
- [ ] Deleting an `analysis_jobs` row cascades to delete associated `job_events` rows

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Insert with `event_type = 'unknown'` | Rejected by CHECK constraint |
| Insert with `job_id` referencing non-existent job | Rejected by FK constraint |
| Insert with `metadata = NULL` | Rejected by NOT NULL; use `'{}'` for empty metadata |
| Multiple events with same `job_id` and `event_type` | Allowed — a job may be claimed multiple times (retries) |
| Concurrent inserts for the same job | Safe — no unique constraints on (job_id, event_type) |

## Integration Points

- **Step 05 (Backend Audit Repo):** writes `job_created` events to this table
- **Step 06 (Worker Audit Repo):** writes all other event types to this table
- **Step 04 (Retention Policy):** `cleanup_expired_data` deletes rows from this table
