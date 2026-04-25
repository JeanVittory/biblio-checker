# Step 12 — Testing Strategy and Release Gate

## Scope

- Define the complete test matrix for the i18n feature across worker, backend, and frontend.
- Specify the manual E2E QA checklist executed before merging.
- Define the rollout gate: what must be green before the `main` merge.

**Out of scope:** Defining new unit tests beyond what's described in Steps 03–11 (each step contributes its own tests); this step assembles and augments them.

## Context

i18n touches every layer. Testing has to cover: (a) each locale alone produces the right text, (b) no locale mixing occurs (a page rendered in PT does not leak ES strings), (c) locale is preserved end-to-end from toggle → request → DB → worker → payload → UI.

## Requirements

### 1. Worker Unit Tests

**Location:** `apps/worker/tests/`

| Test file | Step | Coverage |
|-----------|------|----------|
| `test_i18n.py` | 05 | `normalize_locale`, `render()` fallback chain, missing-key/missing-param behaviour |
| `test_classification_i18n.py` | 06 | Each classification rule produces the right reason string in ES/PT/EN |
| `test_warnings_i18n.py` | 07 | `_validate_doi/_arxiv/_issn` return localised warning messages |
| `test_assemble_report.py` (extended) | 07 | `reportLanguage` in final payload matches `state["locale"]` |
| `test_langgraph_integration.py` (extended) | 05–07 | Running the full graph with `locale="pt"` produces a Portuguese payload (no ES leakage) |

**Parameterise over locales.** Use pytest parametrization to avoid duplicating assertion bodies:

```python
@pytest.mark.parametrize("locale,expected_fragment", [
    ("es", "El DOI"),
    ("pt", "O DOI"),
    ("en", "DOI "),
])
def test_doi_reason_is_localised(locale, expected_fragment, ...):
    ...
```

**Run with:** `pnpm test:worker` (from repo root).

### 2. Backend Unit Tests

**Location:** `apps/backend/tests/`

| Test file | Step | Coverage |
|-----------|------|----------|
| `test_analysis_start.py` | 03 | `locale` accepted, defaulted, validated, rejected region suffix |
| `test_results_schema.py` | 03 | `reportLanguage` accepts `es\|pt\|en`, rejects others |
| `test_http_errors.py` | 04 | `resolve_locale`, `t(code, header)` returns the right string per locale |
| `test_status_controller.py` (extended) | 04 | 401 and 503 responses carry localised `detail` per `Accept-Language` |
| `test_jobs_repo.py` (extended) | 03 | `create_job(..., locale="pt")` round-trips the value |

**Run with:** `pnpm test:backend`.

### 3. Frontend Unit / Component Tests

**Location:** `apps/frontend/**/*.test.ts(x)`

| Test file | Step | Coverage |
|-----------|------|----------|
| `components/recent-analyses/StatusBadge.test.tsx` | 10 | Renders each status in ES/PT/EN using `renderWithLocale` |
| `components/recent-analyses/ExpandedDetail.test.tsx` | 10 | Classification label, field labels, section headings per locale; `decisionReason` passes through unchanged |
| `components/file-dropzone.test.tsx` | 10 | Validation messages localise correctly on oversized/bad-type file |
| `components/language-toggle.test.tsx` | 11 | Changing the select sets cookie + localStorage; calls `router.refresh()` |
| `i18n/detect.test.ts` | 08 | Cookie beats header; header beats default; unknown falls back to `es` |
| `lib/schemas/resultsV1.test.ts` (extended) | 03 | Schema parses `reportLanguage` as `es\|pt\|en` |
| `app/api/analysis-start-gateway/route.test.ts` | 11 | Gateway injects `locale` from cookie, overrides client-supplied locale |
| `messages/_shape.test.ts` (new) | 09 | `es`, `pt`, `en` catalogs have identical key shapes and identical placeholder sets |

**Message-shape test (`messages/_shape.test.ts`):**

```typescript
import { describe, it, expect } from "vitest";
import es from "./es.json";
import pt from "./pt.json";
import en from "./en.json";

function flatKeys(obj: unknown, prefix = ""): string[] {
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
      flatKeys(v, prefix ? `${prefix}.${k}` : k),
    );
  }
  return [prefix];
}

function placeholders(str: string): string[] {
  return Array.from(str.matchAll(/\{([a-zA-Z0-9_]+)(?:,[^}]+)?\}/g), (m) => m[1]).sort();
}

function flatLeaves(obj: unknown, prefix = ""): Record<string, string> {
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    return Object.entries(obj as Record<string, unknown>).reduce<Record<string, string>>((acc, [k, v]) => {
      Object.assign(acc, flatLeaves(v, prefix ? `${prefix}.${k}` : k));
      return acc;
    }, {});
  }
  if (typeof obj === "string") return { [prefix]: obj };
  return {};
}

describe("message catalogs", () => {
  it("have identical key shapes", () => {
    expect(flatKeys(en).sort()).toEqual(flatKeys(es).sort());
    expect(flatKeys(en).sort()).toEqual(flatKeys(pt).sort());
  });

  it("have consistent placeholders per key", () => {
    const enLeaves = flatLeaves(en);
    const esLeaves = flatLeaves(es);
    const ptLeaves = flatLeaves(pt);
    for (const key of Object.keys(enLeaves)) {
      const ePh = placeholders(enLeaves[key]);
      const sPh = placeholders(esLeaves[key] ?? "");
      const pPh = placeholders(ptLeaves[key] ?? "");
      expect(sPh, `mismatch at es:${key}`).toEqual(ePh);
      expect(pPh, `mismatch at pt:${key}`).toEqual(ePh);
    }
  });
});
```

**Run with:** `pnpm --filter frontend exec vitest run`.

### 4. Type Checking

| Check | Command |
|-------|---------|
| Frontend TS | `pnpm --filter frontend exec tsc --noEmit` |
| Backend Python | (ruff) `pnpm lint:backend` |
| Worker Python | (ruff) `pnpm lint:worker` |

All must pass.

### 5. End-to-End Manual QA Checklist

This checklist is executed by a human (or automated via Playwright in a future iteration) before merging the feature.

**Setup:**

```
pnpm dev:frontend
pnpm dev:backend
pnpm dev:worker
```

**Per-locale scenarios — run the full list for each of `es`, `pt`, `en`:**

| # | Action | Expected |
|---|--------|----------|
| 1 | Open fresh browser (no cookies) with `Accept-Language: <locale>` | Landing page renders in `<locale>` |
| 2 | Change `LanguageToggle` to `<locale>` (if not already) | All chrome re-renders; cookie `NEXT_LOCALE=<locale>` set |
| 3 | Reload the page | Locale persists |
| 4 | Upload a small valid PDF | Status badges, progress copy, and toasts all in `<locale>` |
| 5 | Wait for job completion | Recent analyses row, `ExpandedDetail` labels/sections in `<locale>` |
| 6 | Expand a reference | `decisionReason` and `warnings[].message` also in `<locale>` |
| 7 | Upload an empty-text PDF (or trigger `empty_document` warning) | Warning message in `<locale>` |
| 8 | Force an invalid `poll_token` (devtools) | 401 JSON `detail` in `<locale>` |
| 9 | Upload a > 10 MB file | Dropzone validation message in `<locale>` |
| 10 | Set toggle to a *different* locale, then expand a previously-completed job | Chrome changes language, but `decisionReason` stays in the job's original locale (immutability) |

**Cross-locale invariant checks:**

- [ ] No Spanish text appears anywhere while the active locale is PT or EN (grep-equivalent scan of the DOM is acceptable).
- [ ] No mixed-locale strings ("Stage: completada") appear.
- [ ] The HTML `lang` attribute matches the active locale.
- [ ] `next-intl` does not emit `[i18n:...]` placeholders in production builds.

### 6. Regression Test: Legacy Jobs

An analysis job created **before** the migration (with `locale = 'es'` from the column default) must continue to work:

1. Manually insert a row with `locale='es'` and no changes to code.
2. Claim and process it. Confirm the payload has `reportLanguage='es'` and Spanish content.
3. Render it in the UI while the active locale is PT — chrome is PT, embedded worker text is ES. This is the documented behaviour.

### 7. Performance Smoke

- Worker: verify that `render()` adds negligible overhead — benchmark by running the full pipeline with the i18n catalog cold vs. warm. Expected < 1 ms per reference.
- Frontend: confirm the addition of `next-intl` does not regress First Contentful Paint by more than 50 ms locally (rough sanity check via Chrome DevTools).

### 8. CI Gating

Before merging to `main` (or `develop`):

- [ ] All unit tests green: `pnpm test:worker`, `pnpm test:backend`, `pnpm --filter frontend exec vitest run`.
- [ ] Type checks green: `pnpm lint:worker`, `pnpm lint:backend`, `pnpm --filter frontend exec tsc --noEmit`, `pnpm lint:frontend`.
- [ ] Frontend build succeeds: `pnpm build:frontend`.
- [ ] The `messages/_shape.test.ts` assertion passes — i.e. all three catalogs have identical key shape and placeholder sets.
- [ ] Manual E2E checklist (Section 5) completed for all three locales and documented in the PR.
- [ ] `CLAUDE.md` updated if any repository-wide convention changed (e.g. "all new user-facing strings must have a catalog key").

## Acceptance Criteria

- [ ] Every step in this suite (01–11) has at least one automated test referenced in the table above.
- [ ] The catalog shape test is part of the CI run — missing keys in one locale break the build.
- [ ] The E2E manual checklist is attached to the PR as a completed checkbox list.

## Dependencies

- **Depends on:** All prior steps in this suite (tests reference their implementations).
- **Informs:** — (terminal step)
