---
name: ai-adjudication-phase-b
description: AI adjudication node implementation details — structured output schema, prompt design, node behavior, and security measures
type: project
---

## Files created in Phase B

- `langgraph/prompts/adjudicate.py` — `AdjudicationResult`, `AdjudicationBatchOutput` Pydantic schemas + `ADJUDICATE_SYSTEM_PROMPT` + `build_adjudication_user_prompt()`
- `langgraph/nodes/ai_adjudicate.py` — main node function
- `langgraph/nodes/cross_patterns.py` — Phase B pass-through placeholder (returns `{"cross_reference_analysis": {}}`)

## Structured output schema

`AdjudicationResult` fields:
- `reference_id: str` — must match input referenceId
- `ai_analysis: str` — no max-length at schema level; truncated to 500 chars in node
- `suggested_classification: Classification` — enum, never `processing_error`
- `suggested_confidence_score: float` — 0.0–1.0
- `fabrication_indicators: list[str]` — 0–10 items, each up to 200 chars

`AdjudicationBatchOutput` wraps `adjudications: list[AdjudicationResult]`.

## Confidence band derivation

Bands are derived from `(suggested_classification, suggested_confidence_score)`:
- `verified`: ≥0.90 → very_high, else → high
- `likely_verified`: ≥0.80 → high, else → medium
- `ambiguous`: ≥0.50 → medium, else → low
- `not_found`: ≥0.20 → low, else → very_low
- `suspicious`: ≥0.90 → very_high, ≥0.80 → high, else → medium

If derived band is not in `_ALLOWED_BANDS[classification]`, suggestion is rejected and deterministic classification is preserved.

## Security defense-in-depth

1. Injection warning is **first paragraph** of system prompt (before role)
2. All untrusted content uses XML-delimiter tags: `<untrusted_reference>`, `<raw_text>`, `<title>`, `<candidates>`
3. Schema constrains `suggested_classification` to enum values
4. Compatibility matrix rejects invalid band combinations
5. Content plausibility check on `ai_analysis`: rejects authority-framing phrases ("verificado por", "según CrossRef", "confirmado externamente", "verified by", "confirmed by", "esta referencia es confiable", "no hay preocupaciones") and injection artifacts ("ignore", "override", "system:", "[INST]", "ignorar", "anular", "sistema:")
6. Candidate titles and fabrication_indicators: strip HTML tags and markdown links before use

## Per-field truncation in prompt construction

| Field | Max |
|-------|-----|
| raw_text | 500 chars |
| title | 300 chars |
| venue | 200 chars |
| each author | 100 chars |
| authors list | first 10 |
| decision_reason | 300 chars |
| each candidate title | 200 chars |
| candidates per reference | top 5 by score |

## Node behavior (ai_adjudicate)

1. Check `ai_adjudication_enabled` flag — pass-through if False
2. Filter: `manualReviewRequired == True` AND `classification != processing_error`
3. Sort by `confidenceScore` ascending (most uncertain first), cap at `ai_adjudication_max_references`
4. Short-circuit with `ai_adjudicate_skipped` log if no eligible refs
5. Single batched LLM call with `with_structured_output(AdjudicationBatchOutput)`
6. For each result: match by reference_id → derive band → check matrix → apply or reject
7. Plausibility check on ai_analysis → write to decisionReason (or preserve original if fails)
8. Append sanitized fabrication_indicators as bullet list
9. Recompute manualReviewRequired; never overwrite reasonCode
10. Merge back preserving original list order
11. All exceptions caught → graceful degradation + warning in state

## New settings fields (config.py)

- `ai_adjudication_enabled: bool = True` — `AI_ADJUDICATION_ENABLED`
- `ai_adjudication_max_references: int = 20` (ge=1, le=150) — `AI_ADJUDICATION_MAX_REFERENCES`
- `cross_pattern_analysis_enabled: bool = True` — `CROSS_PATTERN_ANALYSIS_ENABLED`
- `cross_pattern_llm_enabled: bool = True` — `CROSS_PATTERN_LLM_ENABLED`
