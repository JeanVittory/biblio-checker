---
name: pipeline-graph-state
description: GraphState schema, reducer strategy, node topology, and i18n locale threading (updated i18n slice)
type: project
---

## GraphState schema (`apps/worker/biblio_checker_worker/langgraph/state.py`)

Inputs (set once at graph invocation):
- `job_id: str` — UUID
- `source_type: NotRequired[str]` — "pdf" | "docx" (Step 04: optional for text-mode jobs)
- `file_bytes: NotRequired[bytes]` — raw document bytes (Step 04: optional for text-mode jobs)
- `locale: str` — BCP-47 locale ("es"|"pt"|"en"), set from `AnalysisJob.locale`, never mutated

After extract_text: `raw_text: str`

After parse_references: `raw_references: list[dict]`, `total_references_detected: int`

After normalize_references: `normalized_references: Annotated[list[dict], operator.add]`

After verify_single_reference (fan-out): `verified_references: Annotated[list[dict], operator.add]`

After classify_results: `classified_references: list[dict]` (plain, no reducer)

After analyze_cross_patterns: `cross_reference_analysis: dict`

Accumulated: `warnings: Annotated[list[dict], operator.add]`

After assemble_report: `results_v1: dict`

## Node topology

START → extract_text → parse_references → normalize_references
→ [fan_out_verify] → verify_single_reference (×N, parallel)
→ classify_results → analyze_cross_patterns → ai_adjudicate → assemble_report → END

Fan-out uses `Send()` — one per normalized reference. Each Send() partial state includes `locale`.

## Key reducer strategy

`normalized_references`, `verified_references`, `warnings` use `operator.add` (fan-out accumulation).
`classified_references` is plain (no reducer) — written once by classify_results after fan-in.
`cross_reference_analysis` is plain — written once.

## i18n integration (Steps 05-07)

- `locale` comes from `AnalysisJob.locale` (added to `_FIELDS` whitelist + `from_row()` with `filtered.get("locale") or "es"`)
- `flow.py` threads it into initial_state: `"locale": job.locale`
- `fan_out_verify` adds `"locale": locale` to each Send() partial state
- All nodes read `state.get("locale", "es")` defensively
- `assemble_report` uses `locale` for `reportLanguage` (widened from `^es$` to `^(es|pt|en)$`)

**Why:** locale is set once at job creation time (immutable), threaded through the entire graph so every user-facing string renders in the chosen language.
**How to apply:** Any new node that builds decisionReason or warning messages must read `state.get("locale", "es")` and pass it to `render()`.

## Step 04: Text-mode subgraph (flow.py)

A separate `_compiled_text_graph` is built by `_build_text_graph()` — topology is START → normalize_references → fan_out_verify → verify_single_reference → classify_results → analyze_cross_patterns → ai_adjudicate → assemble_report → END.

Initial state for text-mode: `{job_id, locale, raw_text, raw_references: [{index:0, rawText:...}], warnings:[], total_references_detected:1}`. No `file_bytes` or `source_type`.

`fan_out_verify` from `graph.py` is reused directly — it works because it reads `normalized_references` from state after normalize_references runs, same as in file-mode.
