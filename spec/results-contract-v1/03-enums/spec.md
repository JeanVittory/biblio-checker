# Step 03 — Closed Enums (Normative)

## Scope

This spec closes the enums required by Results Contract v1.

## Requirements

### 1) `classification` (closed)

Allowed values (exact strings):

- `verified`
- `likely_verified`
- `ambiguous`
- `not_found`
- `suspicious`
- `processing_error`

### 2) `confidenceBand` (closed)

Allowed values (exact strings):

- `very_high` — `[0.90, 1.00]` (inclusive on both ends)
- `high`      — `[0.75, 0.90)` (inclusive lower, exclusive upper)
- `medium`    — `[0.50, 0.75)` (inclusive lower, exclusive upper)
- `low`       — `[0.25, 0.50)` (inclusive lower, exclusive upper)
- `very_low`  — `[0.00, 0.25)` (inclusive lower, exclusive upper)

The numeric ranges above are normative for mapping `confidenceScore` → `confidenceBand` when `confidenceScore` is present (the mapping mechanics are defined in Step 05 as contract-level expectations).

**Boundary rule:** ranges use half-open intervals `[lower, upper)` except for `very_high` which is fully closed `[0.90, 1.00]`. There are no gaps. Scores MUST be rounded to at most 4 decimal places before band assignment.

### 3) `reasonCode` (closed)

Allowed values (exact strings):

- `exact_doi_match`
- `exact_identifier_match`
- `strong_metadata_match`
- `multiple_plausible_candidates`
- `insufficient_metadata`
- `no_match_any_source`
- `strong_doi_conflict`
- `cross_source_metadata_conflict`
- `source_timeout_partial`
- `reference_processing_failure`

## Acceptance Criteria

- Any `results v1` payload containing enum values outside the allowed lists MUST be rejected by schema validation.
- The same enum values MUST be used consistently across backend and frontend types.

## Dependencies

- Step 02 (JSON shape) references these enums.

