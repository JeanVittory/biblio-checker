# Step 11 — Acceptance Criteria and Validation Plan

## Scope

This spec defines the verification checklist for confirming that Results Contract v1 is correctly implemented across:
- JSON Schema artifact validation
- Backend enforcement
- Frontend safe parsing and rendering

No test code is defined here; only the scenarios and expected outcomes.

## Validation requirements

### 1) JSON Schema validation

Given the JSON Schema artifact `spec/results-contract-v1/artifacts/results-v1.schema.json`:

- All valid examples in Step 10 MUST validate successfully.
- All invalid examples in Step 10 MUST be rejected.

### 2) Backend validation behavior

- When job `status != "succeeded"`:
  - `result` MUST be `null`.
- When job `status == "succeeded"` and a `result` payload exists:
  - The backend MUST validate the payload as Results Contract v1 before returning it.
  - If validation fails, the backend MUST return `result=null` (and MUST NOT crash).

### 3) Frontend parsing/rendering behavior

- For succeeded jobs with valid Results v1:
  - Frontend MUST parse and display the report without runtime errors.
- For succeeded jobs with invalid/unsupported results:
  - Frontend MUST show a degraded view:
    - “Unsupported or invalid results format”
    - Raw JSON (best-effort) for debugging
  - Frontend MUST NOT crash.

## Additional correctness checks (report invariants)

For every valid report:

- `references.length == summary.totalReferencesAnalyzed`
- `sum(countsByClassification.*) == summary.totalReferencesAnalyzed`
- `summary.totalReferencesAnalyzed <= summary.totalReferencesDetected`
- `referenceId` unique within the report

## Definition of Done (implementation)

Implementation is considered complete when:

- The JSON Schema artifact exists and rejects all invalid combinations from Step 10.
- Backend enforces Results v1 for succeeded job results and degrades safely on invalid stored payloads.
- Frontend safely parses Results v1 and degrades safely on unsupported payloads.

## Dependencies

- Step 06 (JSON Schema artifact requirements)
- Step 07 (backend enforcement requirements)
- Step 09 (frontend integration requirements)
- Step 10 (examples and fixtures)

