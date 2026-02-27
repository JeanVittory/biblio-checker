# Results Contract v1 — Spec Suite (SDD)

This folder defines the **normative** contract for the `results` payload produced by the analysis system and returned to the UI as `result` in job status responses.

## What this suite defines

- A **strict** JSON shape for `results` (`schemaVersion: "1.0"`).
- Closed enums:
  - `classification`
  - `confidenceBand`
  - `reasonCode`
- Normative **compatibility matrices** and **nullability rules** that prevent illogical combinations (e.g., `verified + very_low`).
- Requirements for a JSON Schema artifact and canonical examples/fixtures.
- Integration requirements (backend persistence/validation + frontend typing/rendering) **without** specifying analysis logic.

## What this suite does NOT define

- How references are extracted from PDFs/DOCX.
- How matches are found in OpenAlex/SciELO/arXiv (or any other source).
- Ranking/scoring algorithms, thresholds, or orchestration flows.
- Worker/job lifecycle semantics beyond “`result` exists only when job status is `succeeded`”.

## System context (where it appears)

- Backend persists the success payload in a DB column commonly named `results`.
- The job-status API returns that payload as `result` when job `status="succeeded"`.
- Frontend renders job status and can display `result` for completed jobs.

## Reading order

Start at `INDEX.md`.

