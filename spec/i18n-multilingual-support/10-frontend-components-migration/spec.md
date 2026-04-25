# Step 10 — Frontend: Component Migration to `useTranslations()`

## Scope

- Replace every hardcoded user-facing string in frontend components with calls to `useTranslations()` / `getTranslations()` against the catalog created in Step 09.
- Migrate `lib/constants.ts` entries (`ERROR_MESSAGES`, `UPLOAD_MESSAGES`) from literal strings to **translation keys** that consumers resolve at call-site.
- Render result enums (`classification`, `confidenceBand`, `reasonCode`, `matchType`) via the catalog's `results.*` namespace.

**Out of scope:** The catalogs themselves (Step 09). The `LanguageToggle` UI (Step 11). Server-side detection (Step 08).

## Context

Step 09 provides a complete catalog. This step is a mechanical migration: each component receives a `const t = useTranslations("namespace")` at the top and each literal string is replaced. The tricky cases are:

- Components that currently consume `ERROR_MESSAGES.FILE_TOO_LARGE` from `lib/constants.ts` (constants returning already-resolved Spanish strings).
- `ExpandedDetail.tsx` which renders enum values (`reference.classification`) and currently has an inline Spanish map.
- Server Components vs. Client Components — they use different `next-intl` APIs.

## Requirements

### 1. Client vs. Server API

| Context | API |
|---------|-----|
| Client Components (`"use client"`) | `const t = useTranslations("namespace")` → `t("key")` / `t("key", { placeholder: value })` |
| Server Components (async, no `"use client"`) | `const t = await getTranslations("namespace")` (from `next-intl/server`) |
| Route Handlers (`app/api/**/route.ts`) | `const t = await getTranslations("namespace")` |
| Non-React modules (`lib/*`, utility fns) | **Do NOT** import `useTranslations` — export translation *keys* and let the calling component resolve them |

### 2. `lib/constants.ts` Migration

**Current shape (approximate):**

```typescript
export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: "El archivo excede el tamaño máximo de 10 MB.",
  UNSUPPORTED_FORMAT: "Solo se aceptan PDF y DOCX.",
  // ...
};
```

**New shape — keys instead of strings:**

```typescript
// apps/frontend/lib/constants.ts

export const ERROR_KEYS = {
  FILE_TOO_LARGE: "dropzone.validation_file_too_large",
  UNSUPPORTED_FORMAT: "dropzone.validation_unsupported_format",
  UPLOAD_FAILED: "errors.upload_failed",
  ANALYSIS_START_FAILED: "errors.analysis_start_failed",
  NETWORK_ERROR: "errors.network_error",
  INVALID_RESULTS_FORMAT: "errors.invalid_results_format",
} as const;

export type ErrorKey = (typeof ERROR_KEYS)[keyof typeof ERROR_KEYS];
```

At the call-site:

```typescript
// client component
import { useTranslations } from "next-intl";
import { ERROR_KEYS } from "@/lib/constants";

const t = useTranslations();
toast.error(t(ERROR_KEYS.FILE_TOO_LARGE));
```

**Rationale:** keeps the single source of truth in the catalog while letting non-React code (validators, utilities) still reference a stable identifier.

### 3. Component Migration Checklist

For each file below, apply the pattern and confirm with `grep -n "[A-Za-z].*\"[A-Z]"` that no literal user-facing strings remain.

#### 3.1 `apps/frontend/app/page.tsx`

```typescript
import { getTranslations } from "next-intl/server";

export default async function HomePage() {
  const t = await getTranslations();
  return (
    <main>
      <h1>{t("common.app_name")}</h1>
      <section>
        <h2>{t("home.hero_title")}</h2>
        <p>{t("home.hero_subtitle")}</p>
        {/* ... */}
      </section>
      <footer>{t("home.footer_tagline")}</footer>
    </main>
  );
}
```

#### 3.2 `apps/frontend/components/file-dropzone.tsx`

```typescript
"use client";
import { useTranslations } from "next-intl";
import { ERROR_KEYS } from "@/lib/constants";

export function FileDropzone() {
  const t = useTranslations();
  // ...
  function validate(file: File): string | null {
    if (file.size > MAX_SIZE) return t(ERROR_KEYS.FILE_TOO_LARGE);
    if (!ACCEPTED_TYPES.includes(file.type)) return t(ERROR_KEYS.UNSUPPORTED_FORMAT);
    return null;
  }
  return (
    <div>
      <p>{t("dropzone.prompt_primary")}</p>
      <p className="text-sm text-muted">{t("dropzone.prompt_secondary")}</p>
      <button onClick={onRemove}>{t("common.remove")}</button>
    </div>
  );
}
```

#### 3.3 `apps/frontend/components/upload-status.tsx`

```typescript
"use client";
import { useTranslations } from "next-intl";

export function UploadStatus({ fileName, status }: Props) {
  const t = useTranslations("upload");
  if (status === "uploading") return <p>{t("uploading", { fileName })}</p>;
  if (status === "success") return <p>{t("upload_success")}</p>;
  return null;
}
```

#### 3.4 `apps/frontend/components/recent-analyses/RecentAnalyses.tsx`

```typescript
"use client";
import { useTranslations } from "next-intl";

export function RecentAnalyses() {
  const t = useTranslations("recent");
  return (
    <section>
      <h2>{t("title")}</h2>
      <table>
        <thead>
          <tr>
            <th>{t("columns.file")}</th>
            <th>{t("columns.submitted")}</th>
            <th>{t("columns.status")}</th>
            <th>{t("columns.actions")}</th>
          </tr>
        </thead>
        {/* ... */}
      </table>
    </section>
  );
}
```

#### 3.5 `apps/frontend/components/recent-analyses/StatusBadge.tsx`

```typescript
"use client";
import { useTranslations } from "next-intl";
import type { JobStatus } from "@/lib/types";

const STATUS_TO_KEY: Record<JobStatus, string> = {
  queued: "status.queued",
  running: "status.running",
  succeeded: "status.succeeded",
  failed: "status.failed",
  expired: "status.expired",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const t = useTranslations();
  return <span className={statusClass(status)}>{t(STATUS_TO_KEY[status])}</span>;
}
```

Keep the existing CSS class-selection logic — only the rendered label changes.

#### 3.6 `apps/frontend/components/recent-analyses/ExpandedDetail.tsx`

This is the largest migration. Replace the inline `CLASSIFICATION_STYLES` label map with a derivation from the catalog:

```typescript
"use client";
import { useTranslations } from "next-intl";

const CLASSIFICATION_STYLES: Record<string, { border: string; bg: string; text: string }> = {
  verified:          { border: "border-green-500/40", bg: "bg-green-500/10", text: "text-green-500" },
  likely_verified:   { border: "border-blue-500/40",  bg: "bg-blue-500/10",  text: "text-blue-500"  },
  ambiguous:         { border: "border-amber-500/40", bg: "bg-amber-500/10", text: "text-amber-500" },
  not_found:         { border: "border-gray-400/40",  bg: "bg-gray-400/10",  text: "text-gray-400"  },
  suspicious:        { border: "border-red-500/40",   bg: "bg-red-500/10",   text: "text-red-500"   },
  processing_error:  { border: "border-orange-500/40", bg: "bg-orange-500/10", text: "text-orange-500" },
};

function ReferenceCard({ reference, expanded, onToggle }: Props) {
  const t = useTranslations();
  const style = CLASSIFICATION_STYLES[reference.classification] ?? CLASSIFICATION_STYLES.not_found;
  const classificationLabel = t(`results.classification.${reference.classification}`);
  const title = reference.normalized.title ?? reference.rawText.slice(0, 80);

  return (
    <div className={cn("rounded-lg border", style.border)}>
      <button type="button" onClick={onToggle} className="...">
        <span className={cn("...", style.bg, style.text)}>{classificationLabel}</span>
        {/* ... */}
      </button>

      {expanded && (
        <div>
          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.raw_text")}</p>
            <p>{reference.rawText}</p>
          </div>

          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.normalized_fields")}</p>
            <div>
              {reference.normalized.authors.length > 0 && (
                <Field label={t("results.fields.authors")} value={reference.normalized.authors.join("; ")} />
              )}
              {reference.normalized.year && <Field label={t("results.fields.year")} value={String(reference.normalized.year)} />}
              {reference.normalized.venue && <Field label={t("results.fields.venue")} value={reference.normalized.venue} />}
              {reference.normalized.publisher && <Field label={t("results.fields.publisher")} value={reference.normalized.publisher} />}
              {reference.normalized.doi && <Field label={t("results.fields.doi")} value={reference.normalized.doi} />}
              {reference.normalized.arxivId && <Field label={t("results.fields.arxiv_id")} value={reference.normalized.arxivId} />}
              {reference.normalized.issn && <Field label={t("results.fields.issn")} value={reference.normalized.issn} />}
              {reference.normalized.volume && <Field label={t("results.fields.volume")} value={reference.normalized.volume} />}
              {reference.normalized.issue && <Field label={t("results.fields.issue")} value={reference.normalized.issue} />}
              {reference.normalized.pages && <Field label={t("results.fields.pages")} value={reference.normalized.pages} />}
            </div>
          </div>

          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.decision_reason")}</p>
            <p>{reference.decisionReason}</p>  {/* already pre-translated by worker */}
          </div>

          {reference.evidence.length > 0 && (
            <div>
              <p className="text-muted font-medium mb-1">
                {t("results.section.candidates_found", { count: reference.evidence.length })}
              </p>
              {/* ... column headers ... */}
              <div>{t("results.section.reference")}</div>
              <div>{t("results.section.candidate")}</div>
              {/* ... */}
            </div>
          )}

          {reference.evidence.length === 0 && <p>{t("results.no_candidates")}</p>}
        </div>
      )}
    </div>
  );
}
```

**Key decision:** `reference.decisionReason` is rendered **as-is** — the worker has already localised it (Step 06). Do not wrap it in `t()`.

For pending states (`"Waiting to be processed..."`, `"Stage: "`, `"Analysis Result"`, `"References detected"`, `"References analyzed"`, `"Reference Details"`), use the `status.*` and `results.section.*` namespaces:

```typescript
if (status === "queued") return <p>{t("status.waiting")}</p>;
if (status === "running") return <p>{t("status.stage_label", { stage: currentStage })}</p>;
```

#### 3.7 `apps/frontend/components/recent-analyses/StorageErrorBanner.tsx`

```typescript
"use client";
import { useTranslations } from "next-intl";

export function StorageErrorBanner({ kind }: { kind: "full" | "corrupted" }) {
  const t = useTranslations("errors");
  const message = kind === "full" ? t("storage_full") : t("storage_corrupted");
  return <div role="alert">{message}</div>;
}
```

#### 3.8 `apps/frontend/components/recent-analyses/JobRow.tsx`

Migrate action labels and tooltips:

```typescript
<button aria-label={t("recent.actions.view_details")}>…</button>
<button aria-label={t("recent.actions.remove_job")}>…</button>
```

### 4. Non-Migrated Strings

The following strings are **not** translated and must remain as-is:

| String | Reason |
|--------|--------|
| File names, DOIs, arXiv IDs, ISSNs | User data |
| `reference.rawText` | User document content |
| `reference.normalized.*` field values | Extracted data |
| `reference.decisionReason` | Pre-translated by worker |
| Source names: `"OpenAlex"`, `"SciELO"`, `"arXiv"` | Proper nouns |
| Confidence scores, percentages | Numeric |
| Stage names from the worker (they are codes, but if displayed as-is keep them — unless a catalog key exists in `status.stage_label`) | Worker emits a short code; UI prefixes with a translated label via `status.stage_label` |

### 5. Formatting Dates and Times

`formatRelativeTime` / `formatElapsedTime` in `apps/frontend/lib/time.ts` currently produce English output (e.g. `"3 min ago"`). Migrate them to `next-intl`'s `useFormatter` / `useNow`:

```typescript
"use client";
import { useFormatter, useNow } from "next-intl";

const formatter = useFormatter();
const now = useNow({ updateInterval: 60_000 });
formatter.relativeTime(new Date(job.submittedAt), now); // "hace 3 min" / "há 3 min" / "3 min ago"
```

`next-intl` picks the language from the provider — no extra wiring needed.

Update the call sites (the recent analyses rows) to use these hooks instead of the custom helpers. Leave `formatElapsedTime` alone if it only produces short formatted strings (e.g. `"02:34"`); that is number formatting, not locale-dependent prose.

### 6. Testing Locale Context in Unit Tests

Wrap components rendered by tests in `NextIntlClientProvider` with the appropriate catalog. Add a helper:

```typescript
// apps/frontend/test-utils/renderWithLocale.tsx
import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import es from "@/messages/es.json";
import pt from "@/messages/pt.json";
import en from "@/messages/en.json";
import type { Locale } from "@/i18n/config";

const CATALOGS = { es, pt, en };

export function renderWithLocale(ui: React.ReactNode, locale: Locale = "es") {
  return render(
    <NextIntlClientProvider locale={locale} messages={CATALOGS[locale]}>
      {ui}
    </NextIntlClientProvider>,
  );
}
```

## Acceptance Criteria

- [ ] `grep -nE "['\"][A-Z][a-z]+(\s+[A-Z][a-z]+)+" apps/frontend/components apps/frontend/app` returns only styling class names and no user-facing prose literals.
- [ ] `lib/constants.ts` exports translation **keys**, not strings.
- [ ] `ExpandedDetail.tsx` renders classification, confidence band, reason code, and match-type labels from `results.*`.
- [ ] `reference.decisionReason` is rendered as plain text (not wrapped in `t()`).
- [ ] `formatRelativeTime` call sites use `next-intl` formatter.
- [ ] `pnpm --filter frontend exec tsc --noEmit` passes.
- [ ] `pnpm --filter frontend exec vitest run` passes with existing tests updated to use `renderWithLocale`.
- [ ] Manual check: set the `NEXT_LOCALE` cookie to `pt` and confirm every UI surface that was in English/Spanish is now in Portuguese.

## Edge Cases

| Scenario | Expected |
|----------|----------|
| New classification enum value not in catalog | Shows `[i18n:results.classification.xxx]` in dev, empty in prod; console warning logs missing key. |
| `reference.decisionReason` contains placeholders because the worker lacked a catalog entry (e.g. `"[i18n:class.doi_match.single.with_title]"`) | Rendered verbatim — alerts QA that the worker catalog is incomplete. |
| `count: 0` in `candidates_found` | Plural form `"No candidates"` / `"Nenhum candidato"` / `"Sin candidatos"` handled by ICU plural syntax in the catalog. |

## Dependencies

- **Depends on:** Step 08 (provider), Step 09 (catalogs).
- **Informs:** Step 11 (toggle will now have a fully translated app to switch).
