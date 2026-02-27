# Step 02 — Results JSON Shape (Normative)

## Scope

This spec defines the full JSON object model for `results` (v1): fields, types, nullability, and structural invariants.

## Context

The backend returns `result` on job success. The frontend stores and renders `result`. A stable and strict schema is required for predictable UI and long-term compatibility.

## Requirements

### 1) Root object (ResultsV1)

`result` MUST be an object with the following required fields:

- `schemaVersion`: string, MUST equal `"1.0"`.
- `reportLanguage`: string, MUST equal `"es"`.
- `pipeline`: object, required:
  - `name`: string, required, non-empty.
  - `version`: string, required, non-empty.
- `summary`: object, required (see below).
- `references`: array of `ReferenceResult`, required (may be empty).
- `warnings`: array of `Warning`, required (may be empty).

### 2) `summary`

`summary` MUST be an object with required fields:

- `totalReferencesDetected`: integer, `>= 0`.
- `totalReferencesAnalyzed`: integer, `>= 0`.
- `countsByClassification`: object, required:
  - MUST include all keys from `classification` (exactly once each).
  - values MUST be integers `>= 0`.

### 3) `references[]` items (`ReferenceResult`)

Each reference result MUST be an object with required fields:

- `referenceId`: string, required, non-empty; MUST be unique within this report.
- `rawText`: string, required, non-empty.
- `normalized`: object, required:
  - `title`: string or `null`
  - `authors`: array of strings (may be empty)
  - `year`: integer or `null`
  - `venue`: string or `null`
  - `doi`: string or `null`
  - `arxivId`: string or `null`
- `classification`: `classification` enum (closed; defined in Step 03).
- `confidenceScore`: number or `null` (range rules defined in Step 04).
- `confidenceBand`: `confidenceBand` enum or `null` (compatibility rules defined in Step 04).
- `manualReviewRequired`: boolean (forced by classification; defined in Step 04).
- `reasonCode`: `reasonCode` enum (closed; defined in Step 03).
- `decisionReason`: string, required, non-empty, Spanish.
- `evidence`: array of `EvidenceItem`, required (may be empty).

### 4) `evidence[]` items (`EvidenceItem`)

Each evidence item MUST be an object with required fields:

- `source`: string, required, non-empty.
- `matchType`: string, required, non-empty.
- `score`: number, required, MUST be in `[0.0, 1.0]`.
- `matchedRecord`: object, required:
  - `externalId`: string, required, non-empty.
  - `title`: string or `null`
  - `year`: integer or `null`
  - `doi`: string or `null`
  - `url`: string or `null`

Note: `source` and `matchType` are intentionally NOT closed enums in v1 to avoid premature lock-in; only the global enums listed in Step 03 are closed in this phase.

### 5) `warnings[]` items (`Warning`)

Each warning MUST be an object with required fields:

- `code`: string, required, non-empty (stable identifier).
- `message`: string, required, non-empty, Spanish.
- `referenceId`: string or `null` (when warning applies to a specific reference).
- `details`: object or `null` (free-form diagnostic payload).

## Normative invariants

1. `references.length` MUST equal `summary.totalReferencesAnalyzed`.
2. `sum(summary.countsByClassification[*])` MUST equal `summary.totalReferencesAnalyzed`.
3. `summary.totalReferencesAnalyzed` MUST be `<= summary.totalReferencesDetected`.
4. `referenceId` values MUST be unique within `references[]`.

## Acceptance Criteria

- All fields above are specified as required vs optional and their types are explicit.
- All nullability is explicit (including `confidenceScore` / `confidenceBand`).
- The invariants are stated as MUST-level requirements.

## Edge Cases

- `references` can be empty (e.g., document had no detectable references).
- `authors` may be empty even when other normalized fields exist.
- `warnings.details` may be `null` when no extra diagnostics are available.

## Integration Points

- Backend: stores this object as JSON in `analysis_jobs.results` for succeeded jobs.
- API: returns this object as `result` in job status response for succeeded jobs.
- Frontend: parses and renders this object for succeeded jobs.

## Dependencies

- Step 03 (Enums) for `classification`, `confidenceBand`, `reasonCode`.
- Step 04 (Matrices + nullability) for compatibility constraints.

