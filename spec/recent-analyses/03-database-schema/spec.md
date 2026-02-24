# Step 03 — Database Schema Requirements

## Scope

This step specifies the data structure changes needed to support job tokens and expiry. It covers:
- New columns to be added to the existing `analysis_jobs` table
- Column types and constraints
- Default values and nullable rules
- Indexing recommendations (for query performance, not optimization details)

This step does NOT cover:
- SQL syntax or DDL statements
- Migration scripts or version control
- Data warehousing, backups, or archival strategies
- Replication or failover mechanisms
- Specific database version or platform choices (assumes PostgreSQL per system architecture)

## Context

The existing `analysis_jobs` table already has columns for `id` (job ID), `status`, `stage`, `results`, and `error`. To support the job access model (Step 02), two new columns must be added to store the token and its expiry time.

## Requirements

1. A new column `job_token` must be added to store the unique token assigned at job creation.
   - Must accept string/text values
   - Must be non-nullable (every job must have a token)
   - Should be indexed for fast lookups during validation queries

2. A new column `token_expires_at` must be added to store the token expiry timestamp.
   - Must accept datetime/timestamp values
   - Must be non-nullable (expiry time is always set at job creation)
   - Should be indexed to support time-based queries (e.g., finding expired tokens)

3. Both columns must have default values or be populated at job creation time (not null).

4. Neither column should be exposed in user-facing output (e.g., API responses to frontend) unless explicitly required by a business rule.

5. The schema change must be backward-compatible (existing jobs without tokens should not cause application errors, or a migration strategy must be defined).

## Acceptance Criteria

- The `job_token` column exists and can store a unique string value
- The `token_expires_at` column exists and can store a timestamp with precision to at least 1 second
- Both columns are non-nullable and have appropriate defaults
- A job created after the schema change has both values populated
- A query to retrieve a job by `id` and validate the token can be executed efficiently
- The new columns do not break existing queries or application logic

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Querying job status for a token that was never created | 404 (handled at application layer, not database) |
| Job created before schema change (missing token columns) | Migration strategy must handle this; new queries assume both columns exist |
| Token collision (same token value for different jobs) | Should be impossible if token generation is cryptographically secure; database uniqueness constraints can enforce this if needed |
| Querying at exactly the expiry timestamp (e.g., 1 hour to the nanosecond) | Job is considered expired if current time >= expiry time |
| Multiple jobs with overlapping expiry times | No issue; expiry is checked per-job, not globally |
| Timezone handling | Timestamps must be stored in a consistent timezone (UTC recommended) |

## Storage Considerations

- Token string size: Estimate 32-64 characters (exact size depends on token generation algorithm; to be confirmed with backend team)
- Timestamp precision: 1-second granularity is sufficient (e.g., `TIMESTAMP` or `TIMESTAMPTZ` in PostgreSQL)
- Index strategy: Both columns should have individual indexes; a composite index on `(id, job_token, token_expires_at)` may improve validation query performance (to be determined by database team)

## Dependencies

- Depends on Step 02 (Job Access Model) for clarity on token lifecycle and expiry rules
- Step 04 (Job Creation Endpoint) will write to these columns
- Step 05 (Job Status Endpoint) will read from these columns for validation
