# Step 08 — Frontend i18n Infrastructure (`next-intl` setup)

## Scope

- Install and wire `next-intl` in no-routing mode (no URL locale prefix).
- Add locale configuration files (`i18n/config.ts`, `i18n/request.ts`, `i18n/detect.ts`).
- Introduce a `LocaleProvider` client wrapper.
- Update `app/layout.tsx` to resolve the active locale on the server and render a dynamic `<html lang=...>`.

**Out of scope:** The message catalogs themselves (Step 09). Replacing hardcoded strings in components (Step 10). The `LanguageToggle` UI (Step 11).

## Context

Next.js 16 App Router + React 19 + Tailwind CSS 4 + TypeScript. `next-themes` is already in use for dark/light mode, and its pattern (cookie + `<html suppressHydrationWarning>`) is a good reference for handling something the server must know about before the first render.

`next-intl` supports both URL-prefixed routing and "static locale" mode. We want the latter: the user's locale is a cookie, not a URL segment.

## Requirements

### 1. Install Dependency

**File:** `apps/frontend/package.json`

```
pnpm --filter frontend add next-intl@latest
```

Pin to the version stable with Next.js 16. If CI surfaces a peer-dep warning, consult Context7 (`resolve-library-id` → `next-intl`) for the current compatible range.

### 2. Configure the Plugin

**File:** `apps/frontend/next.config.ts`

```typescript
import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const nextConfig: NextConfig = {
  // ... existing config
};

export default withNextIntl(nextConfig);
```

### 3. Locale Constants

**File:** `apps/frontend/i18n/config.ts` (new)

```typescript
export const LOCALES = ["es", "pt", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "es";
export const LOCALE_COOKIE = "NEXT_LOCALE";

export const LOCALE_LABELS: Record<Locale, string> = {
  es: "Español",
  pt: "Português",
  en: "English",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

export function normalizeLocale(value: string | null | undefined): Locale {
  if (!value) return DEFAULT_LOCALE;
  const base = value.toLowerCase().split("-")[0];
  return isLocale(base) ? base : DEFAULT_LOCALE;
}
```

### 4. Locale Detection (Server-Side)

**File:** `apps/frontend/i18n/detect.ts` (new)

```typescript
import { cookies, headers } from "next/headers";
import { DEFAULT_LOCALE, LOCALE_COOKIE, type Locale, normalizeLocale } from "./config";

/**
 * Detects the active locale from (in order):
 *   1. The NEXT_LOCALE cookie set by LanguageToggle.
 *   2. The Accept-Language header (highest-weighted supported tag).
 *   3. DEFAULT_LOCALE.
 * Safe to call from Server Components and route handlers.
 */
export async function detectLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const cookieValue = cookieStore.get(LOCALE_COOKIE)?.value;
  const fromCookie = normalizeLocale(cookieValue);
  if (cookieValue && fromCookie !== DEFAULT_LOCALE) return fromCookie;
  if (cookieValue) return fromCookie;

  const headerStore = await headers();
  const acceptLanguage = headerStore.get("accept-language");
  if (acceptLanguage) {
    const preferred = parseAcceptLanguage(acceptLanguage);
    if (preferred) return preferred;
  }
  return DEFAULT_LOCALE;
}

function parseAcceptLanguage(header: string): Locale | null {
  const entries = header
    .split(",")
    .map((part) => {
      const [tag, ...params] = part.trim().split(";");
      const qParam = params.find((p) => p.trim().startsWith("q="));
      const q = qParam ? parseFloat(qParam.split("=")[1]) : 1.0;
      return { tag: tag.toLowerCase(), q: Number.isFinite(q) ? q : 1.0 };
    })
    .sort((a, b) => b.q - a.q);

  for (const { tag } of entries) {
    const base = tag.split("-")[0];
    const normalized = normalizeLocale(base);
    if (normalized !== DEFAULT_LOCALE || base === "es") return normalized;
  }
  return null;
}
```

**Note:** the explicit `base === "es"` check avoids treating the fallback to `es` as a positive detection signal when the user's browser preference was actually `fr` or similar.

### 5. `next-intl` Request Config

**File:** `apps/frontend/i18n/request.ts` (new)

```typescript
import { getRequestConfig } from "next-intl/server";
import { detectLocale } from "./detect";
import type { AbstractIntlMessages } from "next-intl";

export default getRequestConfig(async () => {
  const locale = await detectLocale();
  const messages = (await import(`../messages/${locale}.json`))
    .default as AbstractIntlMessages;
  return {
    locale,
    messages,
    // ICU formatting config — pick one date format globally to keep diffs small
    formats: {
      dateTime: {
        short: {
          day: "numeric",
          month: "short",
          year: "numeric",
        },
      },
    },
    // Prevent crashes on missing keys; log instead.
    onError(err) {
      if (process.env.NODE_ENV !== "production") {
        console.warn("[i18n]", err.code, err.message);
      }
    },
    getMessageFallback({ key, namespace }) {
      const path = [namespace, key].filter(Boolean).join(".");
      return process.env.NODE_ENV !== "production" ? `[i18n:${path}]` : "";
    },
  };
});
```

### 6. Client Provider

**File:** `apps/frontend/providers/LocaleProvider.tsx` (new)

```typescript
"use client";

import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import type { Locale } from "@/i18n/config";

interface Props {
  locale: Locale;
  messages: AbstractIntlMessages;
  now?: Date;
  children: React.ReactNode;
}

export function LocaleProvider({ locale, messages, now, children }: Props) {
  return (
    <NextIntlClientProvider locale={locale} messages={messages} now={now}>
      {children}
    </NextIntlClientProvider>
  );
}
```

### 7. Update `app/layout.tsx`

**File:** `apps/frontend/app/layout.tsx`

```typescript
import { getMessages, getLocale } from "next-intl/server";
import { LocaleProvider } from "@/providers/LocaleProvider";
import type { Locale } from "@/i18n/config";

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = (await getLocale()) as Locale;
  const messages = await getMessages();
  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <LocaleProvider locale={locale} messages={messages}>
          {/* existing ThemeProvider and children */}
          {children}
        </LocaleProvider>
      </body>
    </html>
  );
}
```

- `<html lang={locale}>` replaces the hardcoded `lang="en"`.
- `suppressHydrationWarning` is already in use for theming — keep it.
- `getLocale()` is a `next-intl` server helper that reads from the request config (which calls `detectLocale()`).

### 8. TypeScript Module Declaration

**File:** `apps/frontend/global.d.ts` (create if missing; otherwise extend)

```typescript
import type en from "./messages/en.json";

declare global {
  type Messages = typeof en;
}

declare module "next-intl" {
  interface AppConfig {
    Messages: Messages;
    Locale: "es" | "pt" | "en";
  }
}
```

This gives `useTranslations("namespace")` full autocomplete against the English catalog (the most complete mirror — ensure Step 09 fills it exhaustively).

### 9. Do Not Use the `NextIntlClientProvider` Directly in Pages

Always go through `LocaleProvider` so that later adjustments (e.g. changing `now`, adding a default `timezone`) happen in a single place.

### 10. Hydration

Because the provider is populated on the server (cookie + header driven) and re-used on the client, there is no hydration mismatch in the normal flow. The only place where the UI *changes language dynamically* is the `LanguageToggle` (Step 11), which does a full navigation via `router.refresh()` after writing the cookie — so the server re-renders with the new locale.

## Acceptance Criteria

- [ ] `pnpm --filter frontend install` installs `next-intl`.
- [ ] `apps/frontend/i18n/{config,detect,request}.ts` exist and export the described helpers.
- [ ] `apps/frontend/providers/LocaleProvider.tsx` exists.
- [ ] `apps/frontend/next.config.ts` uses `createNextIntlPlugin("./i18n/request.ts")`.
- [ ] `app/layout.tsx` renders `<html lang={locale}>` dynamically and wraps children in `LocaleProvider`.
- [ ] Requests with `Accept-Language: pt-BR` and no cookie resolve to `locale="pt"` (confirmed via a simple Server Component that renders `{await getLocale()}`).
- [ ] Requests with `Accept-Language: fr` fall back to `locale="es"`.
- [ ] TypeScript compiles (`pnpm --filter frontend exec tsc --noEmit`).
- [ ] No user-facing string has been removed yet — all existing strings still render exactly as before (they will be migrated in Step 10).

## Verification

1. Add a temporary debug line in `app/page.tsx`: `<p data-testid="locale">{await getLocale()}</p>`.
2. `pnpm dev:frontend`.
3. With a `fr` Accept-Language override (browser devtools → Network Conditions), confirm the page shows `es`.
4. With `pt-BR`, confirm `pt`.
5. With `en`, confirm `en`.
6. Remove the debug line.

## Dependencies

- **Depends on:** Step 01 (locale model).
- **Informs:** Step 09 (catalogs), Step 10 (component migration), Step 11 (toggle writes `NEXT_LOCALE` cookie that `detectLocale()` already reads).
