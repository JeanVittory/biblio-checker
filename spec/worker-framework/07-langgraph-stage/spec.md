# Step 07 — LangGraph Stage (Stub)

## Scope

- Define the LangGraph wrapper stage that invokes the analysis flow
- For this spec, the stage is a functional stub that simulates a successful flow
- Define the stage transition semantics: `langgraph_running` and `verifying_references`
- Define the interface contract that the real LangGraph implementation must satisfy

**Out of scope:** The actual LangGraph graph implementation (reference extraction, API calls to OpenAlex/SciELO/arXiv). That will be a separate spec suite.

## Context

The LangGraph stage is the core of the analysis pipeline. It covers two logical phases:

1. **Orchestration (`langgraph_running`):** The LangGraph graph initializes, extracts bibliographic references from the document text, and builds a verification plan.
2. **API verification (`verifying_references`):** The graph executes calls to external academic APIs (OpenAlex, SciELO, arXiv) to verify each reference, then classifies and assembles the final result.

For the worker framework implementation, this stage is a stub: it advances through both stages and produces a minimal valid result dict. This allows the full pipeline to be tested end-to-end before the real analysis logic is built.

## Requirements

### 1. Module Location

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py`

**Public function:** `run_langgraph_stage(*, supabase: Client, ctx: JobContext) -> None`

### 2. Processing Steps

**Step 2.1 — Advance to `langgraph_running`**

Call `repo.update_stage(supabase, job_id=ctx.job.id, stage=JobStage.LANGGRAPH_RUNNING, token=ctx.job.job_token)`

**Step 2.2 — Invoke the analysis flow**

Call the flow function from `biblio_checker_worker.langgraph.flow`:
```
result = start_analysis_flow(job=ctx.job, file_bytes=ctx.file_bytes)
```

The flow function signature (existing stub, to be modified):
```
def start_analysis_flow(*, job: AnalysisJob, file_bytes: bytes) -> dict
```

Currently this is a stub. The stub MUST return a minimal dict (even if empty `{}`) to allow the pipeline to proceed.

If the flow raises any exception, catch it and re-raise as:
`StageError(code="langgraph_flow_failed", detail=<exception message>, transient=True)`

LangGraph failures are transient by default because they could be caused by external API timeouts, rate limits, or temporary service outages.

**Step 2.3 — Advance to `verifying_references`**

Call `repo.update_stage(supabase, job_id=ctx.job.id, stage=JobStage.VERIFYING_REFERENCES, token=ctx.job.job_token)`

Note: In the real implementation, the graph itself will trigger this transition internally when it begins API calls. For the stub, the stage wrapper handles both transitions.

**Step 2.4 — Populate context**

Set `ctx.result_json = result`

### 3. Flow Function Contract

The `start_analysis_flow` function in `langgraph/flow.py` must be updated to match this contract:

**Current signature:** `def start_analysis_flow(*, job: dict[str, Any]) -> None`

**New signature:** `def start_analysis_flow(*, job: AnalysisJob, file_bytes: bytes) -> dict`

Changes:
- `job` parameter type changes from `dict[str, Any]` to `AnalysisJob`
- New `file_bytes` parameter for the downloaded document bytes
- Returns a `dict` (the result payload) instead of `None`

**Stub implementation:** Log the invocation and return `{}` (empty dict). The real implementation will return a dict conforming to the ResultsV1 schema.

### 4. Error Classification

| Error condition | Error type | Code | Transient |
|----------------|------------|------|-----------|
| Flow function raises any exception | `StageError` | `langgraph_flow_failed` | Yes |
| `update_stage` DB error | `JobRepoError` | (from repo) | N/A (handled by runner) |

All LangGraph failures are treated as transient for v1. When the real graph is implemented, specific error types may be classified as terminal (e.g., if the document contains no extractable text).

### 5. Future Transition to Real Implementation

When the real LangGraph graph is built:
- The stub in `langgraph/flow.py` will be replaced with actual graph construction and invocation
- The `verifying_references` stage transition may move inside the graph (via a callback or hook) for more accurate progress reporting
- The return value will be a full ResultsV1-conforming dict
- New terminal error conditions may be added (e.g., `no_references_found`)

The stage wrapper in `run_langgraph.py` should require minimal changes — primarily the error classification may expand.

## Acceptance Criteria

- The stage advances to `langgraph_running` before invoking the flow
- The stage advances to `verifying_references` after the flow completes
- The flow function receives `job` (as `AnalysisJob`) and `file_bytes`
- The flow function returns a `dict` (the result payload)
- The stub flow returns `{}` and logs the invocation
- Any exception from the flow is wrapped in `StageError(code="langgraph_flow_failed", transient=True)`
- The `token` guard is passed to all `update_stage` calls
- `ctx.result_json` is set to the flow's return value

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Stub flow returns `{}` | Pipeline proceeds. Persist stage will attempt to write `{}` as `result_json`. |
| Flow raises `KeyboardInterrupt` | NOT caught by the stage (it only catches `Exception`). Propagates up, killing the worker. Lease expires naturally. |
| Flow takes longer than the lease TTL (5 minutes) | The lease expires while the flow is running. Another worker may claim the job. When the original worker finishes and calls `update_stage`, the token guard will fail (zero rows updated), raising `JobRepoError`. The pipeline runner handles this. |
| `update_stage` for `langgraph_running` fails (lease expired before flow starts) | `JobRepoError` propagates to runner. Runner attempts `mark_failed`. This is correct: the worker lost the lease. |

## Integration Points

- **Step 04:** Calls `repo.update_stage` twice (langgraph_running, verifying_references)
- **Step 05:** Follows the stage function contract
- **Step 06:** Reads `ctx.file_bytes` populated by the extract stage
- **Step 08:** The next stage (persist) reads `ctx.result_json`
- **`langgraph/flow.py`:** The flow function signature is updated

## Dependencies

- **Depends on:** Step 04 (repo.update_stage), Step 05 (stage contract), Step 06 (provides file_bytes)
- **Informs:** Step 08 (provides result_json for persistence)
