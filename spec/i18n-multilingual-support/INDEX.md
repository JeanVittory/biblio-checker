# i18n Multilingual Support — Reading Order and Dependencies

## Dependency Graph

```
01 (Overview)
     │
     ├──────────────────────────────────────┐
     v                                      v
02 (Database Schema)               08 (Frontend Infrastructure)
     │                                      │
     v                                      v
03 (Backend API Contract)          09 (Message Catalogs)
     │                                      │
     ├──> 04 (HTTP Error Translation)       │
     │                                      v
     v                             10 (Component Migration)
05 (Worker i18n Module)                     │
     │                                      v
     ├──> 06 (Classification Reasons)   11 (Language Toggle + Wiring)
     └──> 07 (Warning Messages)             │
              │                             │
              └──────────────┬──────────────┘
                             v
                     12 (Testing Strategy)
```

## Navigation

| Step | Title | Depends on | Key deliverable |
|------|-------|------------|-----------------|
| 01 | Overview and Locale Model | — | Locale catalog (`es`/`pt`/`en`), detection order, translation boundaries, ICU-style interpolation rules |
| 02 | Database Schema | 01 | `analysis_jobs.locale` column + CHECK constraint + RPC updated to expose locale when claiming |
| 03 | Backend API Contract | 02 | Start request accepts `locale`, persists it; jobs repo returns it; `ResultsV1.reportLanguage` widened to `^(es\|pt\|en)$` |
| 04 | HTTP Error Translation | 03 | ~6 error messages translated via `Accept-Language` header; reusable `http_errors.py` helper |
| 05 | Worker i18n Module | 03 | New `langgraph/i18n.py` with `render(key, locale, **params)`; `GraphState.locale`; plumbed through `run_langgraph` stage |
| 06 | Classification Reasons (Worker) | 05 | All 11 `decisionReason` templates in `classification.py` refactored to `render(...)`; ES/PT/EN in catalog |
| 07 | Warning Messages (Worker) | 05 | All `warnings[].message` generators in `nodes/verify.py`, `parse_references.py`, `normalize.py`, `classify.py`, `cross_patterns.py` refactored |
| 08 | Frontend i18n Infrastructure | 01 | `next-intl` installed, `next.config.ts` plugin, `i18n/config.ts`, `i18n/request.ts`, `LocaleProvider`, dynamic `<html lang>` |
| 09 | Message Catalogs | 08 | `messages/es.json`, `pt.json`, `en.json` with ~75 keys in namespaces (`common`, `upload`, `dropzone`, `recent`, `status`, `results.*`, `errors`) |
| 10 | Component Migration | 09 | Every hardcoded-string component (page.tsx, file-dropzone, upload-status, recent-analyses/*, StorageErrorBanner, constants.ts) reads from catalogs |
| 11 | Language Toggle + Wiring | 10 | Header `LanguageToggle`; locale cookie; `analysis-start-gateway` forwards locale to backend |
| 12 | Testing Strategy | 06–07, 10–11 | Worker unit tests for templates; backend contract tests; frontend render tests per locale; manual E2E checklist |

## Implementation Phases

**Phase 1 — Contract & Storage (Steps 02–03):**
Add the `locale` column and widen the `reportLanguage` pattern. Safe to deploy standalone — existing flows default to `es` and nothing visible changes.

**Phase 2 — Backend/Worker Rendering (Steps 04–07):**
Build the worker i18n catalog, refactor classification and warning generators to use it, translate HTTP errors. At the end of this phase, a job submitted with `locale='pt'` would already produce a Portuguese payload — but nothing on the frontend can request `pt` yet.

**Phase 3 — Frontend i18n (Steps 08–10):**
Install `next-intl`, create the three catalogs, migrate every component. At the end of this phase, the UI renders in any of the three languages but still defaults everywhere to `es` because no toggle exists yet.

**Phase 4 — User-facing Language Selection (Step 11):**
Add the `LanguageToggle`, persist the user's choice in `localStorage`/cookie, and propagate it through `/api/analysis-start-gateway` so new analyses are rendered in the chosen language end-to-end.

**Phase 5 — Verification (Step 12):**
Run the full test matrix: worker template tests, backend contract tests, frontend component snapshots per locale, and the end-to-end manual checklist that uploads a real PDF in each language.

## Roll-back Plan

| Phase | Roll-back |
|-------|-----------|
| 1 (DB + contract) | Drop `locale` column; revert schema widening. Zero user-visible impact. |
| 2 (Worker) | Keep the catalog module but revert `classification.py`/nodes to Spanish f-strings. The column remains but is ignored. |
| 3 (Frontend infra) | Remove `next-intl` plugin + provider; restore hardcoded strings from git history. |
| 4 (Toggle) | Remove `LanguageToggle`; gateway stops forwarding locale; worker falls back to stored `es`. |
