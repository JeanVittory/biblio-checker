# Step 14 — Integration and Entry Point

## Scope

- Update `flow.py` to replace the stub with real graph invocation
- Initialize and clean up lease renewal context
- Define end-to-end integration tests
- Verify the full pipeline works from `start_analysis_flow()` to ResultsV1 output

**Out of scope:** Modifications to `run_langgraph_stage` (it already handles errors correctly). Polling loop changes (none needed).

## Context

The final step wires everything together. The stub `start_analysis_flow()` in `apps/worker/biblio_checker_worker/langgraph/flow.py` is replaced with a real implementation that:

1. Builds the initial graph state from the `AnalysisJob` and `file_bytes`
2. Initializes the lease renewal context
3. Invokes the compiled LangGraph graph
4. Extracts the `results_v1` from the final state
5. Cleans up the lease context
6. Returns the result dict

The existing `run_langgraph_stage` in `pipeline/stages/run_langgraph.py` already:
- Advances the job stage to `LANGGRAPH_RUNNING` before calling `start_analysis_flow()`
- Catches any exception and wraps it as `StageError(transient=True)`
- Advances to `VERIFYING_REFERENCES` after the call
- Stores the result on `ctx.result_json`

No changes are needed to `run_langgraph_stage`.

## Requirements

### 1. Updated `flow.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/flow.py`

```python
from __future__ import annotations

import structlog

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.jobs.models import AnalysisJob
from biblio_checker_worker.langgraph.graph import build_graph
from biblio_checker_worker.langgraph.lease import (
    clear_lease_context,
    init_lease_context,
)

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph")

# Cached compiled graph (stateless — safe to reuse)
_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def start_analysis_flow(
    *,
    job: AnalysisJob,
    file_bytes: bytes,
    supabase=None,
) -> dict:
    """Run the LangGraph analysis pipeline.

    Args:
        job: The claimed analysis job.
        file_bytes: Raw document bytes (PDF or DOCX).
        supabase: Supabase client for lease renewal (optional, for testing).

    Returns:
        A dict conforming to the ResultsV1 schema.
    """
    logger.info(
        "langgraph_flow_starting",
        job_id=str(job.id),
        source_type=job.source_type,
        file_bytes=len(file_bytes),
    )

    # Initialize lease renewal context
    if supabase is not None:
        settings = get_settings()
        init_lease_context(
            supabase=supabase,
            job_id=str(job.id),
            token=job.job_token,
            lease_seconds=settings.job_lease_seconds,
        )

    try:
        # Build initial state
        initial_state = {
            "job_id": str(job.id),
            "source_type": job.source_type,
            "file_bytes": file_bytes,
        }

        # Invoke graph
        graph = _get_graph()
        final_state = graph.invoke(initial_state)

        # Extract result
        result = final_state.get("results_v1", {})

        logger.info(
            "langgraph_flow_complete",
            job_id=str(job.id),
            references_analyzed=len(result.get("references", [])),
        )

        return result

    finally:
        clear_lease_context()
```

### 2. Signature Change

The `start_analysis_flow` signature adds an optional `supabase` parameter:

```python
# Before (stub):
def start_analysis_flow(*, job: AnalysisJob, file_bytes: bytes) -> dict:

# After:
def start_analysis_flow(*, job: AnalysisJob, file_bytes: bytes, supabase=None) -> dict:
```

**Backward compatibility:** The `supabase` parameter is optional with default `None`. The existing `run_langgraph_stage` call:

```python
result = start_analysis_flow(job=ctx.job, file_bytes=ctx.file_bytes)
```

...continues to work without changes. However, `run_langgraph_stage` SHOULD be updated to pass the Supabase client:

```python
result = start_analysis_flow(job=ctx.job, file_bytes=ctx.file_bytes, supabase=supabase)
```

This is a one-line change in `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py:40`.

### 3. Updated `run_langgraph_stage`

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py`

Change line 40 from:
```python
result = start_analysis_flow(job=ctx.job, file_bytes=ctx.file_bytes)
```
to:
```python
result = start_analysis_flow(job=ctx.job, file_bytes=ctx.file_bytes, supabase=supabase)
```

No other changes to this file.

### 4. End-to-End Integration Tests

**File:** `apps/worker/tests/test_langgraph_integration.py`

Create integration tests that verify the full pipeline with mocked external dependencies:

#### Test 1: Happy path — PDF with 3 references
- Mock LLM to return 3 parsed references and 3 normalized references
- Mock all 3 API clients to return matching candidates
- Assert: result is a valid ResultsV1 with 3 references
- Assert: all required fields are present on each reference
- Assert: `summary.totalReferencesAnalyzed == 3`
- Assert: `schemaVersion == "1.0"` and `reportLanguage == "es"`

#### Test 2: Empty document
- Provide empty bytes that extract to empty text
- Assert: result is a valid ResultsV1 with 0 references
- Assert: warning with code `"empty_document"` is present

#### Test 3: API failures
- Mock one API client to raise `httpx.TimeoutException`
- Mock others to return results
- Assert: references are still classified using available evidence
- Assert: warnings include `"source_timeout_partial"`

#### Test 4: All APIs fail for one reference
- Mock all API clients to raise for one specific reference
- Assert: that reference has `classification="processing_error"`
- Assert: other references are classified normally

#### Test 5: LLM returns no references
- Mock LLM parse to return empty list
- Assert: valid ResultsV1 with 0 references

#### Test 6: ResultsV1 validation
- Mock the graph to produce output and validate it against the Pydantic `ResultsV1` model
- Assert: model validation passes

### 5. Logging

The `flow.py` logger covers:
- INFO: `"langgraph_flow_starting"` with job_id, source_type, file_bytes size
- INFO: `"langgraph_flow_complete"` with job_id, references_analyzed count
- ERROR: `"langgraph_flow_failed"` (if exception occurs — logged before re-raise)

## Acceptance Criteria

- [ ] `start_analysis_flow()` replaces the stub with real graph invocation
- [ ] The function accepts optional `supabase` parameter for lease renewal
- [ ] Lease context is initialized before and cleared after graph execution (in `finally` block)
- [ ] The compiled graph is cached at module level for reuse
- [ ] `run_langgraph_stage` passes the Supabase client to `start_analysis_flow`
- [ ] The function returns a dict conforming to ResultsV1 schema
- [ ] Exceptions from the graph propagate to `run_langgraph_stage` (which wraps as StageError)
- [ ] Integration tests cover: happy path, empty document, API failures, LLM failures, processing_error
- [ ] All existing worker tests still pass (`pnpm test:worker`)
- [ ] The worker can be started with `pnpm dev:worker` without errors (given proper env config)

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `supabase=None` (no lease renewal) | Lease context is not initialized. `renew_lease_if_needed()` returns `False` silently. Graph still runs. |
| Graph raises exception during invocation | Exception propagates. `finally` block still clears lease context. `run_langgraph_stage` catches and wraps as StageError. |
| Graph returns state without `results_v1` key | `final_state.get("results_v1", {})` returns empty dict. This would fail Pydantic validation in downstream persistence. |
| Very large document (500+ references) | Graph may take several minutes. Lease renewal keeps the job alive. |

## Files Modified

| File | Change |
|------|--------|
| `apps/worker/biblio_checker_worker/langgraph/flow.py` | Replace stub with real implementation |
| `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py` | Pass `supabase` to `start_analysis_flow` (1 line) |
| `apps/worker/tests/test_langgraph_integration.py` | New file: integration tests |

## Dependencies

- **Depends on:** All previous steps (01–13)
- **Informs:** Nothing — this is the final step
