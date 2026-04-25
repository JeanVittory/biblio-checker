# Step 11 — Frontend: `LanguageToggle` and Analysis-Start Wiring

## Scope

- Add a `LanguageToggle` client component in the header, next to `ThemeToggle`.
- Persist the user's choice to `localStorage` and the `NEXT_LOCALE` cookie, then trigger a router refresh so server components pick up the new locale.
- Propagate the active locale through `POST /api/analysis-start-gateway` → FastAPI `/api/analysis/start`, so newly-created jobs have the right `locale` value.
- Provide a small `locale-cookie.ts` helper used by the toggle.

**Out of scope:** Backend contract (Step 03). Catalog contents (Steps 09). Component migration (Step 10).

## Context

After Step 10, the app renders fully in whatever locale `detectLocale()` resolves (Step 08). To let users **change** that choice we need:

1. A UI affordance (the toggle).
2. A way to persist the choice server-side for SSR (cookie) and client-side for UX consistency (localStorage).
3. A way to tell the backend which locale to use when starting an analysis.

## Requirements

### 1. Cookie Helper

**File:** `apps/frontend/lib/locale-cookie.ts` (new)

```typescript
import { LOCALE_COOKIE, type Locale } from "@/i18n/config";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 365; // 1 year

export function setLocaleCookie(locale: Locale) {
  if (typeof document === "undefined") return;
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function getLocaleCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${LOCALE_COOKIE}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}
```

### 2. The Toggle Component

**File:** `apps/frontend/components/language-toggle.tsx` (new)

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { LOCALES, LOCALE_LABELS, type Locale } from "@/i18n/config";
import { setLocaleCookie } from "@/lib/locale-cookie";

export function LanguageToggle() {
  const currentLocale = useLocale() as Locale;
  const t = useTranslations("common");
  const router = useRouter();

  function onChange(locale: Locale) {
    if (locale === currentLocale) return;
    setLocaleCookie(locale);
    try {
      window.localStorage.setItem("locale", locale);
    } catch {
      // Storage may be disabled — cookie alone is enough for SSR.
    }
    router.refresh();
  }

  return (
    <div className="relative">
      <label htmlFor="language-toggle" className="sr-only">
        {t("language_label")}
      </label>
      <div className="flex items-center gap-2">
        <Globe className="h-4 w-4 text-muted" aria-hidden />
        <select
          id="language-toggle"
          value={currentLocale}
          onChange={(e) => onChange(e.target.value as Locale)}
          className="bg-transparent border-0 text-sm focus-visible:ring-2 focus-visible:ring-ring rounded px-1"
          aria-label={t("language_label")}
        >
          {LOCALES.map((loc) => (
            <option key={loc} value={loc}>
              {LOCALE_LABELS[loc]}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
```

Design notes:

- A `<select>` keeps the component accessible and trivially keyboard-navigable — no custom dropdown needed.
- `router.refresh()` re-runs Server Components (including `getLocale()` in `layout.tsx`) so the new locale takes effect everywhere without a hard reload.
- `localStorage` is written as a *nice-to-have* fallback (some browsers may block cookies but allow localStorage); detection reads cookie first anyway.

### 3. Placement

Edit wherever the `ThemeToggle` is currently mounted (header component — grep for `ThemeToggle`). Add the toggle as a sibling:

```tsx
<div className="flex items-center gap-2">
  <LanguageToggle />
  <ThemeToggle />
</div>
```

Do not place it in `app/page.tsx` directly — it belongs to the persistent chrome.

### 4. Syncing localStorage → Cookie on First Load

Users who had a previous session may have a `locale` key in `localStorage` but no cookie (because cookies were never used before). On first mount of `LanguageToggle`, sync them:

```typescript
import { useEffect } from "react";

useEffect(() => {
  if (typeof window === "undefined") return;
  const stored = window.localStorage.getItem("locale");
  if (stored && stored !== currentLocale) {
    // Don't hard-redirect; just set the cookie so the next server render matches.
    setLocaleCookie(stored as Locale);
    router.refresh();
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, []);
```

Run only once on mount.

### 5. Gateway Locale Forwarding

**File:** `apps/frontend/app/api/analysis-start-gateway/route.ts`

Currently the gateway receives a JSON body (sha256, source_type, storage_path) and forwards it to FastAPI. Extend it to read the locale from the cookie and include it in the outbound request:

```typescript
import { cookies } from "next/headers";
import { LOCALE_COOKIE, normalizeLocale } from "@/i18n/config";

export async function POST(request: Request) {
  const body = await request.json();
  const cookieStore = await cookies();
  const localeFromCookie = cookieStore.get(LOCALE_COOKIE)?.value ?? null;
  const locale = normalizeLocale(localeFromCookie);

  const response = await fetch(`${process.env.BACKEND_URL}/api/analysis/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept-Language": request.headers.get("accept-language") ?? "",
    },
    body: JSON.stringify({ ...body, locale }),
  });
  // ... existing response handling
}
```

**Important:** do not trust the client-supplied `body.locale` if it is present — always override with the cookie-resolved one. The cookie is what the server already used to render the current page; using it as the source of truth prevents desynchronisation ("UI shows PT but user submitted with ES").

Propagate `Accept-Language` verbatim so that backend HTTP errors (Step 04) also come back in the user's language even when the job doesn't exist yet (e.g. storage token expired before insert).

### 6. Submit-Time Locale Race Condition

If the user changes the toggle *while an upload is in progress*, the analysis-start-gateway will pick up the **new** locale because the cookie is already set. This is acceptable — the user explicitly asked for that language, so rendering the resulting analysis in it is the correct outcome.

Do not lock the toggle during upload; the cost of a small edge-case desync does not justify the UX penalty.

### 7. `NEXT_LOCALE` Cookie Attributes

- `path=/` — available to all routes.
- `max-age=31536000` (1 year) — long-lived explicit preference.
- `SameSite=Lax` — defaults are safe and allow the cookie to accompany `fetch` inside the same-origin gateway.
- `HttpOnly=false` — the client component needs to read it via `document.cookie` to keep UI state in sync.
- `Secure` — set by Next.js automatically on HTTPS. No manual toggle needed.

### 8. Accessibility

- The `<select>` has an associated `<label>` (visually hidden) so screen readers announce "Language, combobox, Español".
- The `Globe` icon has `aria-hidden` — it is decorative; the select is the control.
- Ensure focus styling matches the `ThemeToggle` for consistency.

## Acceptance Criteria

- [ ] `apps/frontend/components/language-toggle.tsx` exists and is mounted next to `ThemeToggle` in the header.
- [ ] Switching the `<select>` value sets the `NEXT_LOCALE` cookie, writes `localStorage.locale`, and triggers `router.refresh()`.
- [ ] After a switch to `pt`, `document.cookie` contains `NEXT_LOCALE=pt` and every visible string re-renders in Portuguese.
- [ ] A new analysis started *after* the toggle lands in the DB with `analysis_jobs.locale = 'pt'`.
- [ ] The worker processes that job and emits a payload with `reportLanguage = "pt"` and Portuguese `decisionReason` / warning messages.
- [ ] HTTP error responses (e.g. expired poll token) come back in the user's language thanks to `Accept-Language` forwarding.
- [ ] Accessibility: the toggle is reachable by keyboard and announces its label.

## Manual Verification Steps

1. `pnpm dev:frontend` + `pnpm dev:backend` + `pnpm dev:worker`.
2. Open the app in a fresh browser profile with browser language `en-US`. Expect English UI.
3. Switch the toggle to Portuguese. Confirm the page re-renders in PT without a full reload.
4. Upload a valid PDF. Confirm the recent analyses row and the expanded detail render in PT, including `decisionReason` and `warnings[].message` after the job completes.
5. Reload the page. Confirm it stays in PT (cookie persistence).
6. Open DevTools → Application → Cookies and confirm `NEXT_LOCALE=pt`.
7. Open DevTools → Application → Local Storage and confirm `locale: pt`.
8. Switch to ES and re-upload a file; confirm the **new** analysis comes back in ES while the previously-submitted PT analysis still shows PT text (locale immutability per job).

## Dependencies

- **Depends on:** Step 03 (backend accepts `locale`), Step 10 (the app is fully translated — otherwise the toggle has nothing to toggle).
- **Informs:** Step 12 (test matrix covers the toggle + end-to-end locale propagation).
