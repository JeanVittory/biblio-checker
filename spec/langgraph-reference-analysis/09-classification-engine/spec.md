# Step 09 — Classification Engine

## Scope

- Implement the deterministic classification engine that assigns a classification to each reference based on collected evidence
- Define the decision algorithm (priority-ordered rules)
- Define the `decisionReason` Spanish-language templates
- Enforce the compatibility matrix from ResultsV1

**Out of scope:** Evidence collection (Step 10). Report assembly (Step 11). API client calls (Step 07).

## Context

After the `verify_single_reference` node collects `MatchCandidate` results from all three APIs, the classification engine determines what classification to assign. This is purely deterministic logic — no LLM is involved.

The compatibility matrix is defined in `apps/backend/app/schemas/results.py:43-57` and is copied to the worker in `langgraph/schemas.py` (Step 01). The engine MUST produce results that pass the `ReferenceResult` Pydantic validator.

## Requirements

### 1. Classification Module — `langgraph/classification.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/classification.py`

### 2. Main Classification Function

```python
def classify_reference(
    *,
    normalized: dict,
    candidates: list[MatchCandidate],
    source_errors: dict[str, str],
) -> dict:
    """Classify a reference based on evidence from API lookups.

    Args:
        normalized: The normalized reference metadata {title, authors, year, venue, doi, arxivId}
        candidates: All MatchCandidate objects from all sources
        source_errors: Map of source -> error message for sources that failed/timed out

    Returns:
        dict with keys: classification, confidenceScore, confidenceBand,
                        manualReviewRequired, reasonCode, decisionReason, evidence
    """
```

### 3. Decision Algorithm (priority order)

The engine evaluates rules in this order. The **first matching rule** determines the classification:

#### Rule 1: Exact DOI Match → `verified`
**Condition:** `doi` is present in normalized AND a candidate has `match_type="doi_exact"` AND the candidate's metadata (title or year) is consistent with the reference.

```python
classification = "verified"
confidence_score = 0.95
confidence_band = "very_high"
manual_review_required = False
reason_code = "exact_doi_match"
decision_reason = "El DOI coincide exactamente con un registro canónico en {source}."
```

#### Rule 2: Exact Identifier Match → `verified`
**Condition:** `arxivId` is present AND a candidate has `match_type="identifier_exact"` AND metadata is consistent.

```python
classification = "verified"
confidence_score = 0.93
confidence_band = "very_high"
manual_review_required = False
reason_code = "exact_identifier_match"
decision_reason = "El identificador arXiv coincide exactamente con un registro en arXiv."
```

#### Rule 3: DOI Conflict → `suspicious`
**Condition:** `doi` is present AND a candidate has `match_type="doi_exact"` BUT the candidate's title or year is significantly different from the reference (title_similarity < 0.5 OR year differs by > 2).

```python
classification = "suspicious"
confidence_score = 0.90
confidence_band = "high"
manual_review_required = True
reason_code = "strong_doi_conflict"
decision_reason = "El DOI citado apunta a un trabajo incompatible con el título o año reportados. Esto puede indicar una referencia fabricada."
```

#### Rule 4: Cross-Source Metadata Conflict → `suspicious`
**Condition:** Two or more sources return candidates with high title similarity (>= 0.85) to the reference BUT with conflicting metadata (different year by > 2, or different DOI).

```python
classification = "suspicious"
confidence_score = 0.85
confidence_band = "high"
manual_review_required = True
reason_code = "cross_source_metadata_conflict"
decision_reason = "Múltiples fuentes encontraron trabajos similares pero con metadatos contradictorios entre sí."
```

#### Rule 5: Strong Metadata Match → `likely_verified`
**Condition:** No DOI/identifier available, but at least one candidate has `raw_score >= 0.85`.

```python
classification = "likely_verified"
confidence_score = best_score  # the highest raw_score
confidence_band = "high" if best_score >= 0.90 else "medium"
manual_review_required = False
reason_code = "strong_metadata_match"
decision_reason = "Se encontró una coincidencia fuerte por título y autores en {source}, aunque sin identificador canónico."
```

#### Rule 5b: Single Moderate Match → `ambiguous`
**Condition:** Exactly one candidate with `raw_score` between 0.50 and 0.84. No DOI/identifier match. No other candidates above 0.50.

```python
classification = "ambiguous"
confidence_score = best_score
confidence_band = "medium" if best_score >= 0.65 else "low"
manual_review_required = True
reason_code = "single_moderate_match"
decision_reason = "Se encontró un candidato con coincidencia moderada, pero no suficiente para confirmar la referencia."
```

#### Rule 6: Multiple Plausible Candidates → `ambiguous`
**Condition:** Multiple candidates from one or more sources with `raw_score` between 0.50 and 0.85, and no single candidate clearly dominates (top two scores within 0.15 of each other).

```python
classification = "ambiguous"
confidence_score = best_score
confidence_band = "medium" if best_score >= 0.65 else "low"
manual_review_required = True
reason_code = "multiple_plausible_candidates"
decision_reason = "Se encontraron múltiples candidatos plausibles pero ninguno es lo suficientemente concluyente."
```

#### Rule 7: Insufficient Metadata → `not_found`
**Condition:** The normalized reference has `title` is `None` AND `doi` is `None` AND `arxivId` is `None` (not enough data to search meaningfully).

```python
classification = "not_found"
confidence_score = 0.10
confidence_band = "very_low"
manual_review_required = True
reason_code = "insufficient_metadata"
decision_reason = "La referencia no contiene metadatos suficientes (título, DOI o identificador) para realizar una búsqueda confiable."
```

#### Rule 8: No Match in Any Source → `not_found`
**Condition:** All sources returned 0 candidates (or all candidates have `raw_score < 0.50`).

```python
classification = "not_found"
confidence_score = 0.15
confidence_band = "low" if len(source_errors) == 0 else "very_low"
manual_review_required = True
reason_code = "no_match_any_source"
decision_reason = "No se encontraron coincidencias en ninguna fuente consultada (OpenAlex, SciELO, arXiv)."
```

#### Rule 9: Source Timeout with Partial Evidence → use partial evidence
**Condition:** One or more sources timed out (`source_errors` is non-empty) but other sources returned usable evidence.

Apply rules 1–8 using the available evidence. The classification is determined by whatever evidence exists. Add a `source_timeout_partial` reason code ONLY if no other rule matches and all available sources returned no results.

```python
# Only when remaining sources had no usable matches:
classification = "not_found"
confidence_score = 0.10
confidence_band = "very_low"
manual_review_required = True
reason_code = "source_timeout_partial"
decision_reason = "Algunas fuentes no respondieron a tiempo. Los resultados pueden ser incompletos."
```

#### Rule 10: Processing Error (fallback)
**Condition:** This is NOT applied by the classification engine. It is applied by the `verify_single_reference` node (Step 10) when the entire verification for a reference fails.

```python
classification = "processing_error"
confidence_score = None
confidence_band = None
manual_review_required = True
reason_code = "reference_processing_failure"
decision_reason = "Ocurrió un error interno al procesar esta referencia."
```

### 4. Evidence Assembly

The classification function also builds the `evidence` list for the `ReferenceResult`:

```python
evidence = []
for candidate in candidates:
    if candidate.raw_score >= 0.50 or candidate.match_type in ("doi_exact", "identifier_exact"):
        evidence.append({
            "source": candidate.source,
            "matchType": candidate.match_type,
            "score": candidate.raw_score,
            "matchedRecord": {
                "externalId": candidate.external_id,
                "title": candidate.title,
                "year": candidate.year,
                "doi": candidate.doi,
                "url": candidate.url,
            },
        })
```

Only candidates with meaningful scores (>= 0.50) or exact matches are included in evidence. Low-scoring candidates are filtered out to keep the evidence list concise.

### 5. Compatibility Matrix Enforcement

The returned dict MUST satisfy the `ReferenceResult` Pydantic validator:

| Classification | Valid `confidenceBand` | `manualReviewRequired` |
|---------------|----------------------|----------------------|
| `verified` | `high`, `very_high` | `false` |
| `likely_verified` | `medium`, `high` | `false` |
| `ambiguous` | `low`, `medium` | `true` |
| `not_found` | `very_low`, `low` | `true` |
| `suspicious` | `medium`, `high`, `very_high` | `true` |
| `processing_error` | `null` | `true` |

The engine MUST NOT produce combinations outside this matrix.

### 6. Classify Node — `nodes/classify.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/classify.py`

```python
def classify_results(state: GraphState) -> dict:
```

**Behavior:**
1. Read `state["verified_references"]`
2. For each reference, call `classify_reference()` with its candidates and source errors
3. Enrich each reference dict with classification fields
4. Return `{"classified_references": enriched_list}`

**Note:** This node writes to `classified_references` (a plain list field with no reducer), NOT back to `verified_references`. Writing to `verified_references` would trigger the `operator.add` reducer and concatenate results with the existing fan-in accumulation, producing 2N items. `classified_references` is a plain field written once after fan-in completes.

## Acceptance Criteria

- [ ] `classify_reference()` returns a dict with all 7 classification fields
- [ ] Rules are evaluated in priority order (1–10)
- [ ] DOI exact match → `verified` with `very_high` confidence
- [ ] DOI conflict (DOI found but metadata mismatch) → `suspicious`
- [ ] Strong metadata match (score >= 0.85) → `likely_verified`
- [ ] Multiple plausible candidates → `ambiguous`
- [ ] Insufficient metadata → `not_found` with `insufficient_metadata`
- [ ] No matches from any source → `not_found` with `no_match_any_source`
- [ ] All `decisionReason` strings are in Spanish
- [ ] Evidence list includes only candidates with score >= 0.50 or exact matches
- [ ] Output satisfies the compatibility matrix (validated by `ReferenceResult` Pydantic model)
- [ ] Unit tests cover all 10 rules with specific input scenarios

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| DOI match found but title similarity is 0.3 | Rule 3 triggers → `suspicious` (DOI conflict) |
| Single candidate with score 0.92 | Rule 5 triggers → `likely_verified` |
| Two candidates with scores 0.75 and 0.72 | Rule 6 triggers → `ambiguous` (within 0.15 of each other) |
| Two candidates with scores 0.90 and 0.60 | Rule 5 triggers → `likely_verified` (0.90 dominates) |
| All 3 sources returned errors | Rule 9 applies → `not_found` with `source_timeout_partial` |
| No DOI, no title, no arXiv ID | Rule 7 → `not_found` with `insufficient_metadata` |
| Reference has DOI, DOI lookup returns 404 from all sources | Rule 8 → `not_found` with `no_match_any_source` |

## Dependencies

- **Depends on:** Step 01 (schemas: `MatchCandidate`, `Classification`, `ReasonCode`), Step 08 (scoring thresholds)
- **Informs:** Step 10 (verify node feeds candidates to classifier), Step 11 (assemble uses classified references)
