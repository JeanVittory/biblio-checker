# LangGraph Reference Analysis Pipeline

## Overview

This specification suite defines the LangGraph-based analysis pipeline that powers the core functionality of Biblio Checker: verifying academic bibliographic references against OpenAlex, SciELO, and arXiv. The pipeline replaces the current stub in `apps/worker/biblio_checker_worker/langgraph/flow.py` with a fully functional graph that extracts, parses, normalizes, verifies, classifies, and reports on bibliographic references.

## Problem Statement

The worker has a 3-stage pipeline (extract → langgraph → persist) where the LangGraph stage is currently stubbed — `start_analysis_flow()` returns an empty dict `{}`. The surrounding infrastructure (polling, job claiming, error handling, retry, persistence) is fully implemented. This suite defines the graph that runs inside the `langgraph` stage to produce a valid `ResultsV1` payload.

## Key Assumption

The uploaded document contains **only** bibliographic references (like the final references section of an academic paper). There is no need to search for or identify a bibliography section within a larger document.

## Scope

**In scope:**
- Graph state definition and topology (nodes, edges, fan-out/fan-in)
- Text extraction from PDF/DOCX (duplicated from backend, not shared)
- LLM-based reference parsing (splitting individual references from text)
- LLM-based reference normalization (style-agnostic: APA, Vancouver, Chicago, IEEE, etc.)
- Configurable LLM provider (Anthropic/OpenAI)
- HTTP clients for OpenAlex, SciELO, and arXiv APIs
- Fuzzy matching and similarity scoring
- Deterministic classification engine (applying the compatibility matrix)
- Fan-out verification (parallel per-reference checking)
- Report assembly and ResultsV1 Pydantic validation
- Lease renewal during long-running graph execution
- Per-reference error isolation

**Out of scope:**
- Worker polling loop, job claiming, retry strategy (see `spec/worker-framework/`)
- ResultsV1 schema definition (see `spec/results-contract-v1/`)
- Frontend display of results
- Audit logging integration (see `spec/audit-logging/`)
- Database schema for `analysis_jobs` table

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Reference parsing method | LLM (direct) | PDF extraction artifacts and varied listing formats make heuristic parsing unreliable |
| Normalization approach | LLM (style-agnostic) | Must handle APA, Vancouver, Chicago, IEEE, Harvard, and any other citation style without configuration |
| LLM provider | Configurable (Anthropic/OpenAI) | Flexibility to switch providers based on cost, availability, or performance |
| Text extraction | Duplicated from backend | Avoids cross-app imports; keeps worker and backend independent |
| API sources | All 3 from start (OpenAlex, SciELO, arXiv) | ResultsV1 schema already contemplates all three; incremental rollout adds complexity |
| Fan-out strategy | LangGraph `Send()` per reference | Native LangGraph pattern for dynamic parallelism with automatic fan-in |
| Lease management | Renewal before expensive operations | Prevents lease expiry during LLM calls and API verification batches |
| Per-reference errors | Isolated as `processing_error` | One bad reference must not fail the entire analysis |
| ResultsV1 validation | Pydantic copy in worker | Validates output before returning; no cross-app import dependency |

## Audience

| Reader | Start here |
|--------|------------|
| Understanding the full pipeline | Step 01 (overview), then Step 02 (graph topology) |
| Implementing LLM integration | Step 04 (LLM factory), then Steps 05-06 (parse/normalize nodes) |
| Implementing API clients | Step 07 (API clients), then Step 08 (scoring) |
| Understanding classification logic | Step 09 (classification engine) |
| Wiring everything together | Step 13 (graph construction), then Step 14 (integration) |

## Statistics

| Metric | Value |
|--------|-------|
| Total steps | 14 |
| New Python modules | ~20 files |
| Modified Python modules | 3 files (`flow.py`, `config.py`, `repo.py`) |
| New database migrations | 1 (lease renewal RPC) |
| New dependencies | 6 (`langchain-anthropic`, `langchain-openai`, `langchain-core`, `httpx`, `pdfminer.six`, `python-docx`) |
| Implementation phases | 5 (foundation, LLM, API clients, lease renewal, integration) |
