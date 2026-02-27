# Step 07 — Backend Integration Requirements (Contract Enforcement)

## Scope

This spec defines how the backend must integrate and enforce the Results Contract v1, without specifying any analysis logic.

## Context

The backend returns job status and includes `result` only when a job is `succeeded`. Today, the job status response model allows `result: Any | None`. This spec requires `result` to be a validated Results Contract v1 object when present.

## Requirements

### 1) Validation boundary

- If a job has `status="succeeded"` and includes a non-null `result`, the backend MUST ensure that `result` conforms to Results Contract v1 before returning it.

This can be achieved via:
- Pydantic model validation (preferred for runtime safety), and/or
- JSON Schema validation using `results-v1.schema.json`.

### 2) Backward compatibility

- If older jobs contain legacy/non-conforming results, the backend MUST NOT crash.
- The backend MUST implement the following behavior:
  - If the stored payload validates as Results Contract v1, return it as `result`.
  - Otherwise, return `result=null` and MUST NOT change the job status.

### 3) Persistence contract for succeeded jobs

- When the system marks a job as `succeeded`, the stored `analysis_jobs.results` MUST be a JSON object that validates as Results Contract v1.

### 4) Security and sensitive data

- The backend MUST ensure `result` does not contain job tokens, storage signed URLs, or any secret credentials.

## Acceptance Criteria

- A succeeded job returns a `result` that validates as Results Contract v1.
- A non-succeeded job returns `result=null`.
- Invalid stored payloads do not crash the endpoint.

## Integration Points

- `GET /api/analysis/status` response model and serialization.
- Persistence layer writing into `analysis_jobs.results`.

## Dependencies

- Step 06 JSON Schema artifact requirements.
- Step 10 example payloads for integration testing.
