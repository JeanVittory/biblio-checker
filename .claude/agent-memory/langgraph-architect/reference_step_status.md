---
name: step-implementation-status
description: Which spec steps from spec/langgraph-reference-analysis/ have been implemented and where
type: reference
---

Spec lives at `spec/langgraph-reference-analysis/`.

| Step | Title | Status | Key file(s) |
|------|-------|--------|-------------|
| 01 | Overview and Dependencies | Done (parallel agent) | `langgraph/schemas.py`, `core/config.py` (updated), `nodes/__init__.py`, `clients/__init__.py`, `prompts/__init__.py` |
| 02 | Graph State and Topology | Done | `langgraph/state.py` |
| 03 | Text Extraction Node | Partial (extract_text.py exists) | `langgraph/nodes/extract_text.py` |
| 04 | LLM Client Factory | Done | `langgraph/clients/llm.py`, `tests/test_llm_client.py` |
| 05 | Parse References Node | Done | `langgraph/nodes/parse_references.py`, `langgraph/prompts/parse_references.py`, `tests/test_parse_references.py` |
| 06 | Normalize References Node | Done | `langgraph/nodes/normalize.py`, `langgraph/prompts/normalize.py`, `tests/test_normalize_references.py` |
| 07 | API Clients | Done (parallel agent) | `langgraph/clients/openalex.py`, `langgraph/clients/scielo.py`, `langgraph/clients/arxiv.py` |
| 08 | Scoring | Done (parallel agent) | `langgraph/scoring.py`, `tests/test_scoring.py` |
| 09 | Classification Engine | Done | `langgraph/classification.py`, `langgraph/nodes/classify.py`, `tests/test_classification.py` |
| 10 | Verify Reference Node | Done | `langgraph/nodes/verify.py`, `tests/test_verify_node.py` |
| 11 | Assemble Report Node | Done | `langgraph/nodes/assemble.py`, `tests/test_assemble_report.py` |
| 12 | Lease Renewal | Done | `langgraph/lease.py`, `tests/test_lease_renewal.py` |
| 13 | Graph Construction and Wiring | Done | `langgraph/graph.py` |
| 14 | Integration and Entry Point | Done | `langgraph/flow.py`, `pipeline/stages/run_langgraph.py` (1-line change), `tests/test_langgraph_integration.py` |

## Schema note
`ReasonCode.SINGLE_MODERATE_MATCH = "single_moderate_match"` was added to both
`apps/worker/biblio_checker_worker/langgraph/schemas.py` and
`apps/backend/app/schemas/results.py` during Step 09 implementation (the Step 01
agent omitted it but the spec requires it for Rule 5b).
