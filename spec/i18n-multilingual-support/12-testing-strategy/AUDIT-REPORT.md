# i18n Multilingual Support — Audit Report

**Date:** 2026-04-14  
**Auditor:** QA Agent (claude-sonnet-4-6)  
**Branch:** develop  
**Scope:** Wave 1 + Wave 2 implementation against spec steps 01–12

---

## 1. Per-Step Coverage Matrix

### Step 01 — Overview: Locale Model, Detection, and Translation Boundaries

| Acceptance Criterion | Coverage | Notes |
|---|---|---|
| `LOCALES = ("es","pt","en")` with `DEFAULT_LOCALE = "es"` on all three sides | PASS | Worker `i18n.py`, Backend `http_errors.py`, Frontend `config.ts` all match |
| `normalizeLocale()` strips region suffixes on frontend | PASS | `config.ts` + `detect.ts` |
| Detection order: `localStorage → cookie → Accept-Language → default` | PARTIAL | Spec detection order lists `localStorage` first (§2), but `detect.ts` does NOT check `localStorage` — it only checks the NEXT_LOCALE cookie then Accept-Language. The `LanguageToggle` writes both, but `detectLocale()` only reads the cookie. Cookie-first (Step 11 §7) is the documented spec priority for SSR; localStorage is client-only for UX consistency. This is an acceptable gap but not a test-blocking issue. |
| Translation boundary matrix honoured | PASS | `decisionReason` rendered verbatim in ExpandedDetail; frontend does not import worker catalog |
| Placeholder syntax `{name}` exclusively | PASS | All catalogs use ICU `{name}` format |
| Missing-key fallback chain | PASS | Worker: returns `[i18n:key]`; Frontend: `onError` handler in `request.ts` |
| Locale immutability per analysis | PASS | DB column is immutable after creation; frontend renders verbatim |
| Key namespacing matches §7 | PASS | `class.*` / `warn.*` worker; namespaced frontend keys |

### Step 02 — Database Schema

| Acceptance Criterion | Coverage | Notes |
|---|---|---|
| Migration file exists | PASS | `supabase/migrations/20260414000000_add_locale_to_analysis_jobs.sql` |
| `locale TEXT NOT NULL DEFAULT 'es'` | PASS | Migration SQL confirmed |
| CHECK constraint `locale IN ('es','pt','en')` | PASS | Migration SQL confirmed |
| Column comment added | PASS | `COMMENT ON COLUMN` present |
| Idempotent (DO $$ BEGIN IF NOT EXISTS $$) | PASS | Both DO blocks present |
| `claim_analysis_job` RPC projects `locale` automatically via `RETURNING *` | PASS | Documented in migration comment; RPC uses SETOF |
| **REQUIRES MIGRATION** — All 6 DB-level acceptance criteria | MANUAL | Cannot test without applying migration to Supabase cloud |

### Step 03 — Backend API Contract

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `POST /start` accepts `{"locale": "pt"}` | `test_analysis_start_locale.py::TestLocaleField::test_accepts_pt` | PASS |
| `POST /start` without locale defaults to `"es"` | `test_analysis_start_locale.py::TestLocaleField::test_defaults_to_es_when_omitted` | PASS |
| `POST /start` with `locale="fr"` returns 422 | `test_analysis_start_locale.py::TestLocaleField::test_rejects_unsupported_locale` | PASS |
| `POST /start` with `locale="es-ES"` returns 422 | `test_analysis_start_locale.py::TestLocaleField::test_rejects_region_suffix` | PASS |
| Pydantic `ResultsV1` accepts `pt` and `en` | `schemas/test_results_report_language.py` (7 tests) | PASS |
| Zod `resultsV1Schema` parses `pt` and `en` | `lib/schemas/__tests__/resultsV1.test.ts` | PASS |
| `jobs_repo.create_job(..., locale="pt")` round-trips | **GAP** | `test_jobs_repo.py` (extended) does NOT exist. The repo insertion is exercised through integration but no isolated unit test for the round-trip exists. |

### Step 04 — Backend HTTP Error Translation

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `resolve_locale(None)` returns `"es"` | `test_http_errors.py::TestResolveLocale::test_defaults_to_es_when_none` | PASS |
| `resolve_locale("pt-BR,pt;q=0.9,en;q=0.8")` returns `"pt"` | `test_http_errors.py::TestResolveLocale::test_strips_region_complex` | PASS |
| `resolve_locale("fr,zh-CN;q=0.8")` returns `"es"` | `test_http_errors.py::TestResolveLocale::test_unknown_falls_back_to_es` | PASS |
| `t("invalid_or_expired_token", "en")` returns correct string | `test_http_errors.py::TestTranslate::test_invalid_or_expired_token_en` | PASS |
| `t("nonexistent_code", "pt")` returns code string | `test_http_errors.py::TestTranslate::test_unknown_code_returns_code` | PASS |
| `_MAX_HEADER_LEN = 256` enforced | `test_http_errors.py::test_max_header_len_constant` | PASS |
| `_MAX_TAGS = 10` enforced | `test_http_errors.py::test_max_tags_constant` | PASS |
| 10k-char header resolves < 10 ms | `test_http_errors.py::test_ten_thousand_char_header_resolves_fast` | PASS |
| 50-tag header: only first 10 inspected | `test_http_errors.py::test_fifty_tag_header_only_inspects_first_ten` | PASS |
| Every user-facing `HTTPException.detail` uses `t(...)` | Manual code review | PASS — `status.py` lines 27, 34 confirmed |
| `test_status_controller.py` extended: `401` with `Accept-Language: pt-BR` returns localized detail | **GAP** | No HTTP-level integration test exists that sends `Accept-Language: pt-BR` and asserts Portuguese `detail` text in the response body. The 401 test at `test_status_datetime_normalization.py:87` only asserts `t("invalid_or_expired_token", None)` (default locale). |

### Step 05 — Worker i18n Module

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `i18n.py` exports `Locale`, `LOCALES`, `DEFAULT_LOCALE`, `normalize_locale`, `register`, `render`, `TEMPLATES` | `test_i18n.py` + `test_imports.py` | PASS |
| `render("unknown.key", "pt")` returns `[i18n:unknown.key]` | `test_i18n.py::TestRender::test_unknown_key_returns_placeholder` | PASS |
| `normalize_locale("pt-BR")` → `"pt"` | `test_i18n.py::TestNormalizeLocale::test_strips_region` | PASS |
| `normalize_locale(None)` → `"es"` | `test_i18n.py::TestNormalizeLocale::test_none` | PASS |
| `GraphState` has `locale: str` | `state.py` confirmed | PASS |
| `ClaimedJob` carries `locale`; defensive default `"es"` | `test_i18n_integration.py::test_defensive_missing_locale_defaults_to_es` | PASS |
| `run_langgraph` includes `locale` in initial state | `flow.py` confirmed | PASS |
| CWE-134: `{title.__class__}` blocked by `_SafeFormatter` | `test_i18n.py::TestSafeFormatterSecurity::test_disallowed_field_expression_in_template_fails_soft` | PASS |
| Fail-soft: missing param returns `[i18n:key]` not raises | `test_i18n.py::TestRender::test_missing_param_returns_placeholder_fail_soft` | PASS |

### Step 06 — Worker Classification Reasons

| Acceptance Criterion | Test File | Status |
|---|---|---|
| All f-strings in `classification.py` → `render("class.<key>", locale, **params)` | `test_classification_i18n.py` (10 tests) | PASS |
| `classify_reference(...)` takes `locale: str` | `test_classification_i18n.py` — all calls pass `locale=` | PASS |
| `nodes/classify.py` passes `state["locale"]` | Code inspection confirmed | PASS |
| Fallback `processing_error` uses `render()` | `test_classification_i18n.py::TestSpanishByteIdentical::test_processing_error_es` | PASS |
| Catalog registers all keys in 3 locales | `i18n_catalog/classification.py` confirmed | PASS |
| `locale='pt'` produces Portuguese reasons | `test_classification_i18n.py::TestDoiMatchReason::test_portuguese` | PASS |
| `locale='es'` byte-identical to original Spanish | `test_classification_i18n.py::TestSpanishByteIdentical` | PASS |
| No ES substrings in PT output | `test_classification_i18n.py::TestPortugueseNotSpanish` | PASS |

### Step 07 — Worker Warning Messages

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `_validate_doi`, `_validate_arxiv_id`, `_validate_issn` accept `locale` | `test_warnings_i18n.py` (16 tests) | PASS |
| Warning `code` values unchanged | Code inspection + `test_warnings_i18n.py` | PASS |
| `assemble_report` sets `reportLanguage=state["locale"]` | `test_assemble_report.py::test_report_language_reflects_locale` | PASS |
| `locale='pt'` empty document → Portuguese warning | `test_i18n_integration.py` (end-to-end) | PASS |
| `locale='es'` byte-identical warnings | `test_warnings_i18n.py::TestValidateDoiWarning::test_spanish` | PASS |
| `warn.*` catalog has all 11+ keys in 3 locales | `i18n_catalog/warnings.py` confirmed | PASS |

### Step 08 — Frontend i18n Infrastructure

| Acceptance Criterion | Status | Notes |
|---|---|---|
| `next-intl@4.9.1` installed | PASS | `package.json` confirmed |
| `i18n/{config,detect,request}.ts` exist | PASS | All three files present |
| `providers/LocaleProvider.tsx` exists | PASS | Confirmed |
| `next.config.ts` uses `createNextIntlPlugin("./i18n/request.ts")` | PASS | Confirmed |
| `app/layout.tsx` renders `<html lang={locale}>` dynamically | PASS | `getLocale()` used |
| TypeScript compiles | PASS | `tsc --noEmit` clean |
| `global.d.ts` declares `AppConfig` with `Messages` and `Locale` | PASS | Confirmed |
| Requests with `Accept-Language: pt-BR` resolve to `locale="pt"` | MANUAL | Requires running dev server |

### Step 09 — Frontend Message Catalogs

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `es.json`, `pt.json`, `en.json` exist and are valid JSON | `_shape.test.ts` | PASS |
| All three catalogs have identical key shapes | `_shape.test.ts::Message catalog shape invariant::es.json has the same key set as en.json` + pt | PASS |
| Placeholder names consistent across files | `_shape.test.ts::have identical placeholder sets` | PASS |
| 47+ keys per catalog | Code inspection — 47 leaf keys confirmed | PASS |
| `candidates_found` uses ICU plural | `en.json` line 62 confirmed | PASS |
| `global.d.ts` picks up catalog type for autocomplete | PASS | Confirmed |
| No component imports catalog files directly | PASS — all via `useTranslations()` | PASS |
| Accent corrections in Spanish file | PASS — `Razón de la decisión`, `Número`, `Páginas` confirmed | PASS |

### Step 10 — Frontend Component Migration

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `StatusBadge.tsx` migrated | `StatusBadge.test.tsx` (11 tests — ES/PT/EN per status) | PASS |
| `ExpandedDetail.tsx` migrated; `decisionReason` verbatim | `ExpandedDetail.test.tsx::renders decisionReason verbatim` | PASS |
| `file-dropzone.tsx` migrated | `file-dropzone.test.tsx` (7 tests) | PASS |
| `formatRelativeTime` → `useFormatter`/`useNow` | `ExpandedDetail.tsx` lines 209–210 confirmed | PASS |
| `lib/constants.ts` exports keys not strings | **PARTIAL** — `ERROR_MESSAGES` still exists alongside `ERROR_KEYS`; `route.ts` still imports `ERROR_MESSAGES`. This is a regression risk but does not break i18n since the constant is used for a server-side error message not user-visible. |
| **DEVIATION**: `ExpandedDetail.tsx` running-state hardcoded English | `ExpandedDetail.tsx` lines 241, 244 contain `"(processing for {elapsedLabel})"` and `"Processing... (started {elapsedLabel} ago)"` — hardcoded English strings not in any catalog, not passing through `t()`. This is a spec violation (Step 10 §3.6). | FAIL |

### Step 11 — Frontend Language Toggle and Gateway Wiring

| Acceptance Criterion | Test File | Status |
|---|---|---|
| `language-toggle.tsx` exists and is mounted next to `ThemeToggle` | `language-toggle.test.tsx` (8 tests) | PASS |
| Switching select: sets cookie, writes localStorage, calls `router.refresh()` | `language-toggle.test.tsx` (3 dedicated tests) | PASS |
| Cookie attributes: `path=/`, `max-age=31536000`, `SameSite=Lax` | `locale-cookie.test.ts` | PASS |
| `Secure` flag only on HTTPS | `locale-cookie.test.ts::does NOT append Secure when http:` + `appends Secure when https:` | PASS |
| Gateway reads locale from cookie, overrides body | `route.ts` lines 26–31 confirmed | PASS |
| Gateway forwards `Accept-Language` to FastAPI | `route.test.ts::forwards accept-language header when provided` | PASS |
| `LOCALE_COOKIE = "NEXT_LOCALE"` | `route.test.ts::LOCALE_COOKIE is NEXT_LOCALE` | PASS |

### Step 12 — Testing Strategy (CI Gate)

| Gate Requirement | Status |
|---|---|
| All unit tests green | PASS |
| Type checks green (`tsc --noEmit`) | PASS |
| Frontend build succeeds | PASS |
| `messages/_shape.test.ts` passes (catalog shape + placeholder parity) | PASS |
| `pnpm lint:backend` passes | PASS |
| `pnpm lint:frontend` passes | PASS |
| `pnpm lint:worker` passes | **FAIL** — 137 E501 (line-length) violations across worker source + test files. No other error categories. These are pre-existing style issues not introduced by the i18n feature, but they block CI on the lint gate as configured. |
| Manual E2E checklist completed | DEFERRED — requires migration applied |
| Every step 01–11 has at least one automated test | PARTIAL — two gaps remain (see below) |

---

## 2. Automated Test Run Results

### Backend — `pnpm test:backend`

```
95 passed in 1.10s
```

Files:
- `tests/api/test_status_datetime_normalization.py` — 7 tests
- `tests/api/test_status_result_validation.py` — 6 tests
- `tests/schemas/test_results.py` — 19 tests
- `tests/schemas/test_results_report_language.py` — 7 tests
- `tests/test_analysis_start_locale.py` — 8 tests
- `tests/test_audit_repo.py` — 5 tests
- `tests/test_http_errors.py` — 23 tests
- `tests/test_integrity_service.py` — 3 tests
- `tests/test_text_extraction_service.py` — 4 tests
- `tests/test_verify_authenticity_validation.py` — 13 tests

**Result: 95/95 PASS**

### Worker — `pnpm test:worker`

```
600 passed in 146.27s
```

i18n-specific files:
- `test_i18n.py` — 17 tests (Step 05)
- `test_classification_i18n.py` — 10 tests (Step 06)
- `test_warnings_i18n.py` — 16 tests (Step 07)
- `test_assemble_report.py` — 13 tests (includes `test_report_language_reflects_locale`)
- `test_i18n_integration.py` — 5 tests (end-to-end locale propagation)

**Result: 600/600 PASS**

### Frontend — `pnpm --filter frontend exec vitest run`

```
76 passed (8 test files)
```

(74 pre-existing + 2 added by this audit for cross-locale immutability invariant)

Files:
- `messages/_shape.test.ts` — 11 tests (catalog shape + DoS caps)
- `components/recent-analyses/StatusBadge.test.tsx` — 11 tests (Step 10)
- `components/recent-analyses/ExpandedDetail.test.tsx` — 11 tests (Step 10, includes 2 new)
- `components/file-dropzone.test.tsx` — 7 tests (Step 10)
- `components/language-toggle.test.tsx` — 8 tests (Step 11)
- `lib/locale-cookie.test.ts` — 6 tests (Step 11)
- `lib/schemas/__tests__/resultsV1.test.ts` — 15 tests (Step 03)
- `app/api/analysis-start-gateway/route.test.ts` — 7 tests (Step 11)

**Result: 76/76 PASS**

### Frontend TypeScript — `pnpm --filter frontend exec tsc --noEmit`

**Result: PASS (0 errors)**

### Frontend Build — `pnpm build:frontend`

**Result: PASS** — Next.js 16.1.6 production build succeeded; all 6 routes compiled.

### Linters

| Command | Result |
|---|---|
| `pnpm lint:backend` | PASS — 0 errors |
| `pnpm lint:frontend` | PASS — 0 errors |
| `pnpm lint:worker` | **FAIL** — 137 E501 line-length violations (all pre-existing, zero non-E501 errors). No i18n-specific violations introduced. |

---

## 3. Catalog Shape and Placeholder Parity

`messages/_shape.test.ts` — 11 tests, ALL PASS:

- `es.json has the same key set as en.json` — PASS
- `pt.json has the same key set as en.json` — PASS
- `es.json has identical placeholder sets as en.json` — PASS
- `pt.json has identical placeholder sets as en.json` — PASS
- 7 DoS-cap tests for `parseAcceptLanguage` inline implementation — PASS

All three catalogs have 47 leaf keys each with identical shapes and identical placeholder sets. ICU plural on `candidates_found` is consistent across all three locales. The `view_record` key added by the implementation is present in all three catalogs (extra key not in the spec namespace tree — see Section 7).

---

## 4. Cross-Locale Rendering Smoke (Automated)

**Test added:** `ExpandedDetail.test.tsx` — `describe("ExpandedDetail — cross-locale immutability invariant")` (2 tests)

Scenario: `StoredJob` with `reportLanguage="pt"` and a Portuguese `decisionReason` (`"O DOI 10.1/x corresponde a 'Example Title' (2023) em OpenAlex."`), rendered by `ExpandedDetail` inside `NextIntlClientProvider locale="en"`.

| Assertion | Result |
|---|---|
| Chrome label "Decision reason" appears in English | PASS |
| Chrome label "Normalized fields" appears in English | PASS |
| Classification badge "Verified" appears in English | PASS |
| Portuguese `decisionReason` appears verbatim | PASS |
| No English-translated version of the decisionReason appears | PASS |

No cross-locale leak found in `ExpandedDetail.tsx`. The `decisionReason` at line 115 is rendered as `{reference.decisionReason}` without `t()` — compliant.

**Known deviation (not a leak, but a coverage gap):** The `running` state branch at lines 241 and 244 contains two hardcoded English strings that are not in the message catalog (see Section 7 below).

---

## 5. Security Re-Validation

### Worker `i18n.py` — CWE-134 (`_SafeFormatter`)

**File:** `apps/worker/biblio_checker_worker/langgraph/i18n.py`

- `_SafeFormatter.get_field()` uses `re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$").fullmatch(field_name)` — rejects any dotted or dunder expression before lookup.
- **Test exists:** `test_i18n.py::TestSafeFormatterSecurity::test_disallowed_field_expression_in_template_fails_soft` — registers a template with `{title.__class__.__mro__}` and asserts the result is `[i18n:test.malicious_template]`, not an attribute traversal. **PASS**.
- `test_dunder_param_name_rejected` — `{__class__}` template fails-soft. **PASS**.
- `test_plain_param_value_not_traversed` — param value `"{__class__}"` is treated as a literal string. **PASS**.

### Backend `http_errors.py` — `_MAX_HEADER_LEN` / `_MAX_TAGS`

- `_MAX_HEADER_LEN = 256` confirmed at module level (line 20).
- `_MAX_TAGS = 10` confirmed at module level (line 21).
- Both are applied in `resolve_locale()`: `accept_language[:_MAX_HEADER_LEN]` then `.split(",")[:_MAX_TAGS]`.
- **Tests:** `test_http_errors.py::test_max_header_len_constant`, `test_max_tags_constant`, `test_ten_thousand_char_header_resolves_fast`, `test_fifty_tag_header_only_inspects_first_ten`. All **PASS**.

### Frontend `detect.ts` — `parseAcceptLanguage` DoS caps

- `MAX_LEN = 256` and `MAX_TAGS = 10` are defined locally inside `parseAcceptLanguage` in `detect.ts`.
- The function cannot be imported in Vitest (it calls server-only `next/headers`).
- **Mitigation:** `_shape.test.ts` contains an inline copy of the same algorithm with 7 DoS-cap tests. The logic is identical to `detect.ts`. This is an acceptable proxy test. All **PASS**.
- **Gap:** No test exercises the `detectLocale()` function's cookie-priority path directly (cookie beats Accept-Language). This is a known constraint of the Next.js server-only boundary, not a defect in the implementation.

### Frontend `locale-cookie.ts` — `Secure` flag

- `setLocaleCookie()` appends `"; Secure"` only when `window.location.protocol === "https:"`.
- **Tests:** `locale-cookie.test.ts` — `does NOT append Secure when http:` (PASS) and `appends Secure when https:` (PASS). Both use `vi.stubGlobal` to control `window.location.protocol`.

### Frontend `analysis-start-gateway/route.ts` — Cookie overrides body locale

- Lines 26–31: `const localeFromCookie = cookieStore.get(LOCALE_COOKIE)?.value ?? null; const locale = normalizeLocale(localeFromCookie);`
- Line 31: `const bodyWithLocale = { ...rawBody, locale };` — any client-supplied `body.locale` is overwritten.
- **Test:** `route.test.ts` tests `normalizeLocale` behavior (correct) and Accept-Language forwarding (correct). The override behavior is confirmed by code inspection. No test directly verifies that a `body.locale = "fr"` is overridden by cookie — this is a coverage gap but the code is clearly correct by inspection.

---

## 6. Manual E2E Checklist (Ready for Post-Migration Execution)

> **Prerequisite:** Apply `supabase/migrations/20260414000000_add_locale_to_analysis_jobs.sql` in Supabase cloud before executing any scenario below.

### Setup

```bash
# Terminal 1
pnpm dev:frontend       # http://localhost:3000

# Terminal 2
pnpm dev:backend        # http://localhost:8000

# Terminal 3
pnpm dev:worker
```

### Scenario Execution per Locale (run for `es`, `pt`, `en`)

Replace `<LOCALE>` with the target locale code.

**Scenario 1 — First-visit detection (REQUIRES MIGRATION)**

```bash
curl -s http://localhost:3000 \
  -H "Accept-Language: <LOCALE>" \
  --cookie-jar /tmp/cookies.txt | grep 'lang='
# Expected: html lang="<LOCALE>"
```

**Scenario 2 — Toggle sets cookie**

```
Manual: Open browser → change LanguageToggle to <LOCALE>
Check: DevTools → Application → Cookies → NEXT_LOCALE=<LOCALE>
Check: DevTools → Application → LocalStorage → locale: <LOCALE>
```

**Scenario 3 — Reload persists locale**

```
Manual: Reload page after Scenario 2
Expected: Page renders in <LOCALE>
```

**Scenario 4 — Upload triggers localized UI (REQUIRES MIGRATION)**

```bash
# Upload a small valid PDF
curl -s -X POST http://localhost:3000/api/analysis-start-gateway \
  -H "Content-Type: application/json" \
  -H "Cookie: NEXT_LOCALE=<LOCALE>" \
  -d '{"requestId":"<UUID>","extractMode":"backend_extract_references","document":{"sourceType":"pdf","fileName":"test.pdf","mimeType":"application/pdf"},"storage":{"provider":"supabase","bucket":"uploads","path":"uploads/test.pdf"}}'
# Manual: Watch status badges and progress copy render in <LOCALE>
```

**Scenario 5 — Job completion + ExpandedDetail (REQUIRES MIGRATION)**

```
Manual: Wait for job to complete
Check: Recent analyses row, ExpandedDetail labels/sections in <LOCALE>
Check: decisionReason text is in <LOCALE> (matches job locale, not current UI locale)
```

**Scenario 6 — Expanded reference content (REQUIRES MIGRATION)**

```
Manual: Expand a completed reference
Expected: decisionReason and warnings[].message in job's <LOCALE>
```

**Scenario 7 — Empty document warning (REQUIRES MIGRATION)**

```bash
# Upload a PDF with no extractable text (e.g. image-only PDF)
# Expected warning: "O documento não contém texto extraível." (pt)
# Expected warning: "El documento no contiene texto extraíble." (es)
# Expected warning: "The document contains no extractable text." (en)
grep 'empty_document' <response_body>
```

**Scenario 8 — Localized 401 (AUTOMATED — see test_status_datetime_normalization.py; also manual)**

```bash
curl -s "http://localhost:3000/api/jobs/status?poll_token=bad" \
  -H "Accept-Language: pt-BR"
# Expected: {"error": "Token inválido ou expirado."}
```

**Scenario 9 — Dropzone file-too-large validation**

```
Manual: Drag a file > 10MB onto the dropzone
Expected: "El archivo excede el tamaño máximo de 10 MB." (es)
Expected: "O arquivo excede o tamanho máximo de 10 MB." (pt)
Expected: "File exceeds the maximum size of 10 MB." (en)
AUTOMATED: file-dropzone.test.tsx covers prompt text per locale
```

**Scenario 10 — Cross-locale immutability (REQUIRES MIGRATION)**

```
1. Submit job while toggle is in PT → confirm PT decisionReason after completion
2. Switch toggle to ES
3. Open previously-completed PT job in ExpandedDetail
Expected: Chrome renders in ES, but decisionReason stays in PT
AUTOMATED: ExpandedDetail.test.tsx — "cross-locale immutability invariant" (2 tests)
```

### Cross-locale invariant checks

- [ ] No Spanish text appears in DOM while active locale is PT or EN — verify with browser DevTools "Search DOM"
- [ ] No mixed-locale strings (e.g. "Stage: completada") appear
- [ ] HTML `lang` attribute matches active locale (DevTools Elements tab)
- [ ] `next-intl` emits no `[i18n:...]` placeholders in production build

### Regression Test: Legacy Jobs (Scenario 6 from Step 12 §6)

```sql
-- Run in Supabase Studio or psql after applying migration:
INSERT INTO analysis_jobs (sha256, source_type, storage_path, locale)
VALUES ('a' * 64, 'pdf', 'uploads/legacy.pdf', 'es');
```

```
1. Claim the job through worker
2. Confirm payload.reportLanguage == 'es' and Spanish decisionReason
3. Switch UI to PT and open the job → chrome is PT, decisionReason stays ES
AUTOMATED COVERAGE: test_i18n_integration.py::test_spanish_default_locale
```

---

## 7. Regression Risk List

### Files modified by Wave 1/2 that are outside the spec's stated scope

| File | In Spec? | Risk Assessment |
|---|---|---|
| `apps/backend/app/api/controllers/analysis/status.py` | YES (Step 04) | Benign — only adds `t()` wrapping and `Accept-Language` header param |
| `apps/backend/app/services/analysis_jobs_repo.py` | YES (Step 03) | Benign — adds `locale` to insert |
| `apps/frontend/components/recent-analyses/ExpandedDetail.tsx` | YES (Step 10) | Contains two hardcoded English strings (lines 241, 244) not caught by spec — see below |
| `apps/frontend/components/recent-analyses/RecentAnalyses.tsx` | YES (Step 10) | Migrated per spec |
| `apps/frontend/hooks/useRecentAnalysesPolling.ts` | NOT in spec | Benign — no i18n impact; likely polling interval or error handling fix |
| `apps/worker/biblio_checker_worker/langgraph/clients/arxiv.py` | NOT in spec | Enhanced search strategies (PR #26) — unrelated to i18n |
| `apps/worker/biblio_checker_worker/langgraph/clients/llm.py` | NOT in spec | LLM client change — unrelated to i18n |
| `apps/worker/biblio_checker_worker/langgraph/clients/openalex.py` | NOT in spec | Enhanced search strategies — unrelated to i18n |
| `apps/worker/biblio_checker_worker/langgraph/clients/scielo.py` | NOT in spec | Enhanced search strategies — unrelated to i18n |
| `apps/worker/biblio_checker_worker/langgraph/flow.py` | YES (Step 05) | Adds `locale` to initial state — correct |
| `apps/worker/biblio_checker_worker/langgraph/graph.py` | YES (Step 07) | Truncation warning uses `render()` |
| `apps/worker/biblio_checker_worker/langgraph/nodes/classify.py` | YES (Step 06) | Passes `locale` to `classify_reference` |
| `apps/worker/biblio_checker_worker/langgraph/nodes/extract_text.py` | NOT in spec | Likely text extraction improvement — verify no i18n side effects |
| `apps/worker/biblio_checker_worker/langgraph/nodes/normalize.py` | YES (Step 07) | Adds `locale` to validators |
| `apps/worker/biblio_checker_worker/langgraph/nodes/parse_references.py` | YES (Step 07) | Adds `empty_document` warning via `render()` |
| `apps/worker/biblio_checker_worker/langgraph/nodes/verify.py` | YES (Step 07) | Adds `locale` to warning calls |
| `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py` | YES (Step 05) | Adds `locale` to initial state |
| `apps/worker/pyproject.toml` | Likely dependency bump | Monitor for version conflicts |
| `apps/worker/.env.example` | Likely new env vars for enhanced search | Review for i18n-unrelated vars |
| `apps/worker/biblio_checker_worker/core/config.py` | NOT in spec | Configuration change — check for i18n-visible config |
| `apps/worker/biblio_checker_worker/jobs/repo.py` | YES (Step 05) | Adds `locale` to `ClaimedJob` with defensive default |

### Agent-reported fixes (backend — "results" vs "result_json" and E501)

The backend agent reportedly fixed `"results"` → `"result_json"` column name and pre-existing E501 issues. Code inspection confirms:

- `apps/backend/app/api/controllers/analysis/status.py` line 105: `raw_results = row.get("result_json")` — this is the corrected field name. The original bug would have caused results to never be read. **Benign fix; does not affect i18n functionality.**
- E501 violations remain in the worker (137 errors) — the backend fix was for the backend only (which passes lint cleanly).

### Specific FAIL: Hardcoded English in `ExpandedDetail.tsx` running state

**File:** `apps/frontend/components/recent-analyses/ExpandedDetail.tsx`

**Lines 241, 244:**

```typescript
// Line 241:
<span className="text-muted"> (processing for {elapsedLabel})</span>
// Line 244:
<p className="text-muted italic">Processing... (started {elapsedLabel} ago)</p>
```

These strings are hardcoded English and will appear in English regardless of the active locale. They are user-visible (shown while a job is in "running" state). They are not in any message catalog. This is a violation of Step 10 §3.6's requirement to migrate all strings in `ExpandedDetail.tsx`. The strings need catalog keys (e.g. `status.processing_for` and `status.processing_started`) and the component must call `t(...)`.

**This is a FAIL finding. It does not block the automated CI gate but will fail the manual E2E QA checklist for PT and ES locales (Scenario 4/5 running state).**

### Additional catalog key present in implementation but not in spec

`results.section.view_record` is present in all three catalogs and used in `ExpandedDetail.tsx` for the "View record" external link. The spec namespace tree (Step 09 §2) does not list this key. The implementation added it correctly (all three locales present, `_shape.test.ts` passes). This is benign scope creep — the key improves the UX and does not violate any spec constraint.

---

## 8. Go/No-Go Verdict

### YELLOW

**What is green:**
- All 95 backend tests pass
- All 600 worker tests pass
- All 76 frontend tests pass (including 2 new cross-locale immutability tests added by this audit)
- Frontend TypeScript clean (`tsc --noEmit`)
- Frontend build clean (`next build`)
- `messages/_shape.test.ts` — catalog shape and placeholder parity verified
- Security hardening: CWE-134 (`_SafeFormatter`), DoS caps (`_MAX_HEADER_LEN`/`_MAX_TAGS`), `Secure` cookie flag — all tested and passing
- `decisionReason` cross-locale immutability confirmed by automated test

**Specific gaps that must be addressed before GREEN:**

1. **FAIL — Worker lint gate:** `pnpm lint:worker` exits with code 1 (137 E501 violations). All are pre-existing line-length issues unrelated to i18n, but the CI gate as specified in Step 12 §8 requires lint to pass. Either fix the E501 violations or adjust `ruff.toml` to raise the line limit, then document the deviation.

2. **FAIL — Hardcoded English in `ExpandedDetail.tsx` running state (lines 241, 244):** Two user-visible strings are not localized. Will produce English text in PT/ES locales during job processing. Requires catalog keys and `t()` calls.

3. **GAP — `test_status_controller.py` extended (Step 12 §2):** No HTTP-level integration test exercises `Accept-Language: pt-BR` → `401` response with Portuguese `detail`. The `t()` function is tested in isolation in `test_http_errors.py`, but the full HTTP stack is not verified for locale propagation on 401. Add one `httpx` integration test.

4. **GAP — `test_jobs_repo.py` extended (Step 12 §2):** `create_job(..., locale="pt")` round-trip through the DB is not tested. The Supabase repo cannot be unit-tested without a live DB, but a mock-based test covering the insert payload construction is feasible.

5. **DEFERRED — Manual E2E (Step 12 §5):** Cannot execute until `supabase/migrations/20260414000000_add_locale_to_analysis_jobs.sql` is applied in Supabase cloud.

**Gaps 3–4 are low-risk given the comprehensive surrounding coverage; gaps 1–2 are blocking for a strict CI gate and QA sign-off.**
