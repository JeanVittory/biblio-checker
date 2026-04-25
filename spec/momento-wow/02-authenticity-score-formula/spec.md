# Step 02 — Authenticity Score Formula

## Scope

This step specifies the algorithm that computes a single numeric Authenticity Score (0-100) from a `ResultsV1` summary. It covers:
- Classification weights
- Score computation formula
- Band thresholds and labels
- Edge case handling for degenerate inputs

This step does NOT cover:
- How the score is rendered in the UI (see Step 03)
- How the score appears in the PDF export (see Step 07)
- Modifications to the `ResultsV1` contract
- Custom or user-adjustable weights

## Context

The `ResultsV1.summary.countsByClassification` object contains six integer fields representing how many references fell into each classification category. Today these counts are displayed as a breakdown table, but no single number summarizes the overall quality. The Authenticity Score fills this gap by applying weights that reflect the trustworthiness signal of each classification.

The score is computed entirely on the frontend from data already available in the `ResultsV1` payload. No backend changes are needed.

## Requirements

### 1) Classification Weights

Each classification MUST have a fixed weight between 0.0 and 1.0:

| Classification | Weight | Rationale |
|----------------|--------|-----------|
| `verified` | 1.00 | Strong positive signal — high-confidence match found |
| `likely_verified` | 0.75 | Moderate positive signal — plausible match with partial metadata |
| `ambiguous` | 0.25 | Weak signal — multiple plausible candidates, inconclusive |
| `not_found` | 0.00 | Negative signal — no match in any source |
| `suspicious` | 0.00 | Negative signal — metadata conflicts detected |
| `processing_error` | N/A | Excluded from calculation entirely |

### 2) Score Formula

The score MUST be computed using only the fields available in `countsByClassification`:

```
eligible = verified + likely_verified + ambiguous + not_found + suspicious
         (i.e., the sum of all classification counts EXCLUDING processing_error)

weightedSum = (verified × 1.00)
            + (likely_verified × 0.75)
            + (ambiguous × 0.25)
            + (not_found × 0.00)
            + (suspicious × 0.00)

score = round((weightedSum / eligible) × 100)
```

- The `eligible` denominator is derived solely from `countsByClassification` — the function does NOT use `totalReferencesAnalyzed` or any field outside the input object
- The result MUST be an integer in the range [0, 100]
- Rounding MUST use standard mathematical rounding (`Math.round`)

### 3) Denominator Edge Case

When `eligible` is 0 (i.e., all references are `processing_error` or no references were analyzed), the score MUST be 0.

This covers:
- `totalReferencesAnalyzed = 0` (document had no detectable references)
- All references classified as `processing_error`

### 4) Band Thresholds

The score MUST map to exactly one of three bands:

| Band | Range | Meaning |
|------|-------|---------|
| `high` | 80 ≤ score ≤ 100 | Bibliography has high authenticity; most references verified |
| `medium` | 50 ≤ score ≤ 79 | Bibliography needs review; mixed results |
| `low` | 0 ≤ score ≤ 49 | Bibliography has low authenticity; many references unverified or suspicious |

Band boundaries are inclusive. A score of exactly 80 is `high`; a score of exactly 50 is `medium`.

### 5) Return Type

The computation MUST return an object with two fields:
- `score` — integer (0-100)
- `band` — string literal: `"high"` | `"medium"` | `"low"`

### 6) Input Type

The function MUST accept the `countsByClassification` object as defined in the `ResultsV1` contract:

```
{
  verified: integer (≥ 0)
  likely_verified: integer (≥ 0)
  ambiguous: integer (≥ 0)
  not_found: integer (≥ 0)
  suspicious: integer (≥ 0)
  processing_error: integer (≥ 0)
}
```

### 7) Purity

The function MUST be pure: no side effects, no external state, deterministic output for a given input.

## Acceptance Criteria

- Given all references are `verified`, the score is 100 and band is `high`
- Given all references are `not_found`, the score is 0 and band is `low`
- Given all references are `likely_verified`, the score is 75 and band is `medium`
- Given all references are `ambiguous`, the score is 25 and band is `low`
- Given all references are `processing_error`, the score is 0 and band is `low`
- Given 0 references analyzed, the score is 0 and band is `low`
- Given a mix of 3 `verified` + 2 `not_found` + 1 `ambiguous` (6 eligible), the score is `round((3×1.0 + 0 + 0.25×1) / 6 × 100)` = `round(54.17)` = 54, band is `medium`
- Given 4 `verified` + 1 `processing_error` (4 eligible), the score is 100 and band is `high`
- The function is testable with unit tests; no DOM or browser dependencies

## Edge Cases

| Scenario | Expected Result |
|----------|-----------------|
| All six counts are 0 | score=0, band="low" |
| Only `processing_error` > 0, all others 0 | score=0, band="low" |
| Single `verified` reference | score=100, band="high" |
| Single `suspicious` reference | score=0, band="low" |
| Large numbers (10000 verified, 1 not_found) | score=100 (rounds from 99.99), band="high" |
| Score lands exactly on boundary (80) | band="high" |
| Score lands exactly on boundary (50) | band="medium" |
| Score lands exactly on boundary (49) | band="low" |

## Integration Points

- Step 03 (Authenticity Score Component) consumes the return value to render the visual display
- Step 07 (Export PDF) uses the same function to include the score in the PDF report
- The function is a standalone utility with no UI framework dependency

## Dependencies

- None (foundational step)
- Consumes `countsByClassification` shape from `spec/results-contract-v1/`
