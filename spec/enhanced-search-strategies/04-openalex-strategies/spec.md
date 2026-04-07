# Step 04 — OpenAlex Search Strategies

## Scope

- Expand `OpenAlexClient.search()` from 3 strategies to 6
- Add new parameters: `issn`, `volume`, `issue`, `year` (as filters)
- Use combined OpenAlex filters (`filter=X,Y,Z`) for precise multi-field queries

**Out of scope:** SciELO (Step 05). arXiv (Step 06). Changes to response parsing (existing `_parse_work()` is unchanged).

## Context

OpenAlex is the most comprehensive repository — it indexes scholarly works across journals, books, conferences, and preprints. Its `/works` endpoint supports combining multiple filters (title, author, year, ISSN, volume, issue) in a single query with comma-separated syntax. Currently only 3 strategies are implemented (DOI, title, author+title). We need to use the additional filter capabilities to produce more precise matches.

**Existing code:** `apps/worker/biblio_checker_worker/langgraph/clients/openalex.py`

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

New parameters have `= None` defaults for backward compatibility. `pages` and `publisher` are accepted but not used by OpenAlex (reserved for future use or other clients sharing the interface).

### 2. Search Strategies (6, in priority order)

#### Strategy 1: DOI Lookup (unchanged)

- **Condition:** `doi is not None` and valid DOI format
- **Request:** `GET /works/https://doi.org/{encoded_doi}`
- **Match type:** `doi_exact`, `raw_score=1.0`
- **If found:** return immediately

#### Strategy 2: Title + Author + Year (NEW)

- **Condition:** `title is not None` and `authors` is non-empty and `year is not None`
- **Request:** `GET /works?filter=title.search:{title},raw_author_name.search:{first_author},publication_year:{year}&per_page=5`
- **Match type:** `metadata_partial`, `raw_score=0.0`
- **Rationale:** The combination of all three metadata fields is highly specific and produces few false positives. This is the strongest metadata-based strategy.
- **If found:** return immediately

#### Strategy 3: ISSN + Volume (NEW)

- **Condition:** `issn is not None` and `volume is not None`
- **Request:** `GET /works?filter=primary_location.source.issn:{issn},biblio.volume:{volume}&per_page=5`
- **Match type:** `metadata_partial`, `raw_score=0.0`
- **Rationale:** ISSN+volume narrows results to a specific journal issue. Combined with downstream scoring (title/author similarity), this is very precise.
- **If found:** return immediately

#### Strategy 4: Title + Year (NEW)

- **Condition:** `title is not None` and `year is not None`
- **Request:** `GET /works?filter=title.search:{title},publication_year:{year}&per_page=5`
- **Match type:** `title_fuzzy`, `raw_score=0.0`
- **Rationale:** Year filter eliminates papers with similar titles from different years.
- **If found:** return immediately

#### Strategy 5: Title + Author (existing, renumbered)

- **Condition:** `title is not None` and `authors` is non-empty
- **Request:** `GET /works?filter=title.search:{title},raw_author_name.search:{first_author}&per_page=5`
- **Match type:** `metadata_partial`, `raw_score=0.0`
- **If found:** return immediately

#### Strategy 6: Title Only (existing, renumbered)

- **Condition:** `title is not None`
- **Request:** `GET /works?filter=title.search:{title}&per_page=5`
- **Match type:** `title_fuzzy`, `raw_score=0.0`
- **Fallback:** last resort

### 3. Implementation of New Methods

Add two private methods for the new strategies:

```python
def _title_author_year_search(self, title: str, first_author: str, year: int) -> list[MatchCandidate]:
    filter_value = f"title.search:{title},raw_author_name.search:{first_author},publication_year:{year}"
    response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return self._parse_results_page(response, match_type="metadata_partial", raw_score=0.0)

def _issn_volume_search(self, issn: str, volume: str) -> list[MatchCandidate]:
    filter_value = f"primary_location.source.issn:{issn},biblio.volume:{volume}"
    response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return self._parse_results_page(response, match_type="metadata_partial", raw_score=0.0)

def _title_year_search(self, title: str, year: int) -> list[MatchCandidate]:
    filter_value = f"title.search:{title},publication_year:{year}"
    response = self._client.get("/works", params={"filter": filter_value, "per_page": 5})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return self._parse_results_page(response, match_type="title_fuzzy", raw_score=0.0)
```

### 4. Updated `search()` Method Flow

```python
def search(self, *, title, authors, year, doi, arxiv_id, issn=None, volume=None, issue=None, pages=None, publisher=None):
    # Strategy 1: DOI lookup
    if doi is not None and _validate_doi(doi):
        result = self._doi_lookup(doi)
        if result: return result

    # Strategy 2: Title + Author + Year
    if title is not None and authors and year is not None:
        result = self._title_author_year_search(title, authors[0], year)
        if result: return result

    # Strategy 3: ISSN + Volume
    if issn is not None and volume is not None:
        result = self._issn_volume_search(issn, volume)
        if result: return result

    # Strategy 4: Title + Year
    if title is not None and year is not None:
        result = self._title_year_search(title, year)
        if result: return result

    # Strategy 5: Title + Author
    if title is not None and authors:
        result = self._author_title_search(title, authors[0])
        if result: return result

    # Strategy 6: Title only
    if title is not None:
        result = self._title_search(title)
        if result: return result

    return []
```

### 5. Logging

All new strategies follow the existing logging pattern:

```python
logger.info("search_starting", source="openalex", strategy="title_author_year_search", title=title, first_author=authors[0], year=year)
# ... execute ...
logger.info("search_complete", source="openalex", candidates_found=len(result))
```

## Acceptance Criteria

- [ ] `search()` accepts new parameters: `issn`, `volume`, `issue`, `pages`, `publisher`
- [ ] 6 strategies execute in documented priority order
- [ ] Strategy 2 (title+author+year) uses combined filter with `publication_year`
- [ ] Strategy 3 (ISSN+volume) uses `primary_location.source.issn` and `biblio.volume`
- [ ] Strategy 4 (title+year) uses combined filter with `publication_year`
- [ ] Each strategy short-circuits: if results found, return immediately
- [ ] All new strategies reuse existing `_parse_results_page()` method
- [ ] Error handling (404, 429, 500) is consistent with existing strategies
- [ ] Logging follows existing pattern for all new strategies

## Unit Tests

Add to `apps/worker/tests/test_client_openalex.py`:

```python
class TestOpenAlexTitleAuthorYearSearch:
    def test_returns_candidates_when_all_three_provided(self):
        # title search and author+title search return empty → falls through to title+author+year
        # title+author+year returns results

    def test_skipped_when_year_is_none(self):
        # Only title+author are provided → skips strategy 2, goes to strategy 5

class TestOpenAlexIssnVolumeSearch:
    def test_returns_candidates_with_issn_and_volume(self):
        # DOI fails, title+author+year fails → falls through to ISSN+volume

    def test_skipped_when_issn_is_none(self):
        # No ISSN → skips strategy 3

class TestOpenAlexTitleYearSearch:
    def test_returns_candidates_with_title_and_year(self):
        # Higher strategies fail → falls through to title+year
```

All existing tests must add `issn=None, volume=None, issue=None, pages=None, publisher=None` to their `client.search()` calls.

## Dependencies

- **Depends on:** Step 02 (new fields in normalized reference)
- **Informs:** Step 07 (verify node passes new fields), Step 08 (Postman validation)
