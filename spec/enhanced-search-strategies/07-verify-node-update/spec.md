# Step 07 — Verify Node Update

## Scope

- Update the verify node to pass all new normalized fields to client `search()` calls
- Update the input state shape documentation

**Out of scope:** Changes to scoring (`compute_match_score()` is unchanged). Changes to classification (Step 09 in langgraph-reference-analysis). Changes to client implementations (Steps 04–06).

## Context

The `verify_single_reference` node in `nodes/verify.py` receives a partial state dict from `Send()` containing the normalized reference, then calls all three API clients sequentially. Currently it only passes `title`, `authors`, `year`, `doi`, and `arxivId` to `client.search()`. The new fields (`issn`, `volume`, `issue`, `pages`, `publisher`) must also be forwarded.

**Existing code:** `apps/worker/biblio_checker_worker/langgraph/nodes/verify.py`

## Requirements

### 1. Updated Input State Shape

The docstring in `verify_single_reference()` must reflect the new fields:

```python
"""
Input state shape::

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
                "issn": str | None,
                "volume": str | None,
                "issue": str | None,
                "pages": str | None,
                "publisher": str | None,
            },
        },
        "warnings": [],
        "verified_references": [],
    }
"""
```

### 2. Updated `client.search()` Calls

Change the search call block (currently lines 119-125) from:

```python
results = client.search(
    title=normalized.get("title"),
    authors=normalized.get("authors", []),
    year=normalized.get("year"),
    doi=normalized.get("doi"),
    arxiv_id=normalized.get("arxivId"),
)
```

To:

```python
results = client.search(
    title=normalized.get("title"),
    authors=normalized.get("authors", []),
    year=normalized.get("year"),
    doi=normalized.get("doi"),
    arxiv_id=normalized.get("arxivId"),
    issn=normalized.get("issn"),
    volume=normalized.get("volume"),
    issue=normalized.get("issue"),
    pages=normalized.get("pages"),
    publisher=normalized.get("publisher"),
)
```

### 3. Updated Logging

Add `has_issn` to the `verify_starting` log event:

```python
logger.info(
    "verify_starting",
    reference_id=reference_id,
    has_doi=normalized.get("doi") is not None,
    has_arxiv_id=normalized.get("arxivId") is not None,
    has_title=normalized.get("title") is not None,
    has_issn=normalized.get("issn") is not None,
)
```

### 4. No Changes to Scoring or Classification

The `compute_match_score()` function (in `scoring.py`) uses only `title`, `authors`, and `year` for similarity scoring. The new fields are used by the API clients for filtering, not for scoring. No changes needed.

The classification engine (in `classification.py`) uses `match_type` and `raw_score` from `MatchCandidate`. The new `"issn_filter"` match type introduced in Step 05 (SciELO) will be treated the same as `"title_fuzzy"` by the classification engine — it uses scoring to determine the match quality.

### 5. No Changes to Error Handling

The existing try/except block around `client.search()` already catches all exceptions generically. New parameters don't change error behavior.

## Acceptance Criteria

- [ ] All 5 new fields are passed to `client.search()` via `normalized.get()`
- [ ] Docstring reflects new fields in input state shape
- [ ] Logging includes `has_issn`
- [ ] Existing error handling is unchanged
- [ ] Scoring and classification logic are unchanged

## Unit Tests

If verify node tests exist, update the mock normalized reference to include new fields:

```python
"normalized": {
    "title": "Example Title",
    "authors": ["Jane Smith"],
    "year": 2020,
    "venue": "Example Journal",
    "doi": "10.1234/example",
    "arxivId": None,
    "issn": "0034-8910",
    "volume": "26",
    "issue": "3",
    "pages": "41-72",
    "publisher": None,
}
```

Verify that the new fields are forwarded to the mocked client's `search()` call.

## Dependencies

- **Depends on:** Steps 04, 05, 06 (client implementations accept new parameters)
- **Informs:** Step 08 (end-to-end validation)
