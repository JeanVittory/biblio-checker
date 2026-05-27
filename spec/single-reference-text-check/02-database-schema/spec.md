# Step 02 — Database Schema

## Scope

This step specifies the Supabase migration that extends `analysis_jobs` to support text-only input. It covers:
- New columns and their types
- Nullability changes to existing columns
- A CHECK constraint enforcing per-mode field presence
- Backward compatibility with existing rows
- Impact on existing RPCs (`claim_analysis_job`, `cleanup_expired_data`)

This step does NOT cover:
- The endpoint that writes text-mode rows (Step 03)
- The worker logic that reads `input_kind` (Step 04)
- Frontend changes

## Context

`analysis_jobs` currently requires `bucket`, `path`, `sha256`, and `source_type` to be NOT NULL because every job is sourced from a file uploaded to Supabase Storage. To support a parallel "text input" mode, these four columns must become nullable, and a discriminator column (`input_kind`) plus a `raw_reference_text` column must be added. A CHECK constraint guarantees that file-mode rows have the file fields populated and text-mode rows have the text field populated — never both, never neither.

## Requirements

### 1) New Columns

The migration MUST add the following columns to `analysis_jobs`:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `input_kind` | `TEXT` | NO | `'file'` | Discriminator: `'file'` or `'text'` |
| `raw_reference_text` | `VARCHAR(2000)` | YES | `NULL` | Pasted reference text for text-mode jobs (DB-layer cap mirrors the Pydantic 2000-char limit as defense-in-depth) |

`input_kind` MUST have a CHECK constraint: `input_kind IN ('file','text')`.

### 2) Existing Columns Become Nullable

The migration MUST drop the NOT NULL constraint on the following existing columns:

| Column | Before | After |
|--------|--------|-------|
| `bucket` | NOT NULL | NULL allowed |
| `path` | NOT NULL | NULL allowed |
| `sha256` | NOT NULL | NULL allowed |
| `source_type` | NOT NULL | NULL allowed |

### 3) Per-Mode CHECK Constraint

The migration MUST add a CHECK constraint on `analysis_jobs` that enforces the following invariant:

```
(input_kind = 'file'
   AND bucket IS NOT NULL
   AND path IS NOT NULL
   AND sha256 IS NOT NULL
   AND source_type IS NOT NULL
   AND raw_reference_text IS NULL)
OR
(input_kind = 'text'
   AND bucket IS NULL
   AND path IS NULL
   AND sha256 IS NULL
   AND source_type IS NULL
   AND raw_reference_text IS NOT NULL)
```

The constraint name SHOULD be `analysis_jobs_input_kind_consistency`.

### 4) Backfill Behavior

The `input_kind` column is added with `DEFAULT 'file'`, so all existing rows automatically have `input_kind = 'file'` after the migration. No explicit `UPDATE` statement is required, but the migration MAY include an explicit `UPDATE analysis_jobs SET input_kind = 'file' WHERE input_kind IS NULL` for safety (idempotent).

### 5) Index Considerations

`input_kind` SHOULD NOT have a dedicated index. The cardinality is 2 and the column is read alongside the row when claiming jobs; a partial index would not improve any current query.

`raw_reference_text` MUST NOT have an index (it is read-only at job-claim time and never used as a search key).

### 6) Backward Compatibility

The migration MUST NOT alter or drop any existing columns beyond removing the NOT NULL constraint on the four file fields. All existing queries, RPCs, and application code MUST continue to work without modification on file-mode rows.

### 7) Impact on `claim_analysis_job` RPC

**Resolved during spec review:** The current RPC (most recent version: `supabase/migrations/20260301000001_fix_claim_rpc_for_split_tokens.sql`) returns `SETOF analysis_jobs` and uses `RETURNING *`. New columns added to `analysis_jobs` are returned automatically without modifying the function. **No `CREATE OR REPLACE FUNCTION` is required as part of this migration.**

The implementer MUST verify this assumption holds against the actual most-recent RPC migration before applying Step 02; if a future RPC version enumerates columns explicitly, the migration MUST be amended to replace the function in the same file.

### 8) Impact on `cleanup_expired_data` RPC

The existing `cleanup_expired_data(p_retention_days)` RPC deletes from `analysis_jobs`, `job_events`, and `reference_audit_log` based on `created_at`. Text-mode jobs participate in this cleanup unchanged. No modification is required.

### 9) Impact on `reference_audit_log` and `job_events`

Neither table has columns that depend on `input_kind`. Text-mode jobs emit the same `job_events` lifecycle entries (created, claimed, stage_changed, succeeded/failed, requeued) and write per-reference rows to `reference_audit_log` exactly like file-mode jobs. No schema changes required.

### 10) Migration File

The migration MUST be delivered as a SQL file in `supabase/migrations/` following the existing naming convention: `YYYYMMDDHHMMSS_add_text_input_mode.sql`.

The migration MUST be idempotent: running it twice on the same database MUST NOT raise an error. Use `IF NOT EXISTS` / `IF EXISTS` clauses where supported, and check for the constraint by name before adding.

### 11) Manual Application

Per the project convention (memory: `feedback_migrations_manual`), the migration is delivered as a SQL file only. The implementer MUST NOT attempt to apply it programmatically (e.g., via `supabase db push`, `psql`, or any RPC). The user applies migrations manually in the Supabase cloud dashboard.

## Acceptance Criteria

- Migration adds `input_kind TEXT NOT NULL DEFAULT 'file'` with CHECK `IN ('file','text')`
- Migration adds `raw_reference_text VARCHAR(2000) NULL`
- Migration removes NOT NULL from `bucket`, `path`, `sha256`, `source_type`
- Migration adds CHECK constraint `analysis_jobs_input_kind_consistency` enforcing per-mode field presence
- Existing rows transparently take `input_kind = 'file'`; no data loss or constraint violation on the existing dataset
- A test INSERT with `input_kind='text'`, `raw_reference_text=<some text>`, all file fields NULL → succeeds
- A test INSERT with `input_kind='file'`, all file fields populated, `raw_reference_text=NULL` → succeeds
- A test INSERT with `input_kind='text'` AND any file field populated → rejected by CHECK
- A test INSERT with `input_kind='file'` AND `raw_reference_text=<text>` → rejected by CHECK
- A test INSERT with `input_kind='neither'` → rejected by `input_kind` CHECK
- `claim_analysis_job` RPC returns rows with `input_kind` and `raw_reference_text` populated
- Migration is idempotent (running twice is a no-op)
- Migration is delivered as a SQL file; not applied programmatically

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Migration runs on database with thousands of existing rows | All take `input_kind='file'`; CHECK validates without error because file fields are populated |
| Existing row has somehow NULL `bucket` (data corruption) | CHECK constraint REJECTS the migration. Implementer must inspect and clean before applying. The migration MAY include a `DO` block that counts violators and raises a NOTICE, but MUST NOT silently delete rows |
| RPC returns rows without `input_kind` (column was added but RPC was not updated) | Worker treats the field as missing → text-mode jobs are silently processed as file-mode and fail. **Mitigation:** Step 04 includes a defensive check; the migration MUST verify RPC compatibility |
| Two simultaneous migrations on the same DB | Migration is idempotent; second run is a no-op |
| Database is fresh (no existing rows) | Migration adds columns and constraints; no backfill needed |

## Integration Points

- Step 03 (Backend Text Endpoint) — writes rows with `input_kind='text'` and `raw_reference_text`
- Step 04 (Worker Text Mode) — reads `input_kind` and `raw_reference_text` from the claimed job
- `apps/backend/app/services/analysis_jobs_repo.py` — `AnalysisJob` Pydantic/dataclass model MUST be extended to include the new columns and to mark the four file fields optional
- `apps/worker/biblio_checker_worker/db/models.py` (or equivalent) — same dataclass extension on the worker side

## Dependencies

- None (foundational step)
