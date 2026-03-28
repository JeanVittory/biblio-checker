# Step 13 — Graph Construction and Wiring

## Scope

- Implement `graph.py` that constructs the LangGraph `StateGraph`
- Wire all nodes and edges including fan-out via `Send()`
- Define the compiled graph as a reusable object
- Define the fan-out conditional edge function

**Out of scope:** Individual node implementations (Steps 03–11). Entry point integration (Step 14).

## Context

All nodes, clients, scoring, and classification have been implemented in previous steps. This step wires them into a LangGraph `StateGraph` with the topology defined in Step 02.

LangGraph's `StateGraph` is constructed by:
1. Defining the state schema (`GraphState`)
2. Adding nodes (name → function mapping)
3. Adding edges (node → node transitions)
4. Adding conditional edges (node → dynamic routing via `Send()`)
5. Compiling the graph into an executable

## Requirements

### 1. Graph Construction — `langgraph/graph.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/graph.py`

```python
from langgraph.graph import StateGraph, START, END, Send

from biblio_checker_worker.langgraph.state import GraphState
from biblio_checker_worker.langgraph.nodes.extract_text import extract_text
from biblio_checker_worker.langgraph.nodes.parse_references import parse_references
from biblio_checker_worker.langgraph.nodes.normalize import normalize_references
from biblio_checker_worker.langgraph.nodes.verify import verify_single_reference
from biblio_checker_worker.langgraph.nodes.classify import classify_results
from biblio_checker_worker.langgraph.nodes.assemble import assemble_report


def fan_out_verify(state: GraphState) -> list[Send]:
    """Route each normalized reference to its own verify_single_reference invocation."""
    ...


def build_graph() -> StateGraph:
    """Construct and return the compiled analysis graph."""
    ...
```

### 2. Node Registration

```python
graph = StateGraph(GraphState)

graph.add_node("extract_text", extract_text)
graph.add_node("parse_references", parse_references)
graph.add_node("normalize_references", normalize_references)
graph.add_node("verify_single_reference", verify_single_reference)
graph.add_node("classify_results", classify_results)
graph.add_node("assemble_report", assemble_report)
```

### 3. Edge Wiring

```python
# Linear edges
graph.add_edge(START, "extract_text")
graph.add_edge("extract_text", "parse_references")
graph.add_edge("parse_references", "normalize_references")

# Fan-out: normalize → verify (one Send per reference)
graph.add_conditional_edges("normalize_references", fan_out_verify)

# Fan-in: verify → classify (after all Send() complete)
graph.add_edge("verify_single_reference", "classify_results")

# Linear edges (post fan-in)
graph.add_edge("classify_results", "assemble_report")
graph.add_edge("assemble_report", END)
```

### 4. Fan-Out Function

```python
def fan_out_verify(state: GraphState) -> list[Send]:
    """Create one Send per normalized reference for parallel verification.

    If there are no normalized references (empty document or parse failure),
    return a list with a single Send to classify_results with empty data
    to ensure the graph continues to completion.
    """
    settings = get_settings()
    normalized = state.get("normalized_references", [])

    if not normalized:
        # No references to verify — skip directly to classify
        # Return empty Send that routes to classify_results
        # Use warnings=[] (not state.get("warnings", [])) to avoid duplicating
        # warnings already accumulated in state via the operator.add reducer.
        return [Send("classify_results", {
            "verified_references": [],
            "classified_references": [],
            "warnings": [],
        })]

    # Cap to max_references to prevent resource exhaustion
    if len(normalized) > settings.max_references:
        truncated_count = len(normalized) - settings.max_references
        normalized = normalized[:settings.max_references]
        # The caller (graph state) already has accumulated warnings via reducer;
        # the truncation warning will be merged in automatically.
        # Return it as part of the first Send or via a separate mechanism if needed.
        # Implementation note: add a truncation warning to state before fan-out
        # by returning it alongside the sends — see Section 4 note below.

    sends = []
    for ref in normalized:
        sends.append(Send("verify_single_reference", {
            "job_id": state["job_id"],
            "reference": ref,
            "warnings": [],
            "verified_references": [],
        }))
    return sends
```

**Implementation note on max_references truncation warning:** Because `fan_out_verify` returns `list[Send]` and cannot directly accumulate to the parent state's `warnings` field, the truncation warning MUST be added by LangGraph's conditional edge mechanism. The recommended approach is to include a truncation warning in the first `Send()` call's `warnings` list if truncation occurred. This warning will be merged into the parent state via the `operator.add` reducer:

```python
if len(normalized_original) > settings.max_references:
    sends[0] = Send("verify_single_reference", {
        **sends[0].args,
        "warnings": [{
            "code": "references_truncated",
            "message": f"El documento excede el límite de {settings.max_references} referencias. Solo se procesaron las primeras {settings.max_references}.",
            "referenceId": None,
            "details": {"total_detected": len(normalized_original), "max_allowed": settings.max_references},
        }],
    })
```

**Important:** The `Send()` data dict MUST include `warnings` and `verified_references` as empty lists because these fields use `operator.add` reducer. If omitted, the reducer has nothing to concatenate with. The zero-references `Send` to `classify_results` also includes `classified_references: []` to initialize that plain field.

### 5. Graph Compilation

```python
def build_graph():
    # ... node registration and edge wiring ...
    return graph.compile()
    # LangGraph manages concurrency internally.
    # The max_references config (default: 150) caps total fan-out volume,
    # which is the primary mechanism for bounding concurrent resource usage.
```

The compiled graph is an executable object with an `.invoke(initial_state)` method.

**Concurrency note:** LangGraph manages the concurrency of `Send()` fan-out internally. Total concurrency is bounded by `settings.max_references` which caps the maximum number of simultaneous `verify_single_reference` invocations.

### 6. Graph Caching

The `build_graph()` function constructs a new graph each time. For performance, `flow.py` (Step 14) MAY cache the compiled graph as a module-level variable:

```python
_compiled_graph = None

def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
```

This is safe because the graph structure is stateless — all state flows through `GraphState`.

### 7. Zero-References Path

When `normalized_references` is empty (empty document or LLM returned no references):

1. `fan_out_verify` detects empty list
2. Skips `verify_single_reference` entirely
3. Routes to `classify_results` which receives empty `verified_references`
4. `assemble_report` builds a valid ResultsV1 with zero references

This MUST NOT cause a graph execution error.

## Acceptance Criteria

- [ ] `build_graph()` returns a compiled `StateGraph`
- [ ] All 6 nodes are registered with correct names
- [ ] Linear edges connect: START → extract_text → parse_references → normalize_references
- [ ] Conditional edge from `normalize_references` uses `fan_out_verify` with `Send()`
- [ ] Edge from `verify_single_reference` connects to `classify_results`
- [ ] Linear edges connect: classify_results → assemble_report → END
- [ ] `fan_out_verify` creates one `Send` per normalized reference
- [ ] Empty `normalized_references` does NOT cause a graph error — produces valid empty ResultsV1
- [ ] `Send()` data includes `warnings` and `verified_references` as empty lists
- [ ] Graph can be compiled without errors (`build_graph()` does not raise)
- [ ] Unit test: invoke graph with mocked nodes to verify edge wiring

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| 0 normalized references | `fan_out_verify` returns routing to classify with empty data. Valid empty ResultsV1 produced. |
| 1 normalized reference | 1 `Send()` call. Same code path as N references. |
| 200 normalized references | 200 `Send()` calls. LangGraph handles parallelism internally. |
| Node raises an exception | Exception propagates out of `graph.invoke()`. Caught by `run_langgraph_stage` as `StageError`. |
| `verify_single_reference` partially fails (some refs error) | Those refs have `processing_error` classification. Graph continues to classify and assemble. |

## Dependencies

- **Depends on:** Steps 03–12 (all node implementations)
- **Informs:** Step 14 (flow.py invokes the compiled graph)
