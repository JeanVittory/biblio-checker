# Enhanced Search Strategies — Reading Order and Dependencies

## Dependency Graph

```
01 (Overview) ──> 02 (Normalized Fields Expansion)
                       │
                  03 (ISSN Validation)
                       │
           ┌───────────┼───────────┐
           v           v           v
     04 (OpenAlex) 05 (SciELO) 06 (arXiv)
           │           │           │
           └───────────┼───────────┘
                       v
               07 (Verify Node Update)
                       │
                       v
               08 (Postman Validation)
```

## Navigation

| Step | Title | Depends on | Key deliverable |
|------|-------|------------|-----------------|
| 01 | Overview and Field Analysis | — | Metadata field matrix per bibliographic style, API capability map |
| 02 | Normalized Fields Expansion | 01 | Updated `NormalizedFields`, `NormalizedReference` (worker + backend + frontend), LLM prompt |
| 03 | ISSN Validation | 02 | `_validate_issn()` in normalize node, new fields in output dict |
| 04 | OpenAlex Search Strategies | 02 | 6-strategy cascade with combined filters (year, ISSN, volume) |
| 05 | SciELO Search Strategies | 02, 03 | Replace broken title search with ISSN search |
| 06 | arXiv Search Strategies | 02 | Add title+author combined search with boolean operators |
| 07 | Verify Node Update | 04, 05, 06 | Pass all new fields to `client.search()` calls |
| 08 | Postman Validation | 04, 05, 06 | Updated collection with requests for new strategies |

## Implementation Phases

**Phase 1 — Schema & Normalization** (Steps 01–03): Expand fields, update LLM prompt, add ISSN validation. No API changes yet.

**Phase 2 — API Client Strategies** (Steps 04–06): Implement new search strategies per client. Each client can be done independently.

**Phase 3 — Wiring & Validation** (Steps 07–08): Connect verify node to new fields, update Postman for end-to-end validation.
