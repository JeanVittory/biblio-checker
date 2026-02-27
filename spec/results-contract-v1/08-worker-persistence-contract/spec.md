# Step 08 — Worker Persistence Contract (Results v1)

## Scope

This spec defines the worker-side persistence expectations for writing `analysis_jobs.results`, without defining any processing flow.

## Context

The worker (future) will compute the final report and persist it. The frontend depends on this persisted shape to render results.

## Requirements

### 1) Persisted payload MUST be Results v1

- When the worker (or any backend component) writes a final success payload into `analysis_jobs.results`, it MUST write a JSON object that validates as Results Contract v1 (`schemaVersion="1.0"`).

### 2) Reference-level failures

- Failures that affect only a single reference MUST be representable within the report:
  - Use `classification="processing_error"` for the affected `ReferenceResult`.
  - Enforce `confidenceScore=null` and `confidenceBand=null` for that reference (Step 04).

This spec does not require the overall job status to be `failed` when some references are `processing_error`. The lifecycle decision is out of scope.

### 3) Partial source outages

- If a source times out but other evidence exists, the worker MAY still produce a report, and:
  - the relevant reference(s) SHOULD include `reasonCode="source_timeout_partial"` and/or
  - a `warnings[]` entry SHOULD be added at report level.

This spec does not define how to detect timeouts; it only defines how to represent them.

## Acceptance Criteria

- Any persisted `results` payload for succeeded jobs validates as Results Contract v1.
- `processing_error` entries have null score and null band.

## Dependencies

- Steps 02–06 define the payload and validation rules.

