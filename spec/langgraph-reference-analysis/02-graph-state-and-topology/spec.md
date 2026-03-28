# Step 02 — Graph State and Topology

## Scope

- Define the `GraphState` TypedDict that flows through all graph nodes
- Define the graph topology (node order, edges, fan-out/fan-in)
- Define the reducer strategy for accumulating parallel results
- Define each node's input/output contract at a high level

**Out of scope:** Individual node implementations (Steps 03–11). Graph construction code (Step 13).

## Context

LangGraph uses a `StateGraph` parameterized by a `TypedDict`. Each node is a function that receives the current state and returns a partial dict with updates. For list fields that must accumulate results from parallel nodes (fan-out), LangGraph uses `Annotated[list, operator.add]` as a reducer — multiple updates are concatenated rather than overwritten.

The graph has 6 nodes arranged in a linear pipeline with one fan-out/fan-in section for parallel reference verification.

## Requirements

### 1. GraphState Definition — `langgraph/state.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/state.py`

```python
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class GraphState(TypedDict):
    # --- Inputs (set once at graph invocation) ---
    job_id: str
    source_type: str                  # "pdf" | "docx"
    file_bytes: bytes

    # --- After extract_text node ---
    raw_text: str

    # --- After parse_references node ---
    raw_references: list[dict]        # [{rawText: str, index: int}]
    total_references_detected: int

    # --- After normalize_references node ---
    normalized_references: Annotated[list[dict], operator.add]
    # Each dict: {referenceId, rawText, normalized: {title, authors, year, venue, doi, arxivId}}

    # --- After verify_single_reference (fan-out/fan-in) ---
    verified_references: Annotated[list[dict], operator.add]
    # Each dict: full ReferenceResult-like structure with evidence, candidates, source_errors

    # --- After classify_results node ---
    classified_references: list[dict]
    # Plain list (NO reducer). Written once by classify_results after fan-in.
    # Each dict: verified_reference enriched with classification fields.
    # Using a plain field (not operator.add) prevents double-accumulation since
    # classify_results runs once after fan-in, not in parallel.

    # --- Accumulated across all nodes ---
    warnings: Annotated[list[dict], operator.add]
    # Each dict: {code: str, message: str, referenceId: str | None, details: dict | None}

    # --- After assemble_report node ---
    results_v1: dict
    # The final ResultsV1 payload, Pydantic-validated
```

### 2. Field Semantics

| Field | Set by | Reducer | Description |
|-------|--------|---------|-------------|
| `job_id` | Entry point | overwrite | UUID of the analysis job |
| `source_type` | Entry point | overwrite | `"pdf"` or `"docx"` |
| `file_bytes` | Entry point | overwrite | Raw document bytes from Supabase Storage |
| `raw_text` | `extract_text` | overwrite | Plain text extracted from the document |
| `raw_references` | `parse_references` | overwrite | List of raw reference strings with index |
| `total_references_detected` | `parse_references` | overwrite | Count of references found in the document |
| `normalized_references` | `normalize_references` | `operator.add` | Structured reference metadata |
| `verified_references` | `verify_single_reference` | `operator.add` | References with evidence from API lookups (pre-classification) |
| `classified_references` | `classify_results` | none (plain list) | References enriched with classification fields — written once after fan-in |
| `warnings` | Any node | `operator.add` | Warnings accumulated during processing |
| `results_v1` | `assemble_report` | overwrite | Final validated ResultsV1 dict |

### 3. Graph Topology

```
[START]
   │
   ▼
┌──────────────┐
│ extract_text │  deterministic — pdfminer.six / python-docx
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ parse_references │  LLM — splits raw text into individual references
└──────┬───────────┘
       │
       ▼
┌──────────────────────┐
│ normalize_references │  LLM — extracts structured fields from each reference
└──────┬───────────────┘
       │
       ▼ (conditional edge: fan_out_verify)
   ┌───┴───┐
   │ Send()│ one per normalized reference
   └───┬───┘
       │ (N parallel invocations)
       ▼
┌────────────────────────┐
│ verify_single_reference│  deterministic + HTTP — queries 3 APIs per reference
└──────┬─────────────────┘
       │ (fan-in via operator.add reducer on verified_references)
       ▼
┌──────────────────┐
│ classify_results │  deterministic — applies compatibility matrix
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ assemble_report  │  deterministic — builds and validates ResultsV1
└──────┬───────────┘
       │
       ▼
     [END]
```

### 4. Edge Definitions

| From | To | Type | Condition |
|------|----|------|-----------|
| `START` | `extract_text` | Normal | Always |
| `extract_text` | `parse_references` | Normal | Always |
| `parse_references` | `normalize_references` | Normal | Always |
| `normalize_references` | `verify_single_reference` | Conditional (fan-out) | `Send()` per normalized reference |
| `verify_single_reference` | `classify_results` | Normal | After all `Send()` invocations complete (fan-in) |
| `classify_results` | `assemble_report` | Normal | Always |
| `assemble_report` | `END` | Normal | Always |

### 5. Fan-Out Strategy

The conditional edge after `normalize_references` uses LangGraph's `Send()` API. The full implementation (including the zero-references branch) is defined in Step 13.

Each `Send()` invokes `verify_single_reference` with the specific reference data. The `operator.add` reducer on `verified_references` and `warnings` automatically concatenates results from all parallel invocations.

### 6. Node Contract Summary

Each node is a function with signature:

```python
def node_name(state: GraphState) -> dict:
    """Returns a partial state update dict."""
    ...
```

| Node | Reads from state | Writes to state | LLM? | HTTP? |
|------|-----------------|-----------------|------|-------|
| `extract_text` | `file_bytes`, `source_type` | `raw_text` | No | No |
| `parse_references` | `raw_text` | `raw_references`, `total_references_detected` | Yes | No |
| `normalize_references` | `raw_references` | `normalized_references` | Yes | No |
| `verify_single_reference` | `reference` (from Send) | `verified_references`, `warnings` | No | Yes |
| `classify_results` | `verified_references` | `classified_references` | No | No |
| `assemble_report` | `classified_references`, `total_references_detected`, `warnings` | `results_v1` | No | No |

## Acceptance Criteria

- [ ] `GraphState` TypedDict is defined in `langgraph/state.py` with all fields listed above
- [ ] Fields that use fan-out use `Annotated[list[dict], operator.add]` as reducer
- [ ] Fields that are set once use plain types (no reducer)
- [ ] The file imports `operator` and `Annotated` correctly
- [ ] The topology supports linear flow with one fan-out/fan-in section
- [ ] Each node's input/output fields are clearly documented

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Document contains 0 references | `parse_references` returns `raw_references=[]`, `total_references_detected=0`. Fan-out routes to `classify_results` with empty data (see Step 13). `classify_results` writes an empty `classified_references`. `assemble_report` produces a valid ResultsV1 with empty `references[]`. |
| Document contains 1 reference | Single `Send()` call. No parallelism but the same code path executes. |
| Document contains 200+ references | 200+ `Send()` calls. LangGraph handles the parallelism. Lease renewal (Step 12) prevents timeout. |

## Dependencies

- **Depends on:** Step 01 (directory structure, schemas)
- **Informs:** All node steps (03–11), graph construction (Step 13)
