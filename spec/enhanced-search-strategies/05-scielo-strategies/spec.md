# Step 05 — SciELO Search Strategies

## Scope

- Replace the broken title search strategy with a working ISSN-based search
- Add `issn` parameter to `ScieloClient.search()`
- Remove the non-functional `_title_search()` method

**Out of scope:** OpenAlex (Step 04). arXiv (Step 06). Changes to article parsing (`_parse_article()` is unchanged).

## Context

SciELO ArticleMeta's `/article/identifiers/` endpoint does NOT support the `title` parameter — it is silently ignored and returns all 1.3M articles unfiltered. This was confirmed via Postman testing. However, the same endpoint DOES support the `issn` parameter, which correctly filters to articles from a specific journal (validated: `?issn=0034-8910` returned 11,172 filtered results).

SciELO is specialized for Latin American and Iberian scholarly journals. It is most useful when the reference is to a journal article from a Latin American publication. Since most such references include a journal name (venue) but rarely include explicit ISSN, the ISSN search is useful only when the LLM can extract an ISSN from the reference text or when it is explicitly present.

**Existing code:** `apps/worker/biblio_checker_worker/langgraph/clients/scielo.py`

## Requirements

### 1. Updated `search()` Signature

```python
def search(
    self,
    *,
    title: str | None,
    authors: list[str],
    year: int | None,
    doi: str | None,
    arxiv_id: str | None,
    issn: str | None = None,
    volume: str | None = None,
    issue: str | None = None,
    pages: str | None = None,
    publisher: str | None = None,
) -> list[MatchCandidate]:
```

Parameters `title`, `authors`, `year`, `arxiv_id`, `volume`, `issue`, `pages`, and `publisher` are accepted for interface compatibility but are NOT used by SciELO (its API does not support filtering by these fields).

### 2. Search Strategies (2, in priority order)

#### Strategy 1: DOI Lookup (unchanged)

- **Condition:** `doi is not None` and valid DOI format
- **Request:** `GET /article/?doi={doi}`
- **Match type:** `doi_exact`, `raw_score=1.0`
- **If found:** return immediately

#### Strategy 2: ISSN Search (NEW — replaces broken title search)

- **Condition:** `issn is not None`
- **Request:** `GET /article/identifiers/?issn={issn}&limit=5`
- **Response:** `{"meta": {...}, "objects": [{"code": "S...", "collection": "scl"}, ...]}`
- **Second step:** For each PID in `objects`, call `GET /article/?code={pid}&collection={collection}` to get full metadata
- **Match type:** `issn_filter`, `raw_score=0.0`
- **Rationale:** ISSN filtering narrows to articles from a specific journal. The scoring engine (Step 08) then evaluates title/author/year similarity to find the best match.

### 3. Remove `_title_search()` Method

Delete the `_title_search()` method entirely. It:
- Calls `GET /article/identifiers/?title={title}&limit=5`
- The `title` parameter is silently ignored by the SciELO API
- Returns essentially random articles, leading to false matches

### 4. Implement `_issn_search()` Method

```python
def _issn_search(self, issn: str) -> list[MatchCandidate]:
    logger.debug("search_request", source="scielo", url=f"{self._client.base_url}/article/identifiers/", params={"issn": issn, "limit": 5})
    response = self._client.get("/article/identifiers/", params={"issn": issn, "limit": 5})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    try:
        data = response.json()
    except Exception:
        logger.warning("search_parse_error", source="scielo", strategy="issn_search", detail="malformed JSON")
        return []
    if not isinstance(data, dict):
        logger.warning("search_parse_error", source="scielo", strategy="issn_search", detail="unexpected response shape")
        return []
    objects: list[Any] = data.get("objects", [])
    if not isinstance(objects, list):
        logger.warning("search_parse_error", source="scielo", strategy="issn_search", detail="objects field not a list")
        return []

    candidates: list[MatchCandidate] = []
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        pid = obj.get("code", "")
        collection = obj.get("collection", "")
        if not pid:
            continue
        candidate = self._fetch_article_by_pid(pid, collection)
        if candidate is not None:
            candidates.append(candidate)

    return candidates
```

Note: This method reuses the existing `_fetch_article_by_pid()` method, but calls it with `match_type="issn_filter"` instead of `"title_fuzzy"`. Update `_fetch_article_by_pid` to accept `match_type` as a parameter:

```python
def _fetch_article_by_pid(self, pid: str, collection: str, match_type: str = "title_fuzzy") -> MatchCandidate | None:
    # ... existing code ...
    return _parse_article(data, match_type=match_type, raw_score=0.0)
```

Then call from `_issn_search`:
```python
candidate = self._fetch_article_by_pid(pid, collection, match_type="issn_filter")
```

### 5. Updated `search()` Method Flow

```python
def search(self, *, title, authors, year, doi, arxiv_id, issn=None, volume=None, issue=None, pages=None, publisher=None):
    # Strategy 1: DOI lookup
    if doi is not None:
        if not _validate_doi(doi):
            logger.debug("search_request", source="scielo", strategy="doi_lookup", skipped=True, reason="invalid_doi_format")
        else:
            result = self._doi_lookup(doi)
            if result: return result

    # Strategy 2: ISSN search (replaces broken title search)
    if issn is not None:
        logger.info("search_starting", source="scielo", strategy="issn_search", issn=issn)
        result = self._issn_search(issn)
        logger.info("search_complete", source="scielo", candidates_found=len(result))
        return result

    logger.info("search_complete", source="scielo", candidates_found=0)
    return []
```

### 6. API Response Examples

**ISSN identifiers** (`GET /article/identifiers/?issn=0034-8910&limit=3`):
```json
{
  "meta": {
    "limit": 3,
    "offset": 0,
    "filter": {
      "issn": "0034-8910",
      "processing_date": {"$gte": "1900-01-01", "$lte": "2026-03-28"}
    },
    "total": 11172
  },
  "objects": [
    {"code": "S0034-89102000000500018", "collection": "spa", "processing_date": "2001-08-06"},
    {"code": "S0034-89102000000300015", "collection": "spa", "processing_date": "2001-08-06"},
    {"code": "S0034-89102000000200015", "collection": "spa", "processing_date": "2001-08-06"}
  ]
}
```

**Article fetch** (`GET /article/?code=S0034-89102000000500018&collection=spa`):
```json
{
  "code": "S0034-89102000000500018",
  "collection": "spa",
  "article": {
    "v12": [{"_": "Example Article Title"}],
    "v10": [{"n": "Hillegonda Maria D", "s": "Novaes"}],
    "v65": [{"_": "20001000"}],
    "v880": [{"_": "S0034-89102000000500018"}]
  }
}
```

## Acceptance Criteria

- [ ] `_title_search()` method is removed entirely
- [ ] `_issn_search()` method implements the two-step search (identifiers → fetch per PID)
- [ ] `search()` strategy 2 is ISSN-based, not title-based
- [ ] `_fetch_article_by_pid()` accepts `match_type` parameter
- [ ] ISSN search candidates have `match_type="issn_filter"`
- [ ] `search()` accepts all new parameters for interface compatibility
- [ ] Logging follows existing pattern for the new strategy
- [ ] Error handling: malformed JSON, empty objects list, PID fetch 404 — all handled gracefully

## Unit Tests

**File:** `apps/worker/tests/test_client_scielo.py`

Remove `TestScieloTitleSearch` class entirely. Add:

```python
class TestScieloIssnSearch:
    def test_issn_search_returns_candidates(self):
        """ISSN search returns identifiers, then fetches each article."""
        identifiers_body = {
            "objects": [
                {"code": "S0034-89102000000500018", "collection": "spa"},
            ]
        }
        article = _article_fixture(code="S0034-89102000000500018")
        responses = iter([
            _mock_response(200, json_body=identifiers_body),
            _mock_response(200, json_body=article),
        ])
        client = _make_client()
        with patch.object(client._client, "get", side_effect=lambda *a, **k: next(responses)):
            results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id=None, issn="0034-8910")
        assert len(results) == 1
        assert results[0].match_type == "issn_filter"

    def test_issn_search_empty_objects_returns_empty(self):
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body={"objects": []})):
            results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id=None, issn="9999-9999")
        assert results == []

    def test_issn_search_pid_not_found_skips(self):
        identifiers_body = {"objects": [{"code": "S_MISSING", "collection": "scl"}]}
        responses = iter([
            _mock_response(200, json_body=identifiers_body),
            _mock_response(404),
        ])
        client = _make_client()
        with patch.object(client._client, "get", side_effect=lambda *a, **k: next(responses)):
            results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id=None, issn="0034-8910")
        assert results == []

    def test_no_issn_and_no_doi_returns_empty(self):
        """Without DOI or ISSN, SciELO cannot search."""
        client = _make_client()
        results = client.search(title="Some Title", authors=["Smith"], year=2020, doi=None, arxiv_id=None, issn=None)
        assert results == []
```

Update ALL existing tests to add `issn=None` (and other new params) to `client.search()` calls.

Update `test_invalid_doi_format_skips_doi_lookup` — with title search removed, the fallthrough now returns empty if no ISSN is provided.

## Dependencies

- **Depends on:** Step 02 (new fields), Step 03 (validated ISSN)
- **Informs:** Step 07 (verify node passes ISSN to SciELO), Step 08 (Postman validates ISSN search)
