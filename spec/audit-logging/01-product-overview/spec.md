# Step 01 — Product Overview

## Scope

**In scope:**

- Define the goals and non-goals of the audit logging infrastructure
- Identify the traceability requirements for jobs and references
- Establish the data retention policy

**Out of scope:**

- UI for viewing audit data (future work)
- Alerting or notification based on audit events
- Real-time streaming of events

## Context

Biblio Checker processes uploaded academic documents through a multi-stage pipeline (extract, LangGraph analysis, persist). Each document may contain tens to hundreds of bibliographic references, each verified against external sources (OpenAlex, SciELO, arXiv).

Today, the only observable state is the current snapshot in `analysis_jobs`: a single `status`, `stage`, `error_code`, and `error_detail`. When a job fails, there is no record of which stages it passed through, how many times it was retried, or when each transition occurred. When a job succeeds, individual reference outcomes are embedded in the `result_json` blob but cannot be queried independently.

## Requirements

### R1 — Job lifecycle traceability

The system must record a timestamped event for every significant state transition of a job:

1. Job creation (backend receives upload)
2. Job claim (worker acquires lease)
3. Stage advancement (each pipeline stage transition)
4. Job success (pipeline completes)
5. Job failure (terminal error, no more retries)
6. Job requeue (transient error, will retry)

Each event must capture: job ID, event type, current stage, current status, attempt number, and an extensible metadata bag for context-specific data.

### R2 — Per-reference audit trail

After verification completes, the system must record one row per reference with:

- The reference identifier and raw citation text
- Classification outcome (verified, suspicious, not_found, etc.)
- Confidence score and reason code
- Which external sources were checked
- Whether a match was found
- Error details (for `processing_error` classifications)

This enables queries like "show all suspicious references across all jobs in the last 7 days" without parsing the full results blob.

### R3 — Data retention enforcement

All audit data and completed/failed jobs must be automatically cleaned up after 7 days. Jobs that are still queued or running must never be deleted regardless of age.

### R4 — Fire-and-forget semantics

Audit writes must never cause a user-facing error or prevent job processing. If the audit infrastructure is temporarily unavailable, the system must log a warning and continue normally.

### R5 — Infrastructure only

This suite defines the database tables and repository methods. The actual integration into the job creation flow, pipeline runner, and stage functions is deferred to a future implementation phase (described in Step 07 as a reference map).

## Acceptance Criteria

- [ ] Two new database tables exist: `job_events` and `reference_audit_log`
- [ ] A SQL function `cleanup_expired_data` exists and correctly purges data older than the specified retention period
- [ ] Backend has an async `insert_job_event` method that swallows errors
- [ ] Worker has sync `insert_job_event`, `insert_reference_audit_batch`, and `build_reference_audit_entry` methods that swallow errors
- [ ] All new Python code passes lint (`ruff`) and has unit tests
- [ ] No existing files are modified
- [ ] No existing tests break

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Supabase is unreachable during audit write | Log WARNING, return normally, job processing continues |
| Job is deleted while events are being written | CASCADE handles orphan prevention; insert may fail silently |
| Retention cleanup runs while a job is actively being processed | `queued`/`running` jobs are excluded from deletion |
| A job has 0 references (empty document) | No rows inserted into `reference_audit_log`; `job_succeeded` event still recorded |
| `cleanup_expired_data` is called with 0 retention days | Deletes all completed/failed jobs and their audit data |
