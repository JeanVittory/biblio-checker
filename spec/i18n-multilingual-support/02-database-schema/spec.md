# Step 02 — Database Schema: `analysis_jobs.locale`

## Scope

- Add a `locale` column to `analysis_jobs` with a CHECK constraint restricting values to the supported locales.
- Ensure the `claim_analysis_job` RPC returns `locale` so the worker receives it alongside the job payload.
- Provide a forward-compatible default so that existing rows (and inserts that omit `locale`) continue to work.

**Out of scope:** Backend schema/controller changes (Step 03). Worker consumption of the locale (Step 05). Frontend wiring (Step 11).

## Context

The worker reads job data by calling the RPC `claim_analysis_job` (see `apps/worker/biblio_checker_worker/jobs/repo.py`). Every field the worker needs must either be in `analysis_jobs` or joined in by the RPC. Since the worker needs to render text in the user's language, `locale` must travel through the RPC result.

Existing `analysis_jobs` columns (for reference — do not modify): `id`, `sha256`, `source_type`, `storage_path`, `status`, `poll_status_token`, `worker_lease_token`, `claim_deadline_at`, `results`, `error`, `created_at`, `updated_at`.

## Requirements

### 1. Create Migration File

**File:** `supabase/migrations/<YYYYMMDDHHMMSS>_add_locale_to_analysis_jobs.sql`

Use the project's existing timestamp convention. Content:

```sql
-- Add locale column to analysis_jobs so the worker can render decisionReason
-- and warnings[].message in the user's selected language.
-- Supported locales: es (default), pt, en.

ALTER TABLE analysis_jobs
  ADD COLUMN locale TEXT NOT NULL DEFAULT 'es';

ALTER TABLE analysis_jobs
  ADD CONSTRAINT analysis_jobs_locale_check
  CHECK (locale IN ('es', 'pt', 'en'));

COMMENT ON COLUMN analysis_jobs.locale IS
  'Language the worker must use when rendering decisionReason and warning messages. Immutable after insert.';
```

**Rationale for `NOT NULL DEFAULT 'es'`:**
- Existing rows (if any exist in the target environment) are backfilled to `'es'` — matches current behaviour.
- New inserts that omit `locale` keep working during the rollout of Step 03.

### 2. `claim_analysis_job` RPC — Automatically Projects `locale`

**Canonical source of truth:** `supabase/migrations/20260228000000_create_claim_analysis_job_rpc.sql` — this is the live RPC. Its real signature is:

```sql
CREATE OR REPLACE FUNCTION public.claim_analysis_job(
    p_token      text,
    p_lease_secs int DEFAULT 300
) RETURNS SETOF analysis_jobs
```

It uses `RETURNS SETOF analysis_jobs` and `RETURNING *` — i.e. **it already projects every column of the table**. This means adding a column to `analysis_jobs` automatically propagates to the RPC result; no RPC-signature change is required.

**Action for this step:** No additional migration to the RPC. The column added in Section 1 is enough — the RPC will return `locale` on its own the next time it executes. Step 05 must consume `row["locale"]` from the dict returned by `supabase.rpc("claim_analysis_job", {"p_token": ..., "p_lease_secs": ...}).execute().data`.

If a future refactor changes the RPC to return an explicit column list, that refactor must add `locale` to the list — but that refactor is out of scope here.

### 3. Index Strategy

No additional index is required. `locale` is never used in a WHERE filter for queueing; it is only projected into the RPC output.

### 4. Data Migration for Existing Rows

No explicit backfill statement is needed — `DEFAULT 'es'` + `NOT NULL` guarantees every pre-existing row has `locale = 'es'`. The migration is safe to run against a populated table.

### 5. Idempotency

Both migrations must be idempotent against repeated runs in local dev:

```sql
-- At the top of 01_add_locale_to_analysis_jobs.sql
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'analysis_jobs' AND column_name = 'locale'
  ) THEN
    ALTER TABLE analysis_jobs ADD COLUMN locale TEXT NOT NULL DEFAULT 'es';
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'analysis_jobs' AND constraint_name = 'analysis_jobs_locale_check'
  ) THEN
    ALTER TABLE analysis_jobs
      ADD CONSTRAINT analysis_jobs_locale_check CHECK (locale IN ('es','pt','en'));
  END IF;
END $$;
```

(Match whatever idempotency style the rest of the suite uses — inspect a recent migration first.)

### 6. RLS Policies

No changes. `analysis_jobs` is accessed exclusively via the service role key from backend/worker; adding a column does not require new policies.

## Acceptance Criteria

- [ ] Running `pnpm --filter ... supabase db reset` (or the project's local equivalent) against a fresh DB produces an `analysis_jobs` table with a `locale TEXT NOT NULL DEFAULT 'es'` column.
- [ ] `INSERT INTO analysis_jobs (..., locale) VALUES (..., 'xx')` fails with a CHECK constraint violation.
- [ ] `INSERT INTO analysis_jobs (...)` **without** `locale` succeeds and the row has `locale = 'es'`.
- [ ] `SELECT * FROM claim_analysis_job(60)` returns a row that includes a non-null `locale`.
- [ ] Existing worker polling flow does not break when the new migration is present but the worker code has not yet been updated (because the extra column is simply ignored by the destructuring until Step 05).
- [ ] Both migrations are idempotent — re-running them is a no-op.

## Verification

1. Run the migrations locally: `pnpm --filter ... supabase migration up` (use the project's actual command).
2. Connect with `psql` or Supabase Studio and run `\d analysis_jobs` — confirm the `locale` column and the CHECK constraint.
3. Run `SELECT claim_analysis_job(60);` after inserting a test job — confirm the returned row has a `locale` field.

## Dependencies

- **Depends on:** Step 01 (locale set definition)
- **Informs:** Step 03 (backend reads/writes the column), Step 05 (worker plumbs it into `GraphState`)
