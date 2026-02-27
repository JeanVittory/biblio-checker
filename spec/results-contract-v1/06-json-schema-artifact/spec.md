# Step 06 — JSON Schema Artifact Requirements

## Scope

This spec defines the requirements for a canonical JSON Schema artifact that validates Results Contract v1.

This file defines **what** the JSON Schema must enforce, not the exact JSON Schema implementation.

## Required artifact

An implementation MUST add the following artifact to the repo:

- `spec/results-contract-v1/artifacts/results-v1.schema.json`

## Requirements (normative)

### 1) Strictness

- The schema MUST enforce `additionalProperties: false` for every object in the contract (root, summary, normalized, reference result, evidence item, matched record, warning).

### 2) Closed enums

- The schema MUST enforce closed enums for:
  - `classification`
  - `confidenceBand`
  - `reasonCode`

### 3) Constants

- The schema MUST enforce:
  - `schemaVersion` is exactly `"1.0"`
  - `reportLanguage` is exactly `"es"`

### 4) Invariants

The schema MUST enforce (at minimum):

- Required fields presence (as defined in Step 02).
- Number bounds for `confidenceScore` and evidence `score`.
- `countsByClassification` has exactly all keys in `classification` with integer `>= 0`.

Note: cross-field invariants like “sum of counts equals totalReferencesAnalyzed” cannot always be expressed in pure JSON Schema depending on draft/version; this suite requires:
- enforce via backend validation in addition to schema validation (see Step 07).

Normative split for v1:
- JSON Schema MUST enforce all per-field constraints and all matrix/nullability rules (Steps 02–04).
- Backend runtime validation MUST enforce the computed invariants listed in Step 02 and Step 11, specifically:
  - `references.length == summary.totalReferencesAnalyzed`
  - `sum(countsByClassification.*) == summary.totalReferencesAnalyzed`
  - `summary.totalReferencesAnalyzed <= summary.totalReferencesDetected`
  - `referenceId` values MUST be unique within `references[]`

### 5) Matrix enforcement via `oneOf`

The schema MUST enforce:

- The `classification × confidenceBand` compatibility matrix (Step 04)
- Forced `manualReviewRequired` values (Step 04)
- Forced nullability for `processing_error` (`confidenceScore=null` and `confidenceBand=null`)

This MUST be implemented using `oneOf` branches keyed by `classification` (or an equivalent schema mechanism that is equally strict).

## Acceptance Criteria

- All valid examples in Step 10 validate successfully.
- All invalid examples in Step 10 are rejected.

## Dependencies

- Steps 02–05 define the rules the schema must encode.
