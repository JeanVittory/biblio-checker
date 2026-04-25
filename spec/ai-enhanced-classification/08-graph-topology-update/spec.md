# Step 08 — Graph Topology Update

## Scope

- Define the updated LangGraph graph topology with the two new nodes
- Specify edge wiring and node registration
- Define how the fan-in/fan-out pattern remains unchanged
- Specify the state field additions

**Out of scope:** Node implementation details (Steps 05, 06, 07). Configuration (Step 09). Testing (Step 10).

## Context

The current graph topology is:

```
START
  └─► extract_text
        └─► parse_references
              └─► normalize_references
                    └─► [fan_out_verify] ──► verify_single_reference (×N, parallel)
                                                    └─► classify_results (fan-in)
                                                            └─► assemble_report
                                                                    └─► END
```

Two new nodes are inserted between `classify_results` and `assemble_report`:
1. `analyze_cross_patterns` — deterministic pattern checks (Step 06) + LLM pattern analysis (Step 07)
2. `ai_adjudicate` — LLM adjudication of uncertain references (Step 05)

## Requirements

### 1. Updated Graph Topology

```
START
  └─► extract_text
        └─► parse_references
              └─► normalize_references
                    └─► [fan_out_verify] ──► verify_single_reference (×N, parallel)
                                                    └─► classify_results (fan-in)
                                                            └─► analyze_cross_patterns
                                                                    └─► ai_adjudicate
                                                                            └─► assemble_report
                                                                                    └─► END
```

### 2. Edge Changes

**Remove:**
- `classify_results` → `assemble_report`

**Add:**
- `classify_results` → `analyze_cross_patterns`
- `analyze_cross_patterns` → `ai_adjudicate`
- `ai_adjudicate` → `assemble_report`

All new edges are deterministic (plain edges, not conditional). No conditional routing is needed — both new nodes handle their own internal skip logic (feature flags, empty inputs).

### 3. Node Registration

Two new nodes must be registered in the graph:

| Node name | Function | Module path |
|-----------|----------|-------------|
| `"analyze_cross_patterns"` | `analyze_cross_patterns` | `langgraph.nodes.cross_patterns` |
| `"ai_adjudicate"` | `ai_adjudicate` | `langgraph.nodes.ai_adjudicate` |

### 4. State Field Additions

**This step is the sole owner of all `GraphState` changes.** Other steps reference this section when they need the field.

The `GraphState` TypedDict must add one new field:

| Field | Type | Reducer | Written by | Read by |
|-------|------|---------|------------|---------|
| `cross_reference_analysis` | `dict` | None (plain field) | `analyze_cross_patterns` | `ai_adjudicate` |

This field has NO reducer (not `operator.add`) because it is written once by a single node, not accumulated from parallel invocations.

**Access pattern:** Since `cross_reference_analysis` may be absent from state when `cross_pattern_analysis_enabled = False` (the node passes through without writing the field), all consumers MUST access it via `state.get("cross_reference_analysis", {})` — never via direct key access `state["cross_reference_analysis"]`.

### 5. Existing State Fields — No Changes

The following existing fields are reused by the new nodes without modification:

| Field | Used by new nodes |
|-------|-------------------|
| `classified_references` | Read by `analyze_cross_patterns` and `ai_adjudicate`. Written back by `ai_adjudicate`. |
| `warnings` | New nodes may append warnings (uses existing `operator.add` reducer) |

### 6. Backward Compatibility

- The `fan_out_verify` conditional edge is unchanged
- The `verify_single_reference` → `classify_results` edge is unchanged
- All nodes before `classify_results` are unaffected
- The `assemble_report` node reads `classified_references` as before — the new nodes modify this field in place, so `assemble_report` requires no changes

### 7. Node Ordering Guarantees

LangGraph's edge-based execution guarantees:
1. `analyze_cross_patterns` runs AFTER `classify_results` completes (all references classified)
2. `ai_adjudicate` runs AFTER `analyze_cross_patterns` completes (cross-pattern analysis available)
3. `assemble_report` runs AFTER `ai_adjudicate` completes (all adjudications applied)

There is no parallelism between the new nodes — they run sequentially.

## Acceptance Criteria

1. The graph compiles without errors after topology changes
2. The new nodes are registered with correct function references
3. Edge from `classify_results` goes to `analyze_cross_patterns`, not directly to `assemble_report`
4. Edge from `ai_adjudicate` goes to `assemble_report`
5. `GraphState` includes the `cross_reference_analysis: dict` field with no reducer
6. Existing fan-out/fan-in pattern is unchanged
7. `assemble_report` requires no code changes
8. The graph produces valid `ResultsV1` output when both new nodes are in pass-through mode (no flags detected, adjudication disabled)

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| Both new nodes are pass-through (no flags, adjudication disabled) | Graph behaves identically to the current topology. `classified_references` flows unchanged to `assemble_report` |
| `analyze_cross_patterns` writes `cross_reference_analysis` but `ai_adjudicate` is disabled | `cross_reference_analysis` is in state but unused. No issue — state fields are optional to consume |
| `ai_adjudicate` runs but `cross_reference_analysis` is missing from state | Node handles this gracefully — cross-pattern context is optional (see Step 05, requirement 5) |
