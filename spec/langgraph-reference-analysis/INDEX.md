# LangGraph Reference Analysis — Reading Order and Dependencies

## Dependency Graph

```
01 (Overview) ──> 02 (State & Topology)
                       │
           ┌───────────┼───────────────────────┐
           v           v                       v
     03 (Extract)  04 (LLM Factory)      07 (API Clients)
                       │                       │
                  ┌────┴────┐            08 (Scoring)
                  v         v                  │
            05 (Parse)  06 (Normalize)         │
                  │         │                  │
                  └────┬────┘                  │
                       v                       │
                 09 (Classification) <─────────┘
                       │
                       v
               10 (Verify Node) ──> 12 (Lease Renewal)
                       │
                       v
               11 (Assemble Report)
                       │
                       v
               13 (Graph Construction)
                       │
                       v
               14 (Integration & Entry Point)
```

## Navigation

| Step | Title | Depends on | Key deliverable |
|------|-------|------------|-----------------|
| 01 | Overview and Dependencies | — | `pyproject.toml` updates, `.env.example`, new directory structure |
| 02 | Graph State and Topology | 01 | `GraphState` TypedDict, topology diagram, node/edge definitions |
| 03 | Text Extraction Node | 02 | `nodes/extract_text.py`, pdfminer/python-docx logic |
| 04 | LLM Client Factory | 02 | `clients/llm.py`, configurable provider (Anthropic/OpenAI) |
| 05 | Parse References Node | 02, 04 | `nodes/parse_references.py`, `prompts/parse_references.py` |
| 06 | Normalize References Node | 02, 04 | `nodes/normalize.py`, `prompts/normalize.py` |
| 07 | API Clients | 02 | `clients/openalex.py`, `clients/scielo.py`, `clients/arxiv.py` |
| 08 | Scoring and Fuzzy Matching | 07 | `scoring.py`, title/author similarity utilities |
| 09 | Classification Engine | 08, 02 | `classification.py`, deterministic rules, Spanish decision reasons |
| 10 | Verify Reference Node | 07, 08, 09, 12 | `nodes/verify.py`, fan-out target, per-reference error isolation |
| 11 | Assemble Report Node | 09 | `nodes/assemble.py`, `schemas.py` (ResultsV1 copy), final validation |
| 12 | Lease Renewal | 02 | SQL migration, `repo.renew_lease()`, renewal utility |
| 13 | Graph Construction and Wiring | 03–12 | `graph.py`, `StateGraph` with nodes, edges, `Send()` fan-out |
| 14 | Integration and Entry Point | 13 | Updated `flow.py`, end-to-end tests |

## Implementation Phases

**Phase 1 — Foundation** (Steps 01–03, 11): Directory structure, dependencies, config, text extraction, report assembly, ResultsV1 schemas. No external calls.

**Phase 2 — LLM Integration** (Steps 04–06): Configurable LLM client, prompts, parse and normalize nodes. Tests with mocked LLM.

**Phase 3 — API Clients and Scoring** (Steps 07–08): OpenAlex, SciELO, arXiv HTTP clients. Fuzzy matching utilities. Tests with mocked HTTP.

**Phase 4 — Classification and Verification** (Steps 09–10, 12): Classification engine, verify node with fan-out, lease renewal. Tests for classification rules.

**Phase 5 — Graph Assembly and Integration** (Steps 13–14): Wire all nodes into the StateGraph, update `flow.py`, end-to-end integration tests.
