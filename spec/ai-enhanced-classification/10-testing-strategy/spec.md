# Step 10 — Testing Strategy

## Scope

- Define the testing approach for all three phases
- Specify unit test requirements per component
- Specify integration test requirements for the updated graph
- Define E2E validation criteria

**Out of scope:** Implementation of tests (this is a specification, not code). CI/CD pipeline configuration.

## Context

The worker test suite lives in `apps/worker/tests/` and uses `pytest` with `uv run`. Existing tests cover scoring (`test_scoring.py`) and can be extended for the new components. LLM calls in tests must be mocked — tests must not make real API calls.

## Requirements

### 1. Phase A Tests — Enriched Decision Reasons (Step 02)

#### 1.1 Unit Tests for `classify_reference`

File: `tests/test_classification.py` (extend existing or create new)

**Test cases for Rule 1 (exact DOI match):**
- Verify `decisionReason` contains the DOI value
- Verify `decisionReason` contains the matched title (truncated if > 80 chars)
- Verify `decisionReason` contains the source name
- Verify `decisionReason` contains the year when available
- Verify `decisionReason` omits year when candidate year is null
- Verify `decisionReason` omits title when candidate title is null

**Test cases for Rule 2 (exact identifier match):**
- Same pattern as Rule 1 but with arXiv ID

**Test cases for Rule 3 (DOI conflict):**
- Verify `decisionReason` contains both the matched title and the reference title
- Verify `decisionReason` contains both years when available
- Verify message reflects title-only conflict vs year-only conflict vs both

**Test cases for Rule 4 (cross-source conflict):**
- Verify `decisionReason` names the conflicting sources
- Verify `decisionReason` describes the specific conflict (year, DOI, or both)

**Test cases for Rules 5, 5b, 6:**
- Verify `decisionReason` contains the score as percentage
- Verify `decisionReason` contains the candidate title
- Verify Rule 6 includes top two candidates

**Test cases for title truncation:**
- Title of exactly 80 characters is not truncated
- Title of 81 characters is truncated to 77 + "..."
- Null title is omitted gracefully

**Test cases for score formatting:**
- 0.92 → "92%"
- 1.0 → "100%"
- 0.5 → "50%"

### 2. Phase B Tests — AI Adjudication (Steps 03–05)

#### 2.1 Unit Tests for Adjudication Data Model

File: `tests/test_adjudication_model.py`

- Valid `AdjudicationResult` with all fields populated validates successfully
- `suggested_classification` rejects values not in the Classification enum
- `ai_analysis` exceeding 500 characters is handled (truncated or rejected)
- `fabrication_indicators` limited to 10 items
- `AdjudicationBatchOutput` with empty list is valid
- `reference_id` is required and non-empty

#### 2.2 Unit Tests for Confidence Band Derivation

File: `tests/test_adjudication_model.py` or `tests/test_adjudication_node.py`

- `verified` + 0.95 → `very_high` (valid, accepted)
- `verified` + 0.85 → `high` (valid, accepted)
- `verified` + 0.40 → `high` (valid — the "else" branch; `high` IS in allowed set for `verified`. Accepted)
- `likely_verified` + 0.80 → `high` (valid, accepted)
- `likely_verified` + 0.60 → `medium` (valid, accepted)
- `ambiguous` + 0.50 → `medium` (valid, accepted)
- `ambiguous` + 0.30 → `low` (valid, accepted)
- `not_found` + 0.20 → `low` (valid, accepted)
- `not_found` + 0.10 → `very_low` (valid, accepted)
- `not_found` + 0.80 → rejection (`low` band derivation, but score 0.80 would derive `low` per the threshold. Actually: >= 0.20 → `low`. `low` IS in allowed set for `not_found`. So this is accepted too)
- `suspicious` + 0.90 → `very_high` (valid, accepted)
- **Rejection case:** The compatibility matrix does NOT produce rejections via the band derivation table in Step 03 because every "else" branch maps to a band that is in the allowed set. Rejections occur ONLY when `suggested_classification` is `processing_error` (explicitly excluded from LLM output enum)

#### 2.3 Unit Tests for `ai_adjudicate` Node

File: `tests/test_ai_adjudicate.py`

**LLM must be mocked** using a fixture that returns a predetermined `AdjudicationBatchOutput`.

**Test cases:**
- Feature flag disabled → pass-through, no LLM call
- No eligible references → pass-through, no LLM call
- All references are `processing_error` → pass-through, no LLM call
- 5 eligible references → all 5 sent to LLM mock, results applied
- 25 eligible references, cap is 20 → only 20 sent (sorted by lowest confidence)
- LLM suggests valid reclassification → classification updated, `manualReviewRequired` recomputed
- LLM suggests invalid reclassification → classification preserved, `ai_analysis` still applied as `decisionReason`
- LLM returns mismatched `reference_id` → that adjudication is skipped
- LLM call fails → all references preserved unchanged, warning added
- `reasonCode` is never modified by adjudication
- Reference order is preserved in output
- `fabrication_indicators` are appended to `decisionReason`

#### 2.4 Unit Tests for Prompts

File: `tests/test_adjudication_prompts.py`

- System prompt contains prompt injection warning
- User prompt correctly formats reference data (null fields as "N/A")
- User prompt truncates raw text at 500 characters
- User prompt limits candidates to 5 per reference
- Cross-reference context block is included when available
- Cross-reference context block is omitted when not available

### 3. Phase C Tests — Cross-Reference Patterns (Steps 06–07)

#### 3.1 Unit Tests for Deterministic Pattern Detection

File: `tests/test_cross_patterns.py`

**Note:** The `analyze_cross_patterns` node function must accept an injectable `current_year` parameter (defaulting to `datetime.now().year`) so temporal checks can be tested deterministically. All temporal tests must patch `current_year` to a fixed value (e.g., 2026).

**Venue cluster tests:**
- 3 `not_found` refs with same normalized venue → flag produced
- 2 `not_found` refs with same venue → no flag (threshold is 3)
- 3 `not_found` refs with different venues → no flag
- 3 `verified` refs with same venue → no flag (requires `not_found`)
- Venue normalization: lowercase, strip punctuation, collapse spaces

**DOI prefix tests:**
- 2 `not_found` refs with same DOI prefix, no verified refs with that prefix → flag
- 2 `not_found` refs with same DOI prefix, 1 verified ref with same prefix → no flag
- References with null DOI → skipped

**Self-citation tests:**
- Author appears in 50% of refs → flag (exceeds 40%)
- Author appears in 39% of refs → no flag
- Last name extraction works correctly for multi-word names

**Temporal impossibility tests:**
- Year 2027 when current year is 2026 → flag
- Year 2026 → no flag
- Null year → skipped

**Edge cases:**
- Empty reference list → empty flags
- Single reference → only temporal check applies
- Reference appears in multiple flags → included in all relevant flags

#### 3.2 Unit Tests for Cross-Pattern LLM Analysis

File: `tests/test_cross_pattern_llm.py`

**LLM must be mocked.**

- No flags → LLM not called
- 1+ flags → LLM called with flag data and reference context
- LLM response stored in `cross_reference_analysis.llm_analysis`
- LLM failure → graceful degradation, analysis without LLM enrichment
- Reference context is deduplicated when same ref appears in multiple flags

### 4. Integration Tests

File: `tests/test_graph_integration.py`

**Full graph execution with mocked LLM:**

- Graph compiles and runs with new nodes
- Pass-through mode (all features disabled) produces valid ResultsV1
- Full mode (all features enabled) produces valid ResultsV1
- Adjudication-only mode produces valid ResultsV1
- Cross-pattern-only mode produces valid ResultsV1

### 5. E2E Validation Plan

Manual validation (not automated tests):

1. Prepare a test document with known references:
   - 5 references with valid DOIs (should be `verified`)
   - 3 references with real titles but wrong DOIs (should be `suspicious`)
   - 3 references citing a non-existent journal (should trigger venue cluster flag)
   - 2 completely fabricated references (should be `not_found`, potentially reclassified to `suspicious` by adjudication)
   
2. Run the full pipeline and verify:
   - Verified references have enriched `decisionReason` with specific match data
   - Suspicious/ambiguous/not_found references have AI-generated `decisionReason`
   - Cross-pattern analysis detects the fake journal cluster
   - Adjudication provides meaningful reasoning about why fabricated refs are suspicious

## Acceptance Criteria

1. All unit tests pass with `pnpm test:worker`
2. LLM calls are mocked in all tests — no real API calls
3. Phase A tests can run independently (no dependency on Phase B/C)
4. Phase B tests can run independently with Phase A in place
5. Phase C tests require Phase B fixtures but test cross-pattern logic independently
6. Integration tests verify ResultsV1 validity across all feature flag combinations
7. No existing tests are broken by the changes

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| Running Phase A tests without Phase B/C code | Tests pass — Phase A only modifies `classification.py` |
| Running all tests with features disabled | All pass — nodes are pass-through |
| Mock LLM returns unexpected schema | Adjudication node catches the error, tests verify graceful degradation |
