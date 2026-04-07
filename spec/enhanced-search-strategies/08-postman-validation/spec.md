# Step 08 — Postman Collection Validation

## Scope

- Update the Postman collection to validate the new search strategies
- Add requests for OpenAlex combined filters, SciELO ISSN search, and arXiv title+author search
- Include test scripts that validate response structure

**Out of scope:** Newman automation. CI/CD integration.

## Context

The Postman collection (`postman/biblio-checker.postman_collection.json`) already contains an "External API Validation" folder created for the initial endpoint testing. This step updates it to cover the new strategies added in Steps 04–06, and fixes the issues found during the initial testing round (broken SciELO, arXiv rate limiting).

## Requirements

### 1. OpenAlex — New Requests

Add to the OpenAlex sub-folder:

#### 1d) Title + Author + Year Search

- **URL:** `https://api.openalex.org/works?filter=title.search:Array programming with NumPy,raw_author_name.search:Harris,publication_year:2020&per_page=5`
- **Tests:**
  - HTTP 200
  - `results` array is not empty
  - Each result has `id`, `title`, `publication_year`, `authorships`
  - First result's `publication_year` equals 2020

#### 1e) ISSN + Volume Search

- **URL:** `https://api.openalex.org/works?filter=primary_location.source.issn:0028-0836,biblio.volume:585&per_page=5`
- **Test data:** Nature (ISSN 0028-0836), volume 585 (2020)
- **Tests:**
  - HTTP 200
  - `results` array is not empty
  - Each result has `id`, `title`, `publication_year`

#### 1f) Title + Year Search

- **URL:** `https://api.openalex.org/works?filter=title.search:Array programming with NumPy,publication_year:2020&per_page=5`
- **Tests:**
  - HTTP 200
  - `results` array is not empty
  - First result's `publication_year` equals 2020

### 2. SciELO — Replace Title Search with ISSN Search

Replace the current SciELO requests with:

#### 2a) DOI Lookup (updated DOI)

- **URL:** `https://articlemeta.scielo.org/api/v1/article/?doi=10.1590/S0034-89102006000400003`
- **Tests:** Same as current (code, article, v12, v10, v65)
- **Note:** If this DOI returns 404, add a note that SciELO DOI coverage is limited

#### 2b) ISSN Search (identifiers)

- **URL:** `https://articlemeta.scielo.org/api/v1/article/identifiers/?issn=0034-8910&limit=3`
- **Tests:**
  - HTTP 200
  - `meta.filter.issn` equals `"0034-8910"` (confirms ISSN filtering is active)
  - `meta.total` is greater than 0 and less than 1,400,000 (confirms NOT returning all articles)
  - `objects` array has items
  - Each object has `code` and `collection`
  - Save first PID to env: `scielo_test_pid`, `scielo_test_collection`

#### 2c) Fetch Article by PID

- **URL:** `https://articlemeta.scielo.org/api/v1/article/?code={{scielo_test_pid}}&collection={{scielo_test_collection}}`
- **Dependency:** Run after 2b
- **Tests:**
  - HTTP 200
  - Has `code`, `article` object
  - Article has `v12` (title), `v10` (authors), `v65` (date)
  - Cleanup env vars

### 3. arXiv — Add Title+Author Search

Add to the arXiv sub-folder:

#### 3d) Title + Author Search

- **URL:** `https://export.arxiv.org/api/query?search_query=ti:"Attention Is All You Need"+AND+au:Vaswani&max_results=5`
- **Pre-request:** 4-second delay (same as other arXiv requests)
- **Tests:**
  - HTTP 200
  - Response is XML
  - Contains `<entry>` element
  - Entry has `<id>`, `<title>`, `<author><name>`, `<published>`

### 4. arXiv Rate Limiting

All arXiv requests MUST have:
- **Pre-request script:** Busy-wait until 4 seconds have passed since `last_arxiv_request_time`
- **Test script:** Record `Date.now()` to `last_arxiv_request_time`
- **Last request:** Clean up `last_arxiv_request_time` from env

### 5. Folder Description Update

Update the "External API Validation" folder description:

```
Validates that the external APIs used for bibliographic reference verification respond correctly.

Strategies tested:
- OpenAlex: DOI lookup, title search, author+title search, title+author+year, ISSN+volume, title+year
- SciELO: DOI lookup, ISSN search (identifiers → fetch by PID)
- arXiv: ID lookup, DOI search, title search, title+author search

IMPORTANT: Run arXiv requests one at a time (4s delay is built into pre-request scripts).
```

## Acceptance Criteria

- [ ] OpenAlex folder has 6 requests (1a–1f)
- [ ] SciELO folder has 3 requests (2a–2c) with ISSN-based search replacing title search
- [ ] arXiv folder has 4 requests (3a–3d) with title+author combined search
- [ ] SciELO 2b test validates that `meta.total < 1,400,000` (ISSN filter is working)
- [ ] arXiv pre-request scripts enforce 4-second delay
- [ ] All test scripts validate response structure matching client expectations
- [ ] JSON is valid: `python3 -m json.tool postman/biblio-checker.postman_collection.json`

## Verification

1. Import updated collection into Postman
2. Run OpenAlex folder → all 6 requests should pass
3. Run SciELO folder sequentially (2b before 2c) → all 3 should pass
4. Run arXiv folder one by one (wait for pre-request delay) → all 4 should pass
5. Validate JSON syntax: `python3 -m json.tool postman/biblio-checker.postman_collection.json`

## Dependencies

- **Depends on:** Steps 04, 05, 06 (strategies to validate)
- **Informs:** Nothing (final step in the suite)
