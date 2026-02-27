# Step 09 — Frontend Integration Requirements (Types + Degraded Rendering)

## Scope

This spec defines how the frontend integrates with Results Contract v1:
- Strong typing for `result`
- Runtime validation / safe parsing
- Rendering expectations and graceful degradation

No UI redesign is required by this spec; it is limited to correctness and stability.

## Context

The frontend currently stores job entries locally and renders `job.result` as JSON in the “Recent Analyses” UI. Today, `result` is treated as `unknown | null`. With a stable schema, the frontend can render more reliably and detect unsupported/legacy payloads.

## Requirements

### 1) Type definition

- The frontend MUST define a TypeScript type for Results Contract v1 (e.g., `ResultsV1`).
- The type MUST match the contract exactly (Steps 02–05), including:
  - closed enums
  - nullability (`confidenceScore: number|null`, `confidenceBand: ConfidenceBand|null`)
  - required arrays (`references`, `warnings`, `evidence`)

### 2) Runtime validation (required)

- Because `result` is received over the network, the frontend MUST validate at runtime before treating it as `ResultsV1`.
- The validation MUST verify:
  - `schemaVersion === "1.0"`
  - enum membership and compatibility matrices

- Implementation requirement:
  - The frontend MUST implement this runtime validation using a Zod schema located under `apps/frontend/lib/validation/` and MUST parse `result` into `ResultsV1` via that schema.

### 3) Storage model

Implementation MUST choose one storage approach and apply it consistently:

- Store the parsed `ResultsV1` in localStorage when validation succeeds.
- Store `null` (and optionally a warning UI state) when validation fails.

This avoids persisting “unknown shapes” that could break future renders.

### 4) Degraded rendering for unsupported schemas

- If `result` is present but does not validate as `schemaVersion="1.0"`, the UI MUST:
  - display a clear “unsupported or invalid results format” message, and
  - allow the user to see the raw JSON payload (best-effort) for debugging.

## Acceptance Criteria

- The UI never crashes due to unexpected `result` shapes.
- Succeeded jobs with valid Results v1 display the report.
- Succeeded jobs with invalid/unsupported results display the degraded view.

## Dependencies

- Steps 02–05 define the shape and constraints used by the frontend validator.
- Step 10 provides canonical examples for parsing/validation.
