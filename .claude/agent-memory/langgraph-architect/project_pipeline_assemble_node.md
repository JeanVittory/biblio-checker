---
name: pipeline-assemble-node
description: Implementation details for the assemble_report LangGraph node (Step 11)
type: project
---

File: `apps/worker/biblio_checker_worker/langgraph/nodes/assemble.py`

## Key design decisions

- Reads from `state["classified_references"]` (NOT `state["verified_references"]`) — this was a deliberate spec change to avoid reducer conflicts
- Calls `renew_lease_if_needed()` BEFORE Pydantic validation
- `countsByClassification` is built by iterating the `Classification` enum to ensure all keys are always present (zero-valued when absent)
- `ValidationError` from Pydantic propagates uncaught — caller (`run_langgraph_stage`) wraps it as `StageError(transient=True)`
- Returns `{"results_v1": validated.model_dump()}` — a plain dict, not the Pydantic model

## Imports at the time of implementation

- `biblio_checker_worker.langgraph.lease` — Step 12, NOT YET IMPLEMENTED; tests stub this module
- `biblio_checker_worker.langgraph.schemas` — Step 01, already implemented (copy of backend results.py)
- `biblio_checker_worker.core.config.get_settings` — provides `pipeline_name` and `pipeline_version`

## Test file

`apps/worker/tests/test_assemble_report.py`

- Stubs `biblio_checker_worker.langgraph.lease` via `sys.modules.setdefault` before node import
- Mocks `get_settings` via `unittest.mock.patch` in each test
- Covers: normal assembly (mixed classifications), zero references, processing_error pass-through, Pydantic validation failure propagation, lease renewal called once, warnings forwarded, pipeline metadata from settings, detected > analyzed is valid
