import { cookies, headers } from "next/headers";
import { DEFAULT_LOCALE, LOCALE_COOKIE, LOCALES, type Locale } from "./config";

/**
 * Detects the active locale from (in order):
 *   1. The NEXT_LOCALE cookie set by LanguageToggle.
 *   2. The Accept-Language header (highest-weighted supported tag, with DoS caps).
 *   3. DEFAULT_LOCALE.
 * Safe to call from Server Components and route handlers.
 */
export async function detectLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  const cookieValue = cookieStore.get(LOCALE_COOKIE)?.value;

  if (cookieValue) {
    const base = cookieValue.toLowerCase().split("-")[0];
    return (LOCALES as readonly string[]).includes(base)
      ? (base as Locale)
      : DEFAULT_LOCALE;
  }

  const headerStore = await headers();
  const acceptLanguage = headerStore.get("accept-language");
  if (acceptLanguage) {
    const preferred = parseAcceptLanguage(acceptLanguage);
    if (preferred) return preferred;
  }

  return DEFAULT_LOCALE;
}

function parseAcceptLanguage(header: string): Locale | null {
  const MAX_LEN = 256;
  const MAX_TAGS = 10;
  const safe = header.slice(0, MAX_LEN);
  const entries = safe
    .split(",")
    .slice(0, MAX_TAGS)
    .map((part) => {
      const [tag, ...params] = part.trim().split(";");
      const qParam = params.find((p) => p.trim().startsWith("q="));
      const q = qParam ? parseFloat(qParam.split("=")[1]) : 1.0;
      return { tag: tag.toLowerCase(), q: Number.isFinite(q) ? q : 1.0 };
    })
    .sort((a, b) => b.q - a.q);

  for (const { tag } of entries) {
    const base = tag.split("-")[0];
    if ((LOCALES as readonly string[]).includes(base)) return base as Locale;
  }
  return null;
}
