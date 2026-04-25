# Step 03 — Adjudication Data Model

## Scope

- Define the structured output schema that the LLM must return for each adjudicated reference
- Define the internal state field that carries adjudication results through the graph
- Specify how adjudication results map to existing ResultsV1 fields

**Out of scope:** Prompt content (Step 04). Node behavior and batching logic (Step 05). Graph wiring (Step 08).

## Context

The AI adjudication node will send uncertain references to the LLM and receive structured assessments. The LLM response must be constrained to a Pydantic model so that:

1. The LLM cannot invent new classification categories or reason codes
2. The compatibility matrix in `schemas.py` validates the result
3. The response is machine-parseable without post-processing

The structured output schema is used with LangChain's `.with_structured_output()` method, consistent with how `parse_references` and `normalize_references` already work.

## Requirements

### 1. Single Reference Adjudication Result

The LLM returns one adjudication result per reference. Each result contains:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `reference_id` | string | Must match the input reference's `referenceId` | Links the result back to the reference |
| `ai_analysis` | string | 1 character minimum, no max-length constraint on the Pydantic field | Natural-language explanation of why this reference is problematic or plausible. This replaces `decisionReason`. Truncation to 500 characters happens in the node's response application logic (Step 05), not at schema validation time |
| `suggested_classification` | Classification enum | Must be one of: `verified`, `likely_verified`, `ambiguous`, `not_found`, `suspicious` | The LLM's recommended classification. May differ from the deterministic rule's classification |
| `suggested_confidence_score` | float | 0.0–1.0 | The LLM's confidence in its suggested classification |
| `fabrication_indicators` | list of strings | 0–10 items, each 1–200 characters | Specific red flags identified (e.g., "DOI prefix 10.9999 is not registered with any known publisher") |

### 2. Batch Response Schema

Since multiple references are sent in a single LLM call, the response schema wraps a list:

```
AdjudicationBatchOutput {
    adjudications: list of AdjudicationResult
}
```

Each `AdjudicationResult` follows the schema in requirement 1.

### 3. Mapping to ResultsV1 Fields

The adjudication result maps to existing ResultsV1 fields as follows:

| Adjudication field | ResultsV1 field | Mapping rule |
|-------------------|-----------------|--------------|
| `ai_analysis` | `decisionReason` | Direct replacement — overwrites the deterministic rule's template string |
| `suggested_classification` | `classification` | Applied ONLY if the combination with the derived `confidenceBand` passes the compatibility matrix |
| `suggested_confidence_score` | `confidenceScore` | Applied alongside `suggested_classification` |
| `fabrication_indicators` | `decisionReason` | Appended to `ai_analysis` as bullet points if non-empty |
| (not mapped) | `reasonCode` | **Preserved from deterministic rule** — never overwritten by LLM |
| (not mapped) | `manualReviewRequired` | Recomputed based on the final `classification` value |

### 4. Confidence Band Derivation

The `confidenceBand` is not returned by the LLM — it is derived from the `suggested_classification` and `suggested_confidence_score` using the existing compatibility matrix:

| Classification | Allowed bands | Score thresholds |
|---------------|---------------|-----------------|
| `verified` | `high`, `very_high` | >= 0.90 → `very_high`, else `high` |
| `likely_verified` | `medium`, `high` | >= 0.80 → `high`, else `medium` |
| `ambiguous` | `low`, `medium` | >= 0.50 → `medium`, else `low` |
| `not_found` | `very_low`, `low` | >= 0.20 → `low`, else `very_low` |
| `suspicious` | `medium`, `high`, `very_high` | >= 0.90 → `very_high`, >= 0.80 → `high`, else `medium` |

If the derived band is not in the allowed set for the classification, the adjudication suggestion is **rejected** and the deterministic classification is preserved.

### 5. Rejection Criteria

The LLM's suggested classification is rejected (deterministic classification preserved) when:

1. The derived `confidenceBand` is not in the allowed set for the `suggested_classification`
2. The `suggested_classification` is `processing_error` (LLM must never suggest this)
3. The `reference_id` does not match any reference in the input batch
4. The `ai_analysis` is empty

When a suggestion is rejected, the `ai_analysis` is still used as `decisionReason` **only after passing the content plausibility check** (see Step 05, Requirement 6.3b). If the plausibility check fails, the original deterministic `decisionReason` is preserved. The classification, confidence score, and confidence band remain from the deterministic rule.

### 6. Graph State Field

The `cross_reference_analysis: dict` field in `GraphState` is defined in Step 08 (Graph Topology Update), which owns all state changes. See Step 08, Requirement 4 for the field specification.

The adjudication node reads `cross_reference_analysis` via `state.get("cross_reference_analysis", {})` — using `.get()` with a default because the field may be absent when cross-pattern analysis is disabled.

The adjudication node does NOT need its own state field for output — it overwrites `classified_references` via the returned state update dict (standard LangGraph pattern — nodes never mutate state in place).

## Acceptance Criteria

1. The structured output schema constrains `suggested_classification` to the `Classification` enum values (excluding `processing_error`)
2. `ai_analysis` has no max-length at schema level; truncation to 500 characters happens in the response application step (Step 05)
3. `fabrication_indicators` is limited to 10 items
4. The confidence band derivation logic produces only valid combinations per the compatibility matrix
5. When the LLM suggests an invalid classification/band combination, the deterministic classification is preserved
6. `reasonCode` is never overwritten by the adjudication — it always reflects the original deterministic rule
7. `manualReviewRequired` is recomputed after any classification change

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| LLM suggests `verified` with confidence 0.60 | Band would be `high` (valid). Accepted. |
| LLM suggests `verified` with confidence 0.40 | Band derivation produces `high` (the "else" branch). `high` IS in the allowed set for `verified`. Accepted. |
| LLM suggests `processing_error` | Rejected — this classification is reserved for system errors |
| LLM returns fewer adjudications than references sent | Missing references keep their deterministic classification |
| LLM returns a `reference_id` not in the input | That adjudication is discarded |
| LLM returns `ai_analysis` with 501+ characters | Accepted by schema (no max-length). Truncated to 500 characters in Step 05's response application logic. Suggestion still applied. |
| All fabrication_indicators are empty strings | Treated as empty list — nothing appended to `decisionReason` |
