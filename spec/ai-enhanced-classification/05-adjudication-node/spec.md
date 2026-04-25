# Step 05 — AI Adjudication Node Behavior

## Scope

- Define the complete behavior of the `ai_adjudicate` node
- Specify filtering logic: which references are sent to the LLM
- Specify batching, LLM invocation, and response application logic
- Define error handling and graceful degradation

**Out of scope:** Prompt content (Step 04). Data model (Step 03). Graph wiring (Step 08). Configuration fields (Step 09).

## Context

The `ai_adjudicate` node sits between `classify_results` (or `analyze_cross_patterns` when Phase C is active) and `assemble_report`. It reads `classified_references` from state, filters to uncertain references, sends them to the LLM for adjudication, applies the results, and writes back the enriched list.

The node follows the same patterns established by existing LangGraph nodes:
- Uses `get_llm()` from `clients/llm.py` for LLM instantiation
- Uses `structlog` for structured logging
- Uses `get_settings()` for configuration
- Returns a partial state update dict

## Requirements

### 1. Node Entry Point

The node function signature must match the LangGraph convention:

```
ai_adjudicate(state: GraphState) -> dict
```

It reads `classified_references` and optionally `cross_reference_analysis` from state.

### 2. Feature Flag Check

The first action is checking the `ai_adjudication_enabled` setting:
- If `False`, return `{"classified_references": classified_references}` immediately (pass-through, no LLM call)
- If `True`, proceed with adjudication

### 3. Reference Filtering

From `classified_references`, select references where `manualReviewRequired == True`. This includes classifications: `ambiguous`, `not_found`, `suspicious`, `processing_error`.

**Exclusion:** References with `classification == "processing_error"` are excluded from adjudication — they had a system error and there is no evidence for the LLM to reason about.

**Priority sorting:** If the number of eligible references exceeds `ai_adjudication_max_references`, sort by `confidenceScore` ascending (lowest confidence first — most uncertain references get priority) and take the first N.

### 4. Short-Circuit

If no references are eligible for adjudication (all verified/likely_verified, or all processing_error), return immediately with no LLM call:

```
{"classified_references": classified_references}
```

Log this as `ai_adjudicate_skipped` with reason `"no_eligible_references"`.

### 5. LLM Invocation

1. Get the LLM instance via `get_llm()`
2. Use `.with_structured_output(AdjudicationBatchOutput)` for structured response
3. Build the system prompt and user prompt per Step 04
4. If `cross_reference_analysis` is present in state and non-empty, include it in the user prompt
5. Invoke the LLM with the constructed messages
6. Parse the structured response

### 6. Response Application

For each `AdjudicationResult` in the LLM response:

1. **Match by reference_id:** Find the corresponding reference in `classified_references`. If no match, log a warning and skip.

2. **Validate the suggestion:**
   - Derive `confidenceBand` from `suggested_classification` + `suggested_confidence_score` using the thresholds in Step 03
   - Check the compatibility matrix: is the derived band allowed for the suggested classification?
   - If valid: apply the new classification, confidence score, and confidence band
   - If invalid: preserve the deterministic classification, score, and band. Log as `ai_adjudicate_suggestion_rejected`

3. **Apply ai_analysis (with content plausibility check):**
   
   3a. **Truncation:** If `ai_analysis` exceeds 500 characters, truncate to 497 + "..."
   
   3b. **Content plausibility check:** Before writing `ai_analysis` to `decisionReason`, validate that it does NOT contain:
   - Authority-framing language claiming external verification: "verificado por", "según CrossRef", "según DataCite", "confirmado externamente", "verified by", "confirmed by"
   - Trust assertions not grounded in evidence: "esta referencia es confiable", "no hay preocupaciones"
   - Injection artifacts: "ignore", "override", "system:", "[INST]", "ignorar", "anular", "sistema:"
   
   If the plausibility check fails: preserve the original deterministic `decisionReason`. Log as `ai_analysis_plausibility_rejected` with `reference_id` and `reason`. The classification suggestion is still evaluated independently.
   
   3c. **Sanitize fabrication_indicators:** Strip HTML tags (`<[^>]+>`) and markdown link syntax (`\[.*?\]\(.*?\)`) from each indicator string.
   
   3d. If plausibility check passes, replace `decisionReason` with `ai_analysis` (regardless of whether classification was changed). If `fabrication_indicators` is non-empty after sanitization, append them as a bulleted list:
     ```
     {ai_analysis}\n\nIndicadores de fabricación:\n- {indicator_1}\n- {indicator_2}
     ```
   
   **Note:** The assembled `decisionReason` (analysis + indicators) may exceed 500 characters. This is intentional — `ReferenceResult.decisionReason` has no max-length constraint in the schema.

4. **Recompute manualReviewRequired:**
   - If classification changed, recompute based on the `_REQUIRED_MANUAL_REVIEW` set in `schemas.py`: `ambiguous`, `not_found`, `suspicious`, `processing_error` require manual review; `verified`, `likely_verified` do not.

5. **Preserve reasonCode:** The `reasonCode` must always reflect the original deterministic rule, never overwritten by the LLM.

### 7. Merge Back

After processing all adjudication results, merge the modified references back into the full `classified_references` list (which includes both adjudicated and non-adjudicated references) and return:

```
{"classified_references": merged_list}
```

The order of references in the list must be preserved.

### 8. Error Handling

| Error scenario | Behavior |
|---------------|----------|
| LLM call times out | Log `ai_adjudicate_llm_timeout`. Return original `classified_references` unchanged. Add a warning to state: `{"code": "ai_adjudication_timeout", "message": "...", "referenceId": null, "details": null}` |
| LLM returns malformed response | Log `ai_adjudicate_parse_error`. Return original `classified_references` unchanged. Add warning. |
| LLM returns empty adjudications list | Log `ai_adjudicate_empty_response`. Return original `classified_references` unchanged. |
| Individual adjudication has invalid reference_id | Skip that adjudication, log warning, continue processing others |
| Individual adjudication has invalid classification | Preserve deterministic classification for that reference, still apply `ai_analysis` |
| Feature flag is disabled | Pass-through, no LLM call, no warnings |

The node must NEVER raise an exception that would fail the pipeline. All errors are caught, logged, and result in graceful degradation (original classifications preserved).

### 9. Logging

The node must log:

| Event | Level | Fields |
|-------|-------|--------|
| `ai_adjudicate_starting` | info | `eligible_count`, `total_count`, `capped` (bool) |
| `ai_adjudicate_skipped` | info | `reason` |
| `ai_adjudicate_llm_invoked` | info | `reference_count` |
| `ai_adjudicate_result_applied` | debug | `reference_id`, `old_classification`, `new_classification`, `classification_changed` (bool) |
| `ai_adjudicate_suggestion_rejected` | warning | `reference_id`, `reason`, `suggested_classification`, `suggested_confidence` |
| `ai_adjudicate_complete` | info | `adjudicated_count`, `classifications_changed`, `classifications_preserved` |
| Error events | error/warning | Error details, no credential leakage |

## Acceptance Criteria

1. References with `manualReviewRequired == False` are never sent to the LLM
2. References with `classification == "processing_error"` are excluded from adjudication
3. When `ai_adjudication_enabled` is `False`, no LLM call is made
4. When no eligible references exist, no LLM call is made
5. Priority sorting sends the most uncertain references first when the cap is reached
6. Invalid LLM suggestions preserve the deterministic classification
7. `ai_analysis` is applied as `decisionReason` even when the classification suggestion is rejected
8. `reasonCode` is never modified by adjudication
9. `manualReviewRequired` is recomputed after classification changes
10. Reference order in the output list matches the input order
11. All error scenarios result in graceful degradation, not pipeline failure
12. Structured logging covers all key events

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| 1 eligible reference out of 40 total | Only 1 reference sent to LLM; 39 pass through unchanged |
| 25 eligible references, cap is 20 | 20 with lowest confidence scores sent; 5 skipped with original classification |
| LLM upgrades `not_found` to `verified` with confidence 0.95 | Valid per compatibility matrix → applied |
| LLM upgrades `not_found` to `verified` with confidence 0.30 | Band would be invalid for `verified` → rejected, deterministic preserved |
| LLM downgrades `suspicious` to `ambiguous` | Valid → applied. `manualReviewRequired` remains `True` (both require it) |
| LLM upgrades `ambiguous` to `likely_verified` | Valid → applied. `manualReviewRequired` changes from `True` to `False` |
| LLM returns adjudication for reference_id "xyz" that doesn't exist | Logged as warning, skipped |
| LLM call fails but 5 of 20 references were already processed | This cannot happen — the LLM returns all adjudications at once (batch call). Either all succeed or all fail. |
