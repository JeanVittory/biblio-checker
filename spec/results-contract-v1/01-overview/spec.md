# Step 01 — Results Contract Overview

## Scope

This spec defines the scope, intent, and invariants of the **Results Contract v1** (“results v1”).

**In scope**
- Normative JSON contract for `results` / `result` (schema v1).
- Closed enums (`classification`, `confidenceBand`, `reasonCode`).
- Contract-level validation requirements (matrices, nullability, required fields).

**Out of scope**
- Any implementation code.
- Any orchestration flow (worker pipeline, LangGraph, etc.).
- How evidence is collected from external sources.
- Any scoring or matching algorithm design.

## Context

The system persists the analysis success payload in a database column commonly called `results`. When clients poll job status, the backend returns this payload as `result` **only when** the job has `status="succeeded"`.

This contract must support:
- Evidence-based verification (traceability).
- Clear user-facing rationale (Spanish MVP).
- Predictable rendering in the frontend (stable shape).

## Requirements

1. The results payload MUST be a JSON object conforming to Results Contract v1 when present.
2. The results payload MUST be versioned using `schemaVersion`.
3. The contract MUST be strict: unknown properties MUST be rejected by the canonical JSON Schema artifact for v1.
4. User-facing explanatory text inside the payload MUST be in Spanish (`reportLanguage="es"` in v1).
5. The contract MUST NOT introduce fields whose semantics imply “citation generation” or “automatic correction”.

## Acceptance Criteria

- A developer can implement a JSON Schema + backend/frontend types without making additional field-name decisions.
- The contract is explicit about required vs optional fields and about nullability.
- The contract is explicit about when `result` is present or absent in job status responses.

## Edge Cases

- Jobs not in `succeeded` status: `result` is `null` (or absent) and this suite does not change that API behavior.
- Backward compatibility: older jobs may have `results` missing or non-conforming; consumers must degrade gracefully (defined later).

## Integration Points

- Backend: job-status response model includes `result` on success.
- Frontend: “Recent Analyses” UI renders `result` for succeeded jobs.
- Worker (future): persists `results` into the job row.

## Dependencies

- None (suite entrypoint).

