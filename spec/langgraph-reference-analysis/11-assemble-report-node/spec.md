# Step 11 — Assemble Report Node

## Scope

- Implement the `assemble_report` graph node that builds and validates the final ResultsV1 payload
- Compute `summary.countsByClassification`
- Validate the output against the Pydantic `ResultsV1` model
- Handle pre-classified references (processing_error from Step 10)

**Out of scope:** Classification logic (Step 09). Evidence collection (Step 10). Schema definition (Step 01).

## Context

This is the final node in the graph. It receives all classified references (from `classify_results`) and any warnings accumulated during the pipeline. It assembles the complete `ResultsV1` dict, validates it against the Pydantic model, and sets it on the state for the pipeline to persist.

## Requirements

### 1. Node Function — `nodes/assemble.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/assemble.py`

```python
def assemble_report(state: GraphState) -> dict:
```

**Behavior:**

1. Call `renew_lease_if_needed()` before Pydantic validation (as specified in Step 12, Section 4):
   ```python
   from biblio_checker_worker.langgraph.lease import renew_lease_if_needed
   renew_lease_if_needed()
   ```
2. Read `state["classified_references"]` (written by `classify_results`), `state["total_references_detected"]`, and `state["warnings"]`
3. Build each `ReferenceResult` entry from the classified references
4. Compute `countsByClassification`:
   ```python
   counts = {c.value: 0 for c in Classification}
   for ref in references:
       counts[ref["classification"]] += 1
   ```
5. Build the full payload:
   ```python
   payload = {
       "schemaVersion": "1.0",
       "reportLanguage": "es",
       "pipeline": {
           "name": settings.pipeline_name,
           "version": settings.pipeline_version,
       },
       "summary": {
           "totalReferencesDetected": total_references_detected,
           "totalReferencesAnalyzed": len(references),
           "countsByClassification": counts,
       },
       "references": references,
       "warnings": warnings,
   }
   ```
6. Validate against Pydantic:
   ```python
   from biblio_checker_worker.langgraph.schemas import ResultsV1
   validated = ResultsV1(**payload)
   ```
7. If validation succeeds, return `{"results_v1": validated.model_dump()}`
8. If validation fails, raise the `ValidationError` — it will propagate as a transient `StageError` via `run_langgraph_stage`

### 2. Reference Assembly

For each reference in `verified_references`, build the `ReferenceResult` structure:

```python
{
    "referenceId": ref["referenceId"],
    "rawText": ref["rawText"],
    "normalized": ref["normalized"],
    "classification": ref["classification"],
    "confidenceScore": ref["confidenceScore"],
    "confidenceBand": ref["confidenceBand"],
    "manualReviewRequired": ref["manualReviewRequired"],
    "reasonCode": ref["reasonCode"],
    "decisionReason": ref["decisionReason"],
    "evidence": ref["evidence"],
}
```

References that were pre-classified as `processing_error` by Step 10 already have all classification fields set. These pass through unchanged.

### 3. Invariant Checks

The Pydantic `ResultsV1` model (from `schemas.py`) enforces these invariants:
- `references.length == summary.totalReferencesAnalyzed`
- `sum(countsByClassification) == totalReferencesAnalyzed`
- `totalReferencesAnalyzed <= totalReferencesDetected`
- All `referenceId` values are unique
- Each reference's classification/confidenceBand/manualReviewRequired combination is valid per the compatibility matrix

If any invariant is violated, the Pydantic `ValidationError` MUST propagate (not be swallowed).

### 4. Handling Edge Cases in Assembly

**Zero references:**
- Valid ResultsV1 with `totalReferencesAnalyzed=0`, empty `references[]`, all counts zero

**totalReferencesDetected > totalReferencesAnalyzed:**
- Can happen if some references failed normalization (count mismatch from Step 06)
- `totalReferencesDetected` comes from `parse_references` (how many the LLM found)
- `totalReferencesAnalyzed` is `len(verified_references)` (how many were actually processed)

### 5. Logging

Logger name: `"biblio_checker_worker.langgraph.nodes.assemble"`

- INFO: `"assemble_starting"` with `references_count`, `warnings_count`
- INFO: `"assemble_validation_passed"` with summary counts
- ERROR: `"assemble_validation_failed"` with validation error details

## Acceptance Criteria

- [ ] Node function has signature `assemble_report(state: GraphState) -> dict`
- [ ] Returns `{"results_v1": dict}` with a Pydantic-validated ResultsV1 payload
- [ ] Calls `renew_lease_if_needed()` before Pydantic validation
- [ ] Reads from `state["classified_references"]` (not `state["verified_references"]`)
- [ ] `schemaVersion` is `"1.0"` and `reportLanguage` is `"es"`
- [ ] `pipeline.name` and `pipeline.version` come from `settings.pipeline_name` and `settings.pipeline_version`
- [ ] `summary.countsByClassification` is computed correctly from reference classifications
- [ ] `summary.totalReferencesAnalyzed == len(references)`
- [ ] `summary.totalReferencesDetected` comes from graph state
- [ ] All ResultsV1 invariants are enforced by Pydantic validation
- [ ] Pydantic `ValidationError` propagates as an exception (not swallowed)
- [ ] Pre-classified `processing_error` references pass through unchanged
- [ ] Zero references produces a valid (empty) ResultsV1
- [ ] Unit tests cover: normal assembly, zero references, processing_error mixed in, invariant violation

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| All references are `verified` | Valid ResultsV1 with all counts in `verified` |
| Mix of classifications | Counts computed correctly per classification |
| `processing_error` references have `confidenceScore=null` | Pydantic accepts this per the compatibility matrix |
| Duplicate `referenceId` (bug in upstream) | Pydantic validation fails → exception propagates |
| `totalReferencesDetected < totalReferencesAnalyzed` (bug) | Pydantic validation fails → exception propagates |

## Dependencies

- **Depends on:** Step 01 (schemas: `ResultsV1`), Step 09 (classified references), Step 02 (GraphState)
- **Informs:** Step 14 (flow.py returns `results_v1` from the graph)
