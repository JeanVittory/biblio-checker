"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Globe } from "lucide-react";
import { LOCALES, LOCALE_LABELS, type Locale } from "@/i18n/config";
import { setLocaleCookie } from "@/lib/locale-cookie";

export function LanguageToggle() {
  const currentLocale = useLocale() as Locale;
  const t = useTranslations("common");
  const router = useRouter();

  // On first mount: reconcile any stale localStorage.locale → cookie divergence.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const stored = window.localStorage.getItem("locale");
      if (stored && stored !== currentLocale) {
        setLocaleCookie(stored as Locale);
        router.refresh();
      }
    } catch {
      // localStorage may be disabled; ignore.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
