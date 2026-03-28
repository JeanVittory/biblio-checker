---
name: pipeline-graph-state
description: GraphState TypedDict schema, reducer strategy, node topology, and fan-out/fan-in design for the LangGraph biblio-checker pipeline
type: project
---

`GraphState` is defined in `apps/worker/biblio_checker_worker/langgraph/state.py`.

## Reducer strategy

Fields that use `Annotated[list[dict], operator.add]` (fan-out accumulation):
- `normalized_references` — written by normalize_references
- `verified_references` — written by verify_single_reference (parallel Send() invocations)
- `warnings` — accumulated by any node

Fields with NO reducer (plain types, overwritten):
- `job_id`, `source_type`, `file_bytes` — inputs
- `raw_text` — extract_text node
- `raw_references`, `total_references_detected` — parse_references node
- `classified_references` — classify_results node (plain list, NOT operator.add, to prevent double-accumulation since classify_results runs once after fan-in)
- `results_v1` — assemble_report node

## Graph topology (6 nodes)

```
START → extract_text → parse_references → normalize_references
      → verify_single_reference (fan-out via Send(), N parallel)
      → classify_results (fan-in) → assemble_report → END
```

**Why:** `classified_references` was deliberately kept as a plain list (no reducer) because `classify_results` runs once after fan-in; using `operator.add` there would cause double-accumulation.
