# Step 10 — Verify Reference Node (Fan-Out Target)

## Scope

- Implement the `verify_single_reference` graph node that verifies one reference against all 3 API sources
- Define the fan-out input contract (what `Send()` passes)
- Define per-reference error isolation
- Integrate API clients (Step 07), scoring (Step 08), and lease renewal (Step 12)

**Out of scope:** Classification logic (Step 09 — handled by `classify_results` node). Fan-out wiring in graph.py (Step 13).

## Context

This node is the fan-out target: LangGraph invokes it once per normalized reference via `Send()`. Each invocation is independent and may run in parallel. The node queries all three API sources, computes similarity scores, and returns the reference enriched with evidence and source error information.

Classification is NOT applied here — it happens in the `classify_results` node (Step 09) after fan-in.

## Requirements

### 1. Node Function — `nodes/verify.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/verify.py`

```python
def verify_single_reference(state: dict) -> dict:
```

**Note:** The input `state` is NOT the full `GraphState` — it's the partial dict from `Send()`:

```python
{
    "job_id": str,
    "reference": {
        "referenceId": str,
        "rawText": str,
        "normalized": {
            "title": str | None,
            "authors": list[str],
            "year": int | None,
            "venue": str | None,
            "doi": str | None,
            "arxivId": str | None,
        },
    },
    "warnings": [],
    "verified_references": [],
}
```

### 2. Verification Flow

1. Extract normalized fields from `state["reference"]["normalized"]`
2. Create API client instances using config settings
3. Query all 3 sources concurrently, collecting results and errors:

```python
candidates: list[MatchCandidate] = []
source_errors: dict[str, str] = {}

for source_name, client in [("openalex", openalex), ("scielo", scielo), ("arxiv", arxiv)]:
    try:
        results = client.search(
            title=normalized["title"],
            authors=normalized["authors"],
            year=normalized["year"],
            doi=normalized["doi"],
            arxiv_id=normalized["arxivId"],
        )
        candidates.extend(results)
    except Exception as exc:
        logger.warning("verify_source_failed", source=source_name, error=str(exc))
        source_errors[source_name] = _safe_error_message(exc)
        # Log warning but continue with other sources
```

4. For candidates from title/metadata searches (not DOI/identifier exact matches), compute `raw_score` using `compute_match_score()` from `scoring.py`:

```python
for candidate in candidates:
    if candidate.match_type not in ("doi_exact", "identifier_exact"):
        score = compute_match_score(
            ref_title=normalized["title"],
            ref_authors=normalized["authors"],
            ref_year=normalized["year"],
            candidate_title=candidate.title,
            candidate_authors=candidate.authors,
            candidate_year=candidate.year,
        )
        # Replace raw_score on the candidate
        candidate = dataclasses.replace(candidate, raw_score=score)
```

5. Build the verified reference dict:

```python
verified_ref = {
    **state["reference"],  # referenceId, rawText, normalized
    "candidates": [asdict(c) for c in candidates],
    "source_errors": source_errors,
}
```

6. Return accumulated results:

```python
return {
    "verified_references": [verified_ref],
    "warnings": warnings,
}
```

### 2b. Error Message Sanitization

To prevent raw exception messages (which may contain internal URLs, credentials hints, or other sensitive data) from appearing in user-facing warnings, use the following helper when recording source errors:

```python
def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection_failed"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http_{exc.response.status_code}"
    return "unexpected_error"
```

In the source-level error loop (Section 2), replace `str(exc)` with `_safe_error_message(exc)` when recording into `source_errors` and into user-facing warning messages. The full `str(exc)` MUST still be passed to `logger.warning("verify_source_failed", ...)` for structured log output.

### 3. Per-Reference Error Isolation

If the ENTIRE verification fails for a reference (e.g., all 3 sources raise exceptions), the node MUST NOT raise. Instead, it returns a `processing_error` result:

```python
try:
    # ... verification logic ...
except Exception as exc:
    logger.exception("verify_reference_failed", reference_id=reference_id)
    return {
        "verified_references": [{
            **state["reference"],
            "candidates": [],
            "source_errors": {"all": str(exc)},
            "classification": "processing_error",
            "confidenceScore": None,
            "confidenceBand": None,
            "manualReviewRequired": True,
            "reasonCode": "reference_processing_failure",
            "decisionReason": "Ocurrió un error interno al procesar esta referencia.",
            "evidence": [],
        }],
        "warnings": [{
            "code": "reference_verification_failed",
            "message": f"La verificación de la referencia {reference_id} falló completamente.",
            "referenceId": reference_id,
            "details": None,
        }],
    }
```

### 4. Source Timeout Warnings

If one or more sources fail but others succeed, add a warning per failed source. The `error` value in `source_errors` is already sanitized via `_safe_error_message()` (see Section 2b):

```python
for source, error in source_errors.items():
    warnings.append({
        "code": "source_timeout_partial",
        "message": f"La fuente {source} no respondió correctamente: {error}",
        "referenceId": reference_id,
        "details": None,
    })
```

### 5. Lease Renewal

Before starting API calls, renew the worker lease (Step 12):

```python
from biblio_checker_worker.langgraph.lease import renew_lease_if_needed

renew_lease_if_needed()
```

`renew_lease_if_needed()` takes no arguments — it reads job context from the module-level context initialized by `flow.py` (Step 12). This prevents the lease from expiring during potentially slow API calls.

### 6. API Client Lifecycle

Create client instances at the start of each invocation. Close them at the end:

```python
settings = get_settings()
openalex = OpenAlexClient(timeout=settings.api_timeout_seconds, email=settings.openalex_email)
scielo = ScieloClient(timeout=settings.api_timeout_seconds)
arxiv = ArxivClient(timeout=settings.api_timeout_seconds)

try:
    # ... search logic ...
finally:
    openalex.close()
    scielo.close()
    arxiv.close()
```

### 7. Logging

Logger name: `"biblio_checker_worker.langgraph.nodes.verify"`

- INFO: `"verify_starting"` with `reference_id`, `has_doi`, `has_arxiv_id`, `has_title`
- INFO: `"verify_complete"` with `reference_id`, `candidates_found`, `sources_failed`
- WARNING: `"verify_source_failed"` per source that errored
- ERROR: `"verify_reference_failed"` if entire verification fails (before returning processing_error)

## Acceptance Criteria

- [ ] Node receives partial state from `Send()` (not full `GraphState`)
- [ ] Queries all 3 API sources for each reference
- [ ] Computes `raw_score` using `compute_match_score()` for non-exact matches
- [ ] Returns `{"verified_references": [dict], "warnings": list[dict]}`
- [ ] Per-source failures don't crash the node — other sources are still queried
- [ ] Total verification failure returns `processing_error` classification (not an exception)
- [ ] Source timeout warnings are added to the warnings list
- [ ] Lease is renewed before API calls
- [ ] API clients are properly closed after use
- [ ] Unit tests with mocked API clients cover: all sources succeed, one source fails, all sources fail, no candidates found

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Reference has DOI — OpenAlex finds it, SciELO and arXiv don't | Return OpenAlex candidate. No errors for SciELO/arXiv (404 is empty list, not an error). |
| All 3 sources timeout | Per-reference error isolation: return `processing_error` result, not an exception. |
| Reference has no title, no DOI, no arXiv ID | Sources may return empty results. Scoring returns 0.0. Classification (Step 09) handles this as `insufficient_metadata`. |
| OpenAlex returns 5 candidates, arXiv returns 2 | All 7 candidates are merged into the candidates list. Classification picks the best. |
| One source returns very slowly (25+ seconds) | Timeout from `API_TIMEOUT_SECONDS` config. Source error is logged, others proceed. |

## Dependencies

- **Depends on:** Step 07 (API clients), Step 08 (scoring), Step 12 (lease renewal), Step 01 (schemas: `MatchCandidate`)
- **Informs:** Step 09 (classify_results processes the output of this node)
