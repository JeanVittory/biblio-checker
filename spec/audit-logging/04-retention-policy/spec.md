# Step 04 — Retention Policy

## Scope

**In scope:**

- SQL function `cleanup_expired_data` for purging old data
- Deletion order and CASCADE behavior
- Scheduling considerations
- Safety rules for in-progress jobs

**Out of scope:**

- Supabase Storage file cleanup (separate concern; requires Storage API calls)
- pg_cron installation or Edge Function deployment (deployment concern)
- Configurable per-tenant retention periods

## Context

SYSTEM_SPEC (section "Data Retention") defines a 7-day retention target that is not yet implemented. This step creates the database function that enforces it. The function is designed to be called by an external scheduler (pg_cron, Supabase Edge Function cron, or manual invocation).

The deletion strategy leverages `ON DELETE CASCADE` on child tables (`job_events`, `reference_audit_log`) to automatically clean up associated audit data when parent `analysis_jobs` rows are deleted.

## Requirements

### R1 — Function signature

```sql
CREATE OR REPLACE FUNCTION public.cleanup_expired_data(
    p_retention_days int DEFAULT 7
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
```

### R2 — Deletion logic

The function executes three DELETE statements in this specific order:

**Phase 1 — Orphan audit rows:** Delete `job_events` and `reference_audit_log` rows where `created_at` is older than the cutoff, excluding rows belonging to in-progress jobs. This preserves the complete audit trail for any job that is still `queued` or `running`.

```sql
DELETE FROM public.job_events je
WHERE je.created_at < cutoff
  AND NOT EXISTS (
      SELECT 1 FROM public.analysis_jobs aj
      WHERE aj.id = je.job_id
        AND aj.status IN ('queued', 'running')
  );

DELETE FROM public.reference_audit_log ral
WHERE ral.created_at < cutoff
  AND NOT EXISTS (
      SELECT 1 FROM public.analysis_jobs aj
      WHERE aj.id = ral.job_id
        AND aj.status IN ('queued', 'running')
  );
```

**Phase 2 — Completed jobs:** Delete `analysis_jobs` rows where `created_at` is older than the cutoff AND `status` is terminal.

```sql
DELETE FROM public.analysis_jobs
WHERE created_at < cutoff
  AND status IN ('succeeded', 'failed');
```

CASCADE automatically deletes any remaining child rows in `job_events` and `reference_audit_log` for these jobs.

### R3 — Safety: never delete in-progress jobs

The WHERE clause explicitly filters `status IN ('succeeded', 'failed')`. Jobs with `status = 'queued'` or `status = 'running'` are never deleted, regardless of their age. This prevents data loss for stuck jobs that require investigation.

### R4 — Return value

The function returns a `jsonb` object summarizing what was deleted:

```json
{
    "cutoff": "2026-03-04T00:00:00+00:00",
    "deleted_events": 234,
    "deleted_references": 1890,
    "deleted_jobs": 15
}
```

Each count is obtained via `GET DIAGNOSTICS ... = ROW_COUNT` after each DELETE:
- `deleted_events`: rows removed from `job_events` in Phase 1 (direct DELETE)
- `deleted_references`: rows removed from `reference_audit_log` in Phase 1 (direct DELETE)
- `deleted_jobs`: rows removed from `analysis_jobs` in Phase 2

Note: Phase 2 CASCADE may delete additional child rows in `job_events` and `reference_audit_log`, but these are NOT reflected in the counts because PostgreSQL `GET DIAGNOSTICS ROW_COUNT` does not include cascade-deleted rows. This is acceptable because Phase 1 already deleted the majority of expired audit rows.

### R5 — Permissions

```sql
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_data(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cleanup_expired_data(int) TO service_role;
```

### R6 — Migration file

**File:** `supabase/migrations/20260311000001_create_retention_cleanup.sql`

Separate from the table creation migration to allow independent review and rollback.

### R7 — Scheduling guidance

The function itself does not schedule its own execution. The recommended scheduling approaches (in order of preference):

1. **pg_cron** (if available): `SELECT cron.schedule('cleanup-expired-data', '0 3 * * *', $$SELECT public.cleanup_expired_data(7)$$);`
2. **Supabase Edge Function** with cron trigger: invoke `supabase.rpc("cleanup_expired_data", {"p_retention_days": 7})`
3. **External cron job**: call the Supabase REST API with service_role key

Run daily at a low-traffic hour (e.g., 03:00 UTC).

## Acceptance Criteria

- [ ] Function `public.cleanup_expired_data` exists and is callable with `service_role`
- [ ] Calling with default parameter (7) deletes only rows older than 7 days
- [ ] Jobs with `status = 'queued'` or `status = 'running'` are never deleted
- [ ] Jobs with `status = 'succeeded'` or `status = 'failed'` older than cutoff are deleted
- [ ] CASCADE deletes child rows in `job_events` and `reference_audit_log`
- [ ] Return value is valid `jsonb` with all four keys
- [ ] Calling with `p_retention_days = 0` deletes all eligible data
- [ ] Calling on empty tables returns `jsonb` with all counts = 0
- [ ] PUBLIC cannot execute the function

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `p_retention_days = 0` | Cutoff = now(); deletes all completed/failed jobs and all audit rows |
| `p_retention_days = 365` | Only deletes data older than 1 year |
| No rows match the cutoff | Returns counts of 0; no errors |
| Job is `running` but 30 days old | NOT deleted (could be stuck, needs investigation) |
| Concurrent cleanup calls | Both succeed; second call finds fewer/no rows to delete |
| Audit row exists but parent job is `running` | Audit row preserved by Phase 1 (NOT EXISTS excludes rows with active parent jobs) |

## Integration Points

- **Steps 02-03:** This function deletes rows from `job_events` and `reference_audit_log`
- **`analysis_jobs` table:** This function deletes terminal jobs, relying on CASCADE for child cleanup
- **Deployment:** Scheduling mechanism is external to this migration
