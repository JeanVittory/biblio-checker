# Step 07 — API Clients (OpenAlex, SciELO, arXiv)

## Scope

- Implement HTTP clients for OpenAlex, SciELO ArticleMeta, and arXiv APIs
- Define the search strategies for each source
- All clients return `list[MatchCandidate]` (uniform interface)
- Define timeout and error handling per client

**Out of scope:** Similarity scoring logic (Step 08). Classification decisions (Step 09). Fan-out orchestration (Step 10).

## Context

Each API client receives a normalized reference (title, authors, year, DOI, arXiv ID) and searches for matching works. The clients implement a multi-strategy search: try the most specific identifiers first (DOI, arXiv ID), then fall back to metadata-based searches (title, author+title).

All three clients return `list[MatchCandidate]` from `langgraph/schemas.py` (defined in Step 01). This uniform interface allows the classification engine (Step 09) to process results from all sources identically.

## Requirements

### 1. Shared Client Pattern

Each client class follows this structure:

```python
class XxxClient:
    def __init__(self, base_url: str, timeout: int, **kwargs):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        # provider-specific kwargs

    def search(self, *, title: str | None, authors: list[str], year: int | None, doi: str | None, arxiv_id: str | None) -> list[MatchCandidate]:
        """Search for matching works using the best available strategy."""

    def close(self):
        """Close the underlying HTTP client."""
```

The `search()` method is the single public entry point. It internally decides which search strategy to use based on available metadata.

### 2. OpenAlex Client — `clients/openalex.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/clients/openalex.py`

**API Base:** `https://api.openalex.org`

**Search strategies (in priority order):**

1. **DOI lookup** (if `doi` is provided):
   - `GET /works/https://doi.org/{doi}`
   - If found, returns 1 `MatchCandidate` with `match_type="doi_exact"`, `raw_score=1.0`

2. **Title search** (if `title` is provided):
   - `GET /works?filter=title.search:{title}&per_page=5`
   - Returns up to 5 candidates with `match_type="title_fuzzy"`
   - `raw_score` is NOT provided by OpenAlex — set to `0.0` (scoring is handled by Step 08)

3. **Author + Title search** (if both `title` and `authors` are provided):
   - `GET /works?filter=title.search:{title},authorships.author.display_name.search:{first_author}&per_page=5`
   - Returns up to 5 candidates with `match_type="metadata_partial"`

**Response mapping to MatchCandidate:**

| OpenAlex field | MatchCandidate field |
|---------------|---------------------|
| `id` (e.g., `https://openalex.org/W1234567890`) | `external_id` (extract `W1234567890`) |
| `title` | `title` |
| `authorships[*].author.display_name` | `authors` |
| `publication_year` | `year` |
| `doi` (e.g., `https://doi.org/10.1234/...`) | `doi` (extract `10.1234/...`) |
| `id` as URL | `url` |

**Headers:**
- `User-Agent: BiblioChecker/0.1 (mailto:{openalex_email})` if `settings.openalex_email` is set (polite pool)
- `Accept: application/json`

### 3. SciELO Client — `clients/scielo.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/clients/scielo.py`

**API Base:** `https://articlemeta.scielo.org/api/v1` (defined as module-level constant `SCIELO_BASE_URL`)

**Search strategies (in priority order):**

1. **DOI lookup** (if `doi` is provided):
   - `GET /article/?doi={doi}`
   - If found, returns 1 `MatchCandidate` with `match_type="doi_exact"`, `raw_score=1.0`

2. **Title search** (if `title` is provided):
   - `GET /article/identifiers/?title={title}&limit=5`
   - Returns up to 5 candidates with `match_type="title_fuzzy"`
   - The identifiers endpoint returns only PIDs — a second `GET /article/?code={pid}&collection={collection}` is required to fetch full metadata for each PID.

**Example API responses:**

DOI lookup (`GET /article/?doi={doi}`):
```json
{
  "code": "S0123-45672020000100001",
  "collection": "scl",
  "article": {
    "v12": [{"_": "Example Article Title"}],
    "v10": [{"n": "John", "s": "Smith"}, {"n": "Jane", "s": "Doe"}],
    "v65": [{"_": "20200601"}],
    "v237": [{"_": "10.1234/example"}],
    "v880": [{"_": "S0123-45672020000100001"}]
  }
}
```

Title search (`GET /article/identifiers/?title={title}&limit=5`):
```json
{
  "objects": [
    {"code": "S0123-45672020000100001", "collection": "scl"}
  ]
}
```

**Response mapping to MatchCandidate:**

SciELO uses ISIS field codes in its article response. The mapping is:

| SciELO field | MatchCandidate field |
|-------------|---------------------|
| `code` or `article.v880[0]._` | `external_id` |
| `article.v12[0]._` | `title` |
| `article.v10[*]` → join `n` + `s` for each author | `authors` |
| `article.v65[0]._` → first 4 characters (year portion) | `year` |
| `article.v237[0]._` | `doi` |
| Constructed: `https://www.scielo.br/scielo.php?pid={code}&script=sci_arttext` | `url` |

**Note:** SciELO's API uses ISIS field codes (v12=title, v10=authors, v65=date, v237=DOI). The identifiers endpoint returns only PIDs — a second GET to `/article/?code={pid}&collection={collection}` is needed to fetch full metadata. If the API structure differs from documented, adapt gracefully and return an empty list on parse failure.

### 4. arXiv Client — `clients/arxiv.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/clients/arxiv.py`

**API Base:** `https://export.arxiv.org/api` (defined as module-level constant `ARXIV_BASE_URL`; HTTPS enforced)

**Search strategies (in priority order):**

1. **arXiv ID lookup** (if `arxiv_id` is provided):
   - `GET /query?id_list={arxiv_id}`
   - If found, returns 1 `MatchCandidate` with `match_type="identifier_exact"`, `raw_score=1.0`

2. **DOI search** (if `doi` is provided):
   - `GET /query?search_query=doi:{doi}&max_results=1`
   - Returns 0-1 candidates with `match_type="doi_exact"`

3. **Title search** (if `title` is provided):
   - `GET /query?search_query=ti:"{title}"&max_results=5`
   - Returns up to 5 candidates with `match_type="title_fuzzy"`

**Response format:** arXiv returns Atom XML. The client MUST parse the XML response.

**Response mapping to MatchCandidate:**

| arXiv field | MatchCandidate field |
|------------|---------------------|
| `<id>` (e.g., `http://arxiv.org/abs/2301.12345v1`) | `external_id` (extract `2301.12345`) |
| `<title>` | `title` |
| `<author><name>` | `authors` |
| `<published>` year portion | `year` |
| `<arxiv:doi>` if present | `doi` |
| `<id>` as URL | `url` |

**Note:** arXiv has rate limits. The client SHOULD respect a 3-second delay between requests. Use `time.sleep(3)` between consecutive calls if multiple search strategies are tried.

### 5. Input Validation (all clients)

Before making any HTTP request, each client MUST validate identifier formats to prevent malformed data from reaching external APIs.

**DOI format validation:**
- Valid pattern: `^10\.\d{4,}(/\S+)+$`
- If the DOI does not match, skip the DOI lookup and log a DEBUG message. Fall through to title search.

**arXiv ID format validation:**
- Valid patterns: `^\d{4}\.\d{4,5}(v\d+)?$` OR `^[a-z-]+/\d{7}$`
- If the arXiv ID does not match, skip the ID lookup. Fall through to title search.

**URL encoding:**
- All query parameters MUST be passed using `httpx`'s `params=` kwarg, NOT via f-string interpolation. This ensures correct URL encoding automatically.
- For DOI values used in URL paths (e.g., OpenAlex `/works/https://doi.org/{doi}`), use `urllib.parse.quote(doi, safe="")` before interpolation.

**API base URLs:**
- Each client defines its base URL as a module-level constant (not from settings):
  ```python
  # clients/openalex.py
  OPENALEX_BASE_URL = "https://api.openalex.org"

  # clients/scielo.py
  SCIELO_BASE_URL = "https://articlemeta.scielo.org/api/v1"

  # clients/arxiv.py
  ARXIV_BASE_URL = "https://export.arxiv.org/api"
  ```
- The `__init__` `base_url` parameter in the shared client pattern (Section 1) is retained for test injection but MUST default to the respective constant.

### 6. Error Handling (all clients)

| Error scenario | Behavior |
|---------------|----------|
| HTTP 404 (not found) | Return empty `list[MatchCandidate]` |
| HTTP 429 (rate limited) | Raise `httpx.HTTPStatusError` — caught at node level |
| HTTP 5xx (server error) | Raise `httpx.HTTPStatusError` — caught at node level |
| Network timeout | Raise `httpx.TimeoutException` — caught at node level |
| Connection error | Raise `httpx.ConnectError` — caught at node level |
| Malformed response (can't parse) | Log warning, return empty `list[MatchCandidate]` |
| XML parse error (arXiv) | Log warning, return empty `list[MatchCandidate]` |

Clients MUST NOT swallow HTTP errors for non-404 status codes. The `verify_single_reference` node (Step 10) handles per-source failures.

### 7. Logging

Each client logs:
- INFO: `"search_starting"` with `source`, search strategy used, and key parameters
- INFO: `"search_complete"` with `source`, `candidates_found=len(results)`
- WARNING: `"search_parse_error"` if response is malformed
- DEBUG: `"search_request"` with full URL (for debugging)

Logger names: `"biblio_checker_worker.langgraph.clients.openalex"`, etc.

## Acceptance Criteria

- [ ] `OpenAlexClient.search()` returns `list[MatchCandidate]`
- [ ] `ScieloClient.search()` returns `list[MatchCandidate]`
- [ ] `ArxivClient.search()` returns `list[MatchCandidate]`
- [ ] All clients try DOI/identifier lookup first, then fall back to title search
- [ ] OpenAlex includes polite pool email header when `settings.openalex_email` is set
- [ ] arXiv client parses Atom XML responses correctly
- [ ] HTTP 404 returns empty list (not an error)
- [ ] Non-404 HTTP errors propagate as exceptions
- [ ] Malformed responses return empty list with a warning log
- [ ] All clients accept `base_url` and `timeout` as constructor parameters
- [ ] Unit tests with mocked HTTP responses cover: DOI found, title search with results, no results, HTTP error, malformed response

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| DOI with special characters (e.g., parentheses) | URL-encode the DOI in the request |
| arXiv ID in old format (`hep-ph/9901234`) | Pass as-is to the API; arXiv handles both formats |
| Title with special characters or non-ASCII | URL-encode properly; APIs should handle Unicode |
| OpenAlex returns a work with no title | Set `title=None` in MatchCandidate |
| SciELO API is down or unreachable | `httpx.ConnectError` propagates to node level |
| arXiv returns 0 results for ID lookup | Return empty list (the ID may be incorrect) |

## Dependencies

- **Depends on:** Step 01 (dependencies: `httpx`, config settings: `api_timeout_seconds`, `openalex_email`; base URL constants defined per-client), Step 01 (schemas: `MatchCandidate`)
- **Informs:** Step 08 (scoring uses MatchCandidate), Step 10 (verify node calls all 3 clients)
