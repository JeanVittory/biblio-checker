# Step 01 — State Machine Definition

## Scope

- Define the two-axis state model: `status` (coarse lifecycle) and `stage` (fine-grained progress)
- Enumerate all valid values for each axis
- Define the complete transition table with triggers and guards
- Establish the domain meaning of each stage

**Out of scope:** Implementation of the state machine in Python code (see Step 03 for enums, Step 04 for repo transitions).

## Context

The `analysis_jobs` table already enforces allowed values via CHECK constraints:
- `status`: `queued`, `running`, `succeeded`, `failed`
- `stage`: `created`, `extract_done`, `langgraph_running`, `verifying_references`, `persisting_result`, `done`

These constraints exist at the database level but have no corresponding application logic. This step formalizes the state machine so that all subsequent steps implement transitions consistently.

## Requirements

### 1. Two-Axis State Model

The job lifecycle is governed by two independent but correlated columns:

- **status** represents the coarse lifecycle phase. It controls visibility to the frontend (queued/running jobs are "in progress", succeeded/failed are terminal).
- **stage** represents the fine-grained progress within the `running` status. It tells the worker (and observability) exactly where in the pipeline a job is.

### 2. Status Values and Semantics

| Status | Meaning | Terminal? |
|--------|---------|-----------|
| `queued` | Job is waiting to be claimed by a worker | No |
| `running` | A worker has claimed this job and is actively processing it | No |
| `succeeded` | Processing completed successfully; `result_json` is populated | Yes |
| `failed` | Processing failed permanently; `error_code` and `error_detail` are populated | Yes |

- `succeeded` and `failed` are sink states. No transitions out of them are allowed.
- A job may transition from `running` back to `queued` on a retryable failure (see retry spec, Step 10).

### 3. Stage Values and Semantics

Stages only progress forward while `status = running`. The domain of each stage:

| Stage | Domain | Description |
|-------|--------|-------------|
| `created` | Initialization | Job has been claimed. The file has not been fetched yet. This is the entry point after claiming. |
| `extract_done` | File acquisition | The document has been downloaded from Supabase Storage and its SHA-256 hash has been verified against the stored value. The raw file bytes are available in memory. |
| `langgraph_running` | Orchestration | The LangGraph graph has been invoked. The system is extracting bibliographic references from the document text and building the verification plan. |
| `verifying_references` | API verification | The system is actively calling external academic APIs (OpenAlex, SciELO, arXiv) to verify each extracted reference. |
| `persisting_result` | Result persistence | API verification is complete. The system is validating the result against the ResultsV1 schema and writing `result_json` to the database. |
| `done` | Completion | The result has been successfully persisted. The job is ready for status transition to `succeeded`. |

### 4. Valid Transition Table

| # | From Status | From Stage | Trigger | To Status | To Stage |
|---|-------------|------------|---------|-----------|----------|
| T1 | `queued` | `created` | Worker claims the job via RPC | `running` | `created` |
| T2 | `running` | `created` | File downloaded and SHA-256 verified | `running` | `extract_done` |
| T3 | `running` | `extract_done` | LangGraph graph invoked | `running` | `langgraph_running` |
| T4 | `running` | `langgraph_running` | Graph begins API verification calls | `running` | `verifying_references` |
| T5 | `running` | `verifying_references` | All references verified, result assembled | `running` | `persisting_result` |
| T6 | `running` | `persisting_result` | `result_json` written to DB | `succeeded` | `done` |
| T7 | `running` | *any* | Transient error AND attempts < max_attempts | `queued` | `created` |
| T8 | `running` | *any* | Terminal error OR attempts >= max_attempts | `failed` | *(preserved)* |

### 5. Transition Rules

1. Stage transitions (T2–T6) MUST be sequential. Skipping a stage is not allowed.
2. Stage transitions only occur while `status = running`.
3. Transition T7 (requeue) resets the stage to `created`. The job will be re-processed from scratch on the next claim. This is a v1 simplification; the design accommodates future migration to resume-from-last-stage by preserving the stage column instead of resetting it.
4. Transition T8 (permanent failure) preserves the current stage for debugging purposes. The `error_code` and `error_detail` columns are populated.
5. Transition T1 (claim) is performed atomically by a Postgres RPC function (see Step 02). It increments `attempts` and sets a lease token.
6. No transitions are allowed out of `succeeded` or `failed`.

### 6. Stage-Status Compatibility Matrix

| Stage | queued | running | succeeded | failed |
|-------|--------|---------|-----------|--------|
| `created` | Valid (initial) | Valid (post-claim) | — | Valid (failed at init) |
| `extract_done` | — | Valid | — | Valid (failed after extract) |
| `langgraph_running` | — | Valid | — | Valid (failed during graph) |
| `verifying_references` | — | Valid | — | Valid (failed during verify) |
| `persisting_result` | — | Valid | — | Valid (failed during persist) |
| `done` | — | — | Valid (only terminal success) | — |

## Acceptance Criteria

- Every allowed value for `status` and `stage` has a documented semantic definition
- The transition table covers all possible state changes including error paths
- Forward-only stage progression is enforced (no backward stage transitions while running)
- Terminal states (`succeeded`, `failed`) have no outbound transitions
- The requeue transition (T7) resets stage to `created`
- The failure transition (T8) preserves the current stage for observability

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Worker crashes mid-stage (e.g., during `langgraph_running`) | Job stays at `status=running`, `stage=langgraph_running` until lease expires. Then eligible for T7 via re-claim. |
| Job has `attempts = max_attempts` and encounters a transient error | Transition T8 applies (permanent failure), not T7 |
| Job is in `succeeded` and another worker tries to claim it | The claim RPC only selects `status=queued` rows; this job is invisible to claiming |
| Job is in `failed` and `attempts < max_attempts` | No transition. `failed` is a sink state. Manual intervention required to requeue. |
| Two workers claim the same queued job simultaneously | Resolved by the atomic RPC (see Step 02). Only one succeeds. |

## Dependencies

- **Depends on:** None (foundational step)
- **Informs:** Step 02 (claiming mechanism uses T1), Step 03 (Python enums mirror these values), Step 04 (repo functions enforce transitions), Step 05 (pipeline stages map to stage values), Step 10 (retry logic uses T7/T8)
