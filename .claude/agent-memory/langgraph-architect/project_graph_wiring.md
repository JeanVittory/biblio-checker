---
name: graph-wiring-patterns
description: Key implementation details for graph.py and flow.py (Steps 13-14) — Send import location, fan-out pattern, test isolation
type: project
---

## Send import location

`Send` is NOT in `langgraph.graph` in the installed version. Use:
```python
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
```

## fan_out_verify pattern

Zero-references path sends directly to `classify_results` (not `verify_single_reference`)
to avoid hanging the graph. The Send payload must include `classified_references: []`
because that field has no reducer and classify_results expects it.

Each verify Send includes `warnings: []` and `verified_references: []` (empty lists)
because these fields use `operator.add` reducer — omitting them would cause reducer errors.

Truncation warning goes in the first Send's `warnings` list to reach parent state
via the operator.add reducer.

## Test isolation for integration tests

Do NOT use `sys.modules.setdefault()` to inject lease stubs at module level —
this persists across the pytest session and breaks `test_lease_renewal.py`.
Instead, patch `biblio_checker_worker.langgraph.flow.init_lease_context` and
`biblio_checker_worker.langgraph.flow.clear_lease_context` in each test's
context manager stack.

Also reset `flow_module._compiled_graph = None` before each integration test
to force recompilation with fresh mocks.

## test_assemble_report.py — lease stub removal

The original file used `sys.modules.setdefault` to inject a stub lease module
(because lease.py didn't exist). That was removed and replaced with
`patch("biblio_checker_worker.langgraph.nodes.assemble.renew_lease_if_needed")`
inside the `_invoke` helper. The `_invoke` signature now accepts an optional
`mock_renew` parameter for the lease renewal test.

## All APIs fail → not processing_error

When all three API sources raise (TimeoutException or ConnectError), the
verify node catches each error per-source, accumulates `source_timeout_partial`
warnings, and returns normally with zero candidates. The classification engine
then assigns `not_found` with reason `source_timeout_partial` — NOT
`processing_error`. Only an unhandled exception in the verify node itself
produces `processing_error`.

**Why:** The outer try/except in verify_single_reference only triggers on
non-source errors (e.g., schema construction failure, unexpected crash).

**How to apply:** Test assertions for "all APIs fail" should check for
`not_found` or `source_timeout_partial` classification — not `processing_error`.
