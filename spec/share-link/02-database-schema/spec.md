# Step 02 — Database Schema

## Scope

This step specifies the database migration that adds share token support to the `analysis_jobs` table. It covers:
- New columns and their types
- Constraints and defaults
- Index requirements
- Impact on existing RPC functions

This step does NOT cover:
- How tokens are generated (see Step 03)
- How tokens are used for public access (see Step 04)
- Frontend changes

## Context

The `analysis_jobs` table already has two token columns: `poll_status_token` (frontend polling, 1h TTL) and `job_token` (worker lease, 5min TTL). The share token is a third, independent token with a longer TTL (7 days) that enables public read-only access to completed job results.

## Requirements

### 1) New Columns

The migration MUST add the following columns to the `analysis_jobs` table:

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `share_token` | `TEXT` | YES | `NULL` | URL-safe share token; NULL when not shared |
| `share_token_expires_at` | `TIMESTAMPTZ` | YES | `NULL` | Expiry timestamp; NULL when not shared |

### 2) Uniqueness Constraint

`share_token` MUST have a `UNIQUE` constraint. This ensures:
- No two jobs can have the same share token
- Token lookup is efficient (implicitly creates an index)
- Token collision is prevented at the database level

### 3) Nullability

Both columns MUST be nullable. A job that has not been shared has `share_token = NULL` and `share_token_expires_at = NULL`. This is the default state for all jobs.

### 4) No Default TTL in Schema

The TTL (7 days) is NOT enforced in the database schema. It is computed by the backend at token generation time (`NOW() + INTERVAL '7 days'`). The schema only stores the resulting timestamp.

### 5) Backward Compatibility

The migration MUST NOT alter or drop any existing columns. All existing queries, RPCs, and application code MUST continue to work without modification after the migration runs.

### 6) Impact on `cleanup_expired_data` RPC

The existing `cleanup_expired_data(p_retention_days)` RPC deletes rows from `analysis_jobs` based on `created_at`. When a job row is deleted, the share token is automatically removed with it. No changes to this RPC are needed.

### 7) Impact on `claim_analysis_job` RPC

The `claim_analysis_job` RPC operates on `job_token` and `status` columns only. The new share token columns do not affect it. No changes to this RPC are needed.

### 8) Migration File

The migration MUST be delivered as a SQL file in `supabase/migrations/` following the existing naming convention: `YYYYMMDDHHMMSS_description.sql`.

## Acceptance Criteria

- Migration adds `share_token TEXT UNIQUE` column to `analysis_jobs`
- Migration adds `share_token_expires_at TIMESTAMPTZ` column to `analysis_jobs`
- Both columns default to NULL
- Existing rows are not affected (all get NULL for both columns)
- Existing queries, RPCs, and application code continue to work
- The UNIQUE constraint prevents duplicate share tokens
- Migration is idempotent (can be run on a fresh or existing database)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Migration runs on existing database with data | Existing rows get NULL for both columns; no data loss |
| Two tokens generated simultaneously with same value | UNIQUE constraint rejects the second insert; application retries |
| Job is deleted by `cleanup_expired_data` | Share token is deleted with the row (cascade not needed — same row) |

## Integration Points

- Step 03 (Share Token Generation) writes to these columns
- Step 04 (Public Read Endpoint) reads from these columns
- Existing `get_analysis_job_by_id` in `analysis_jobs_repo.py` should include new columns in SELECT

## Dependencies

- None (foundational step)
