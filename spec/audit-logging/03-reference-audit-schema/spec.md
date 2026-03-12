# Step 03 — Reference Audit Schema

## Scope

**In scope:**

- DDL for the `reference_audit_log` table
- Column definitions, types, constraints, and indexes
- Permission model
- Relationship to `ResultsV1.references` schema

**Out of scope:**

- Repository methods that write to this table (Step 06)
- Querying or aggregating reference audit data (future admin endpoints)

## Context

When the worker completes a job successfully, the full verification result is stored as a JSON blob in `analysis_jobs.result_json`. This blob contains an array of `ReferenceResult` objects — one per bibliographic reference found in the document.

The `reference_audit_log` table denormalizes key fields from each `ReferenceResult` into queryable columns. This enables cross-job analytics (e.g., "which references are most frequently flagged as suspicious") and per-reference failure investigation without parsing JSON blobs.

### Field mapping from ResultsV1

| ResultsV1 field | Audit column | Notes |
|---|---|---|
| `referenceId` | `reference_id` | Unique within a job |
| `rawText` | `raw_text` | Original citation string |
| `classification` | `classification` | Enum: verified, likely_verified, ambiguous, not_found, suspicious, processing_error |
| `confidenceScore` | `confidence_score` | 0.0-1.0 or NULL |
| `reasonCode` | `reason_code` | 10 stable reason codes |
| `evidence[].source` | `sources_checked` | Deduplicated array of source names |
| `len(evidence) > 0` | `match_found` | Boolean derived from evidence array |
| `decisionReason` (when `classification` = `processing_error`) | `error_detail` | Only for `processing_error`; see `ReferenceResult.decisionReason` in `results.py` |

## Requirements

### R1 — Table definition

**Table:** `public.reference_audit_log`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `bigint GENERATED ALWAYS AS IDENTITY` | NOT NULL | auto | Sequential PK |
| `job_id` | `uuid` | NOT NULL | — | FK to `analysis_jobs(id) ON DELETE CASCADE` |
| `reference_id` | `text` | NOT NULL | — | Matches `ReferenceResult.referenceId` |
| `raw_text` | `text` | YES | `NULL` | Original citation string from the document |
| `classification` | `text` | YES | `NULL` | Verification outcome |
| `confidence_score` | `double precision` | YES | `NULL` | 0.0-1.0; NULL for `processing_error` |
| `reason_code` | `text` | YES | `NULL` | Machine-readable reason (e.g., `exact_doi_match`) |
| `sources_checked` | `text[]` | NOT NULL | `'{}'` | Array of external sources queried |
| `match_found` | `boolean` | YES | `NULL` | Whether any source returned a match |
| `error_detail` | `text` | YES | `NULL` | Only populated for `processing_error` classification |
| `created_at` | `timestamptz` | NOT NULL | `now()` | Insertion timestamp |

### R2 — Indexes

| Index | Columns | Purpose |
|---|---|---|
| `idx_ref_audit_job_id` | `job_id` | All references for a specific job |
| `idx_ref_audit_classification` | `classification` | Cross-job queries by outcome (e.g., all `suspicious`) |
| `idx_ref_audit_created_at` | `created_at` | Efficient retention cleanup |

### R3 — Permissions

```sql
REVOKE ALL ON public.reference_audit_log FROM PUBLIC;
GRANT SELECT, INSERT ON public.reference_audit_log TO service_role;
GRANT USAGE ON SEQUENCE public.reference_audit_log_id_seq TO service_role;
```

Same model as `job_events`: service_role only, SELECT + INSERT only, immutable rows.

### R4 — Migration file

Included in the same migration as `job_events`: `supabase/migrations/20260311000000_create_audit_logging_tables.sql`

### R5 — No application-level constraints

The table does not enforce classification or reason_code values via CHECK constraints. These values come from the `ResultsV1` schema which is validated at the application level (Pydantic). The audit table is a denormalized copy — it records what the application produced, even if a future schema version adds new classification values.

## Acceptance Criteria

- [ ] Table `public.reference_audit_log` exists with all columns, types, and defaults as specified
- [ ] Foreign key to `analysis_jobs(id)` with `ON DELETE CASCADE` is active
- [ ] All three indexes exist
- [ ] Only `service_role` has SELECT/INSERT; PUBLIC has no access
- [ ] Bulk insert of multiple rows for the same `job_id` succeeds
- [ ] Deleting an `analysis_jobs` row cascades to delete associated `reference_audit_log` rows
- [ ] `sources_checked` accepts text arrays (e.g., `'{"openalex","scielo","arxiv"}'`)

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Job with 0 references | No rows inserted; table unaffected |
| Job with 200+ references | Single bulk insert succeeds (Supabase handles batch) |
| Duplicate `reference_id` within same `job_id` | Allowed at DB level (no unique constraint); application should prevent this |
| `classification = 'processing_error'` with non-null `confidence_score` | Allowed at DB level; application enforces nullability per ResultsV1 rules |
| `sources_checked = '{}'` (empty array) | Valid; indicates no external sources were queried |

## Integration Points

- **Step 06 (Worker Audit Repo):** `build_reference_audit_entry` maps `ReferenceResult` fields to this table's columns; `insert_reference_audit_batch` writes rows
- **Step 04 (Retention Policy):** `cleanup_expired_data` deletes rows from this table
- **ResultsV1 schema:** `apps/backend/app/schemas/results.py` defines the canonical field names and validation rules
