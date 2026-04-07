# Enhanced Search Strategies for Bibliographic Reference Verification

## Overview

This specification suite upgrades the bibliographic reference verification pipeline to extract more metadata fields from references and use smarter, multi-strategy searches against OpenAlex, SciELO, and arXiv. The current system only extracts 6 fields (title, authors, year, venue, doi, arxivId) and uses simplistic search strategies that miss many valid references.

## Problem Statement

1. **SciELO title search is broken.** The `/article/identifiers/?title=X` endpoint ignores the `title` parameter — it returns all 1.3M articles unfiltered. This was confirmed by Postman testing.
2. **OpenAlex author filter was invalid.** `authorships.author.display_name.search` is not a valid filter (already fixed to `raw_author_name.search`).
3. **Useful metadata is discarded.** Bibliographic references in all major styles (APA, MLA, Chicago, Vancouver, IEEE) contain volume, issue, pages, publisher, and sometimes ISSN — all of which are ignored by the current normalization pipeline.
4. **Search strategies are too few.** OpenAlex supports filtering by year, ISSN, volume, and issue, but the client only uses title, author, and DOI. arXiv supports `au:` (author) and `jr:` (journal reference) prefixes but only uses `ti:` and `doi:`.

## Key Findings from API Validation

| API | DOI Lookup | Title Search | Author Search | ISSN Filter | Year Filter | Volume/Issue |
|-----|-----------|-------------|---------------|-------------|-------------|--------------|
| **OpenAlex** | `GET /works/https://doi.org/{doi}` | `filter=title.search:{t}` | `filter=raw_author_name.search:{a}` | `filter=primary_location.source.issn:{issn}` | `filter=publication_year:{y}` | `filter=biblio.volume:{v},biblio.issue:{i}` |
| **SciELO** | `GET /article/?doi={doi}` | **BROKEN** (param ignored) | Not supported | `GET /article/identifiers/?issn={issn}` | Not supported | Not supported |
| **arXiv** | `search_query=doi:{doi}` | `search_query=ti:"{t}"` | `search_query=au:{a}` | Not supported | Not supported | Not supported |

## Bibliographic Styles Analyzed

All five major styles used by students were analyzed for available metadata:

- **APA** (American Psychological Association)
- **MLA** (Modern Language Association)
- **Chicago** (Chicago Manual of Style)
- **Vancouver** (ICMJE)
- **IEEE** (Institute of Electrical and Electronics Engineers)

Every style always provides: **title**, **authors**, **year**, and **venue** (journal name or publisher). Most journal articles also include **volume**, **issue**, and **pages**. DOI and ISSN are occasionally present.

## Scope

**In scope:**
- Expand `NormalizedFields` schema with 5 new fields (issn, volume, issue, pages, publisher)
- Update LLM normalization prompt to extract new fields
- Add ISSN format validation
- Implement new search strategies for OpenAlex (6 strategies with combined filters)
- Replace broken SciELO title search with ISSN-based search
- Add title+author combined search to arXiv
- Update verify node to pass new fields to clients
- Update Postman collection for validation
- Synchronize schemas across worker, backend, and frontend

**Out of scope:**
- Changes to the scoring engine (Step 08) — existing `compute_match_score()` is unaffected
- Changes to the classification engine (Step 09) — existing rules remain
- Changes to the assemble report node (Step 11)
- Frontend UI changes to display new fields

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| New fields are all optional (nullable) | `str \| None = None` | Most references won't have all fields; backward-compatible |
| Remove SciELO title search entirely | Replace with ISSN search | Title param on `/article/identifiers/` does nothing (confirmed) |
| Keep same `search()` interface for all clients | Extended with new kwargs | Each client ignores params its API doesn't support |
| OpenAlex is the primary search engine | 6 strategy cascade | It's the only API that supports combined metadata filters |
| arXiv gets title+author combined search | `ti:"{t}"+AND+au:{a}` | arXiv API supports boolean operators between field prefixes |
| ISSN validation regex | `^\d{4}-\d{3}[\dXx]$` | Standard ISSN format (4 digits, hyphen, 3 digits, check digit) |

## Audience

| Reader | Start here |
|--------|------------|
| Understanding the full change | Step 01 (Overview) |
| Implementing schema changes | Step 02 (Normalized Fields Expansion) |
| Implementing API client changes | Steps 04-06 (per-client strategies) |
| Testing the changes | Step 08 (Postman Validation) |

## Statistics

| Metric | Value |
|--------|-------|
| Total steps | 8 |
| Modified Python modules | 8 files |
| Modified TypeScript modules | 1 file |
| Modified spec files | 2 files |
| Modified Postman files | 1 file |
| New fields added | 5 (issn, volume, issue, pages, publisher) |
| New search strategies | 5 (OpenAlex: 3 new, SciELO: 1 new, arXiv: 1 new) |
| Search strategies removed | 1 (SciELO broken title search) |
