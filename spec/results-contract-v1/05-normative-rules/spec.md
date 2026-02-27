# Step 05 — Normative Rules (Minimum, Contract-Level)

## Scope

This spec defines the **minimum** normative rules required to make the contract operationally meaningful without describing implementation flows.

These rules are written as obligations on the output payload (what must be true about the report), not as a step-by-step algorithm.

## Requirements

### 1) `decisionReason` is mandatory and Spanish

- Every `ReferenceResult` MUST include `decisionReason` as a non-empty string in Spanish.
- The text MUST explain why the reference was classified as it was, referencing the available evidence at a high level.

### 2) `reasonCode` is the primary reason

- `reasonCode` MUST represent the single primary reason for the classification decision.
- Secondary considerations MAY be expressed in `decisionReason` and/or `warnings[]` but MUST NOT require additional structured fields in v1.

### 3) Evidence list rules

- `evidence` MUST be present and MUST be an array (may be empty).
- If `evidence` is non-empty, each item MUST include `score` in `[0.0, 1.0]` and `matchedRecord.externalId`.

### 4) Summary consistency rules

The report MUST satisfy:

- `summary.totalReferencesAnalyzed == references.length`
- `summary.countsByClassification` equals the computed counts over `references[].classification`
- `summary.totalReferencesAnalyzed <= summary.totalReferencesDetected`

### 5) Versioning and language

- `schemaVersion` MUST be `"1.0"` in v1.
- `reportLanguage` MUST be `"es"` in v1.
- `pipeline.version` MUST be present to allow pipeline evolution without changing the schema.

## Acceptance Criteria

- A consumer can reliably display a report without guessing missing fields.
- A validator can reject payloads that violate the matrix rules (Step 04) and the invariants (Step 02/05).

## Dependencies

- Steps 02–04 define the shape and compatibility constraints referenced here.

