# Step 04 — Compatibility Matrices + Nullability (Normative)

## Scope

This spec prevents illogical outputs by defining:
- Compatibility matrix: `classification × confidenceBand`
- Forced rules for `manualReviewRequired`
- Forced nullability rules for `processing_error`

## Requirements

### 1) `confidenceScore` type and bounds

- `confidenceScore` MUST be `null` or a number in `[0.0, 1.0]`.

### 2) `classification × confidenceBand` allowed matrix

For each `ReferenceResult`, the pair (`classification`, `confidenceBand`) MUST satisfy:

- `verified` → `confidenceBand ∈ { high, very_high }`
- `likely_verified` → `confidenceBand ∈ { medium, high }`
- `ambiguous` → `confidenceBand ∈ { low, medium }`
- `not_found` → `confidenceBand ∈ { very_low, low }`
- `suspicious` → `confidenceBand ∈ { medium, high, very_high }`
- `processing_error` → `confidenceBand = null`

### 3) `processing_error` is unscored (forced nullability)

If `classification = "processing_error"` then:

- `confidenceBand` MUST be `null`
- `confidenceScore` MUST be `null`
- `manualReviewRequired` MUST be `true`

Rationale: processing errors do not have sufficient evidence to assign a meaningful confidence score/band.

### 4) `manualReviewRequired` forced by `classification`

The value of `manualReviewRequired` MUST be:

- `true` for `classification ∈ { ambiguous, not_found, suspicious, processing_error }`
- `false` for `classification ∈ { verified, likely_verified }`

### 5) Explicitly forbidden combinations (examples)

These examples MUST be rejected by schema validation:

- `classification="verified"` + `confidenceBand="very_low"` (forbidden)
- `classification="not_found"` + `confidenceBand="very_high"` (forbidden)
- `classification="processing_error"` + `confidenceBand="low"` (forbidden; must be null)
- `classification="ambiguous"` + `manualReviewRequired=false` (forbidden; must be true)

## Acceptance Criteria

- The matrix is complete (covers all `classification` values).
- The forced rules are strict enough to eliminate illogical states.

## Dependencies

- Step 03 defines the enums used by this matrix.

