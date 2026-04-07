# Step 06 — arXiv Search Strategies

## Scope

- Add title+author combined search strategy using arXiv boolean operators
- Add new parameters to `ArxivClient.search()` for interface compatibility
- Existing strategies remain unchanged

**Out of scope:** OpenAlex (Step 04). SciELO (Step 05). Changes to XML parsing (`_parse_entry()` and `_parse_feed()` are unchanged).

## Context

The arXiv API supports boolean operators (`AND`, `OR`, `ANDNOT`) to combine search prefixes. Currently only `ti:` (title) and `doi:` searches are implemented separately. Adding a combined `ti:"{title}"+AND+au:{author}` search significantly improves precision for preprint references that include an author name but no DOI or arXiv ID.

**Existing code:** `apps/worker/biblio_checker_worker/langgraph/clients/arxiv.py`

**arXiv search prefixes (from API documentation):**

| Prefix | Field | Currently used |
|--------|-------|----------------|
| `ti:` | Title | yes |
| `au:` | Author | **no** (adding in this step) |
| `abs:` | Abstract | no |
| `co:` | Comment | no |
| `jr:` | Journal reference | no |
| `cat:` | Subject category | no |
| `all:` | All fields | no |

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

Parameters `issn`, `volume`, `issue`, `pages`, and `publisher` are accepted for interface compatibility but are NOT used by arXiv (its API does not support these filters).

### 2. Search Strategies (4, in priority order)

#### Strategy 1: arXiv ID Lookup (unchanged)

- **Condition:** `arxiv_id is not None` and valid format
- **Request:** `GET /query?id_list={arxiv_id}`
- **Match type:** `identifier_exact`, `raw_score=1.0`

#### Strategy 2: DOI Search (unchanged)

- **Condition:** `doi is not None` and valid DOI format
- **Request:** `GET /query?search_query=doi:{doi}&max_results=1`
- **Match type:** `doi_exact`, `raw_score=1.0`

#### Strategy 3: Title + Author Search (NEW)

- **Condition:** `title is not None` and `authors` is non-empty
- **Request:** `GET /query?search_query=ti:"{title}"+AND+au:{first_author_surname}&max_results=5`
- **Match type:** `metadata_partial`, `raw_score=0.0`
- **Rationale:** Combining title and author significantly reduces false positives compared to title-only search. The `au:` prefix matches on author surnames.

**Author name handling:**
- Use only the first author from the `authors` list
- Extract the surname (last word of the name, or the part before the comma if format is "Surname, Name")
- URL-encode special characters

#### Strategy 4: Title Only Search (existing, renumbered)

- **Condition:** `title is not None`
- **Request:** `GET /query?search_query=ti:"{title}"&max_results=5`
- **Match type:** `title_fuzzy`, `raw_score=0.0`

### 3. Implement `_title_author_search()` Method

```python
def _title_author_search(self, title: str, first_author: str) -> list[MatchCandidate]:
    # Extract surname from author name
    surname = self._extract_surname(first_author)
    search_query = f'ti:"{title}" AND au:{surname}'
    logger.debug("search_request", source="arxiv", url=f"{self._client.base_url}/query", params={"search_query": search_query, "max_results": 5})
    response = self._client.get("/query", params={"search_query": search_query, "max_results": 5})
    if response.status_code == 404:
        return []
    response.raise_for_status()
    try:
        return _parse_feed(response.text, match_type="metadata_partial", raw_score=0.0)
    except ValueError:
        logger.warning("search_parse_error", source="arxiv", strategy="title_author_search", detail="XML parse error")
        return []
```

### 4. Surname Extraction Helper

```python
@staticmethod
def _extract_surname(author_name: str) -> str:
    """Extract the surname from an author name for arXiv search.

    Handles common formats:
    - 'Smith, J.' → 'Smith'
    - 'John Smith' → 'Smith'
    - 'García Márquez, Gabriel' → 'García Márquez'  (but arXiv may only match 'Márquez')
    - 'L. Martínez' → 'Martínez'
    """
    author_name = author_name.strip()
    if "," in author_name:
        # Format: "Surname, Given" → take everything before the first comma
        return author_name.split(",")[0].strip()
    # Format: "Given Surname" → take the last word
    parts = author_name.split()
    return parts[-1] if parts else author_name
```

### 5. Updated `search()` Method Flow

```python
def search(self, *, title, authors, year, doi, arxiv_id, issn=None, volume=None, issue=None, pages=None, publisher=None):
    self._request_count = 0

    # Strategy 1: arXiv ID lookup
    if arxiv_id is not None:
        if not _validate_arxiv_id(arxiv_id):
            logger.debug(...)
        else:
            self._throttle()
            result = self._id_lookup(arxiv_id)
            if result: return result

    # Strategy 2: DOI search
    if doi is not None:
        if not _validate_doi(doi):
            logger.debug(...)
        else:
            self._throttle()
            result = self._doi_search(doi)
            if result: return result

    # Strategy 3: Title + Author search (NEW)
    if title is not None and authors:
        self._throttle()
        logger.info("search_starting", source="arxiv", strategy="title_author_search", title=title, first_author=authors[0])
        result = self._title_author_search(title, authors[0])
        logger.info("search_complete", source="arxiv", candidates_found=len(result))
        if result: return result

    # Strategy 4: Title only search
    if title is not None:
        self._throttle()
        result = self._title_search(title)
        return result

    return []
```

### 6. Throttling

The existing 3-second throttle (`self._throttle()`) applies to the new strategy as well. The `_request_count` is reset at the start of each `search()` call.

## Acceptance Criteria

- [ ] `search()` accepts all new parameters for interface compatibility
- [ ] Strategy 3 (title+author) uses `ti:"{title}" AND au:{surname}` syntax
- [ ] `_extract_surname()` handles "Surname, Given" and "Given Surname" formats
- [ ] Strategy 3 is tried before title-only (Strategy 4)
- [ ] Strategy 3 candidates have `match_type="metadata_partial"`
- [ ] Throttle is applied before the new strategy
- [ ] Existing strategies (ID lookup, DOI, title-only) are unchanged
- [ ] XML parsing is unchanged

## Unit Tests

**File:** `apps/worker/tests/test_client_arxiv.py`

Add:

```python
class TestArxivTitleAuthorSearch:
    def test_title_author_returns_candidates(self):
        """Combined title+author search produces results."""
        # ID lookup fails, DOI fails → title+author returns results
        # Verify search_query contains 'AND au:'

    def test_surname_extracted_from_comma_format(self):
        """'Smith, J.' → surname 'Smith' used in query."""

    def test_surname_extracted_from_space_format(self):
        """'John Smith' → surname 'Smith' used in query."""

    def test_skipped_when_no_authors(self):
        """Without authors, falls through to title-only search."""

class TestArxivExtractSurname:
    def test_comma_format(self):
        assert ArxivClient._extract_surname("Smith, J.") == "Smith"

    def test_space_format(self):
        assert ArxivClient._extract_surname("John Smith") == "Smith"

    def test_initials_format(self):
        assert ArxivClient._extract_surname("L. Martínez") == "Martínez"

    def test_single_name(self):
        assert ArxivClient._extract_surname("Aristotle") == "Aristotle"
```

Update ALL existing tests to add new params to `client.search()` calls.

## Dependencies

- **Depends on:** Step 02 (new fields in search interface)
- **Informs:** Step 07 (verify node passes authors to arXiv), Step 08 (Postman validates combined search)
