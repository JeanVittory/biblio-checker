import { LOCALE_COOKIE, type Locale } from "@/i18n/config";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 365; // 1 year

/**
 * Writes the NEXT_LOCALE cookie to document.cookie.
 * Appends Secure when running on HTTPS.
 * No-ops when called server-side (document is undefined).
 */
export function setLocaleCookie(locale: Locale): void {
  if (typeof document === "undefined") return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${MAX_AGE_SECONDS}; SameSite=Lax${secure}`;
}

/**
 * Reads the NEXT_LOCALE cookie value from document.cookie.
 * Returns null when not found or when called server-side.
 */
export function getLocaleCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${LOCALE_COOKIE}=([^;]+)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}
