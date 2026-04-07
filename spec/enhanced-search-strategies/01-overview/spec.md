# Step 01 — Overview: Bibliographic Styles and Available Metadata

## Scope

- Catalog the metadata fields present in each major bibliographic style
- Map which fields are extractable by an LLM from reference text
- Identify which fields each external API can use for searching
- Define the strategy routing logic: which repository to use based on available fields

**Out of scope:** Implementation details of individual clients (Steps 04–06). Normalization prompt changes (Step 02). Validation logic (Step 03).

## Context

Students use five major citation styles in their academic work. Each style structures references differently, but all contain a predictable set of metadata fields. The LLM can extract these fields regardless of style. The goal is to maximize the metadata extracted and route searches to the API that can best use each combination of fields.

## Requirements

### 1. Bibliographic Styles and Their Fields

#### 1.1 Book References

| Campo | APA | MLA | Chicago | Vancouver | IEEE |
|-------|-----|-----|---------|-----------|------|
| **authors** | `Williams, P. F.` | `García Márquez, Gabriel` | `García Márquez, Gabriel` | `García Márquez G.` | `G. García Márquez` |
| **year** | `(2007)` | `1967` (al final) | `1967` (al final) | `1967` (al final) | `1967` |
| **title** | *J. S. Bach: A life in music* | *Cien años de soledad* | *Cien años de soledad* | *Cien años de soledad* | *Cien años de soledad* |
| **publisher** | `Cambridge University Press` | `Sudamericana` | `Editorial Sudamericana` | `Editorial Sudamericana` | `Editorial Sudamericana` |
| **city** | — | — | `Bogotá` | `Bogotá` | `Bogotá, Colombia` |
| **edition** | — | — | — | `2ª ed.` | `2.ª ed.` |
| **doi** | sometimes | rare | sometimes | rare | sometimes |

**Examples:**

- **APA:** Williams, P. F. (2007). *J. S. Bach: A life in music*. Cambridge University Press.
- **MLA:** García Márquez, Gabriel. *Cien años de soledad*. Sudamericana, 1967.
- **Chicago:** García Márquez, Gabriel. *Cien años de soledad*. Bogotá: Editorial Sudamericana, 1967.
- **Vancouver:** García Márquez G. *Cien años de soledad*. 2ª ed. Bogotá: Editorial Sudamericana; 1967.
- **IEEE:** [1] G. García Márquez, *Cien años de soledad*, 2.ª ed. Bogotá, Colombia: Editorial Sudamericana, 1967.

#### 1.2 Journal Article References

| Campo | APA | MLA | Chicago | Vancouver | IEEE |
|-------|-----|-----|---------|-----------|------|
| **authors** | `Morán, P.` | `Martínez, Lucía` | `Martínez, Lucía` | `Martínez L.` | `L. Martínez` |
| **year** | `(2004)` | `2021` | `(marzo 2021)` | `2021 Mar 10` | `Mar. 2021` |
| **title** | "La docencia como..." | "La metáfora en..." | "La metáfora en..." | La metáfora en... | "La metáfora en..." |
| **venue** | *Perfiles Educativos* | *Revista de Lit. Hispánica* | *Revista de Lit. Hispánica* | *Rev Lit Hisp.* | *Rev. Lit. Hisp.* |
| **volume** | `26` | `vol. 12` | `12` | `12` | `vol. 12` |
| **issue** | `(105-106)` | `n.º 3` | `n.º 3` | `(3)` | `n.º 3` |
| **pages** | `41-72` | `pp. 45-60` | `45-60` | `45-60` | `pp. 45-60` |
| **doi** | sometimes | rare | sometimes | rare | sometimes |

**Examples:**

- **APA:** Morán, P. (2004). La docencia como recreación y construcción del conocimiento. *Perfiles Educativos*, 26(105-106), 41-72.
- **MLA:** Martínez, Lucía. "La metáfora en la poesía moderna". *Revista de Literatura Hispánica*, vol. 12, n.º 3, 2021, pp. 45-60.
- **Chicago:** Martínez, Lucía. "La metáfora en la poesía moderna". *Revista de Literatura Hispánica* 12, n.º 3 (marzo 2021): 45-60.
- **Vancouver:** Martínez L. La metáfora en la poesía moderna. Rev Lit Hisp. 2021 Mar 10;12(3):45-60.
- **IEEE:** [2] L. Martínez, "La metáfora en la poesía moderna", *Rev. Lit. Hisp.*, vol. 12, n.º 3, pp. 45-60, Mar. 2021, doi: 10.1016/j.lit.2021.03.001.

### 2. Field Availability Summary

| Field | Books | Journal articles | Extractable by LLM |
|-------|-------|------------------|---------------------|
| `title` | always | always | **yes** — 100% |
| `authors` | always | always | **yes** — 100% |
| `year` | always | always | **yes** — 100% |
| `venue` | publisher name | journal name | **yes** — ~95% |
| `volume` | never | always | **yes** — ~80% (only articles) |
| `issue` | never | almost always | **yes** — ~75% (only articles) |
| `pages` | never | almost always | **yes** — ~75% (only articles) |
| `publisher` | always | never | **yes** — ~40% (only books) |
| `doi` | sometimes | sometimes | **yes** — ~30% |
| `issn` | never | rare (explicit) | **yes** — ~5% explicit |
| `arxivId` | never | only preprints | **yes** — ~5% |

### 3. API Search Capabilities

#### 3.1 OpenAlex (most comprehensive)

| Filter | API Parameter | Validated |
|--------|---------------|-----------|
| DOI exact lookup | `GET /works/https://doi.org/{doi}` | yes |
| Title fuzzy search | `filter=title.search:{title}` | yes |
| Author name search | `filter=raw_author_name.search:{author}` | yes |
| Publication year | `filter=publication_year:{year}` | yes (from API docs) |
| ISSN | `filter=primary_location.source.issn:{issn}` | yes (from API docs) |
| Volume | `filter=biblio.volume:{vol}` | yes (from API docs) |
| Issue | `filter=biblio.issue:{issue}` | yes (from API docs) |
| Combined filters | comma-separated | yes |

#### 3.2 SciELO ArticleMeta

| Filter | API Parameter | Validated |
|--------|---------------|-----------|
| DOI exact lookup | `GET /article/?doi={doi}` | yes |
| ISSN identifier search | `GET /article/identifiers/?issn={issn}&limit=5` | yes (Postman) |
| Fetch by PID | `GET /article/?code={pid}&collection={col}` | yes (Postman) |
| Title search | `GET /article/identifiers/?title={title}` | **BROKEN** — param is ignored |
| Author search | — | not supported |
| Year filter | — | not supported |
| Volume/Issue | — | not supported |

#### 3.3 arXiv API

| Filter | API Parameter | Validated |
|--------|---------------|-----------|
| arXiv ID exact lookup | `id_list={id}` | yes |
| DOI search | `search_query=doi:{doi}` | yes |
| Title search | `search_query=ti:"{title}"` | yes |
| Author search | `search_query=au:{author}` | yes (from API docs) |
| Journal reference | `search_query=jr:{journal}` | yes (from API docs) |
| Boolean combinations | `ti:"{t}"+AND+au:{a}` | yes (from API docs) |

### 4. Search Strategy Routing

Given a normalized reference, determine which strategies to execute based on available fields:

```
PRIORITY 1: Exact identifier match (highest confidence)
  ├─ DOI present? → OpenAlex(DOI) + SciELO(DOI) + arXiv(DOI)
  └─ arXiv ID present? → arXiv(ID)

PRIORITY 2: Specific metadata combinations
  ├─ ISSN + volume present? → OpenAlex(ISSN+volume) + SciELO(ISSN)
  └─ title + author + year present? → OpenAlex(title+author+year) + arXiv(title+author)

PRIORITY 3: Partial metadata
  ├─ title + year present? → OpenAlex(title+year)
  └─ title + author present? → OpenAlex(title+author) + arXiv(title+author)

PRIORITY 4: Minimal metadata (lowest confidence)
  └─ title present? → OpenAlex(title) + arXiv(title)
```

Each client internally implements this cascade in its `search()` method. The verify node calls all three clients for every reference — each client returns what it can find using the best strategy available for its API.

## Acceptance Criteria

- [ ] All 5 bibliographic styles are documented with field availability
- [ ] API capabilities are validated against real endpoints
- [ ] Routing logic covers all field combinations
- [ ] New fields to extract are identified: `issn`, `volume`, `issue`, `pages`, `publisher`

## Dependencies

- **Depends on:** Existing API client implementations (Step 07 of langgraph-reference-analysis)
- **Informs:** All subsequent steps in this suite
