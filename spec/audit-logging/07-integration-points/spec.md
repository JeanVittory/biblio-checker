# Step 07 — Integration Points

## Scope

**In scope:**

- Map of where audit functions will be called in existing code
- Event emission points for each event type
- Reference audit emission point
- Call patterns and parameter sources

**Out of scope:**

- Actually modifying existing code (this step is a reference map for future implementation)
- New API endpoints for querying audit data

## Context

Steps 02-06 create the infrastructure: tables, functions, enums, and repositories. This step documents exactly where in the existing codebase each audit function should be called when the integration phase begins. It serves as a checklist for the implementation team.

No code is written in this step. This is a reference document.

## Requirements

### R1 — Backend integration points

**File:** `apps/backend/app/api/controllers/analysis/start.py`

| Location | Event | Parameters |
|---|---|---|
| After `create_analysis_job(row)` succeeds (line ~60) | `job_created` | `job_id=job_row["id"]`, `status="queued"`, `metadata={"sha256": sha256, "source_type": source_type, "bucket": bucket, "path": path}` |

**Call pattern:**

```python
from app.services.audit_repo import insert_job_event
from app.schemas.audit_events import JobEventType

# After job creation succeeds:
await insert_job_event(
    job_id=job_row["id"],
    event_type=JobEventType.JOB_CREATED,
    status="queued",
    metadata={...},
)
```

This is the only backend integration point. The backend does not process jobs, so it only emits `job_created`.

### R2 — Worker integration points: polling loop

**File:** `apps/worker/biblio_checker_worker/polling/runner.py`

| Location | Event | Parameters |
|---|---|---|
| After `claim_one_job()` returns a job | `job_claimed` | `job_id`, `status="running"`, `attempt=job.attempts`, `metadata={"lease_seconds": settings.job_lease_seconds}` |

### R3 — Worker integration points: pipeline runner

**File:** `apps/worker/biblio_checker_worker/pipeline/runner.py`

| Location | Event | Parameters |
|---|---|---|
| After `mark_succeeded()` succeeds | `job_succeeded` | `job_id`, `status="succeeded"`, `stage="done"`, `attempt`, `metadata={"references_count": len(result_json.get("references", []))}` |
| After `mark_failed(requeue=False)` | `job_failed` | `job_id`, `status="failed"`, `stage` (preserved), `error_code`, `error_detail`, `attempt` |
| After `mark_failed(requeue=True)` | `job_requeued` | `job_id`, `status="queued"`, `error_code`, `error_detail`, `attempt` |

### R4 — Worker integration points: pipeline stages

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/extract.py`

| Location | Event | Parameters |
|---|---|---|
| After `repo.update_stage(stage=EXTRACT_DONE)` | `stage_changed` | `job_id`, `status="running"`, `stage="extract_done"`, `attempt`, `metadata={"previous_stage": "created"}` |

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py`

| Location | Event | Parameters |
|---|---|---|
| After `repo.update_stage(stage=LANGGRAPH_RUNNING)` | `stage_changed` | `job_id`, `stage="langgraph_running"`, `metadata={"previous_stage": "extract_done"}` |
| After `repo.update_stage(stage=VERIFYING_REFERENCES)` | `stage_changed` | `job_id`, `stage="verifying_references"`, `metadata={"previous_stage": "langgraph_running"}` |

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/persist.py`

| Location | Event | Parameters |
|---|---|---|
| After `repo.update_stage(stage=PERSISTING_RESULT)` | `stage_changed` | `job_id`, `stage="persisting_result"`, `metadata={"previous_stage": "verifying_references"}` |

### R5 — Worker integration point: reference audit batch

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/persist.py`

| Location | Action | Details |
|---|---|---|
| After `mark_succeeded()`, before function returns | Build entries + batch insert | Iterate `ctx.result_json["references"]`, call `build_reference_audit_entry` for each, then `insert_reference_audit_batch` |

**Call pattern:**

```python
from biblio_checker_worker.jobs.audit_repo import (
    build_reference_audit_entry,
    insert_reference_audit_batch,
)

entries = [
    build_reference_audit_entry(
        job_id=str(ctx.job.id),
        reference_id=ref["referenceId"],
        raw_text=ref.get("rawText"),
        classification=ref.get("classification"),
        confidence_score=ref.get("confidenceScore"),
        reason_code=ref.get("reasonCode"),
        sources_checked=[e["source"] for e in ref.get("evidence", [])],
        match_found=len(ref.get("evidence", [])) > 0,
        error_detail=ref.get("decisionReason") if ref.get("classification") == "processing_error" else None,
    )
    for ref in ctx.result_json.get("references", [])
]

insert_reference_audit_batch(supabase, job_id=str(ctx.job.id), entries=entries)
```

### R6 — Threading the Supabase client

The worker audit functions require a `supabase: Client` parameter. In the current architecture:

- `polling/runner.py` creates the client and passes it to `claim_one_job`
- `pipeline/runner.py` receives the client (or creates one) and passes it to stages
- The audit functions should receive the same client instance — no new client creation needed

The `JobContext` object (`pipeline/context.py`) currently holds `job`, `token`, `file_bytes`, `extracted_text`, and `result_json`. The Supabase client is NOT in the context — it is passed separately to repo functions. Audit functions should follow the same pattern.

## Acceptance Criteria

- [ ] This document exists as a reference map
- [ ] Every event type in the `JobEventType` enum has at least one integration point identified
- [ ] Every integration point specifies: file path, location hint, event type, and parameters
- [ ] The reference audit batch integration point specifies the mapping from `ResultsV1` fields

## Dependencies

- **Steps 02-06** must be implemented before integration begins
- This step is informational — it produces no code artifacts
