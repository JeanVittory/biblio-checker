"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";

export function MarketingFooter() {
  const t = useTranslations();

  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-6xl px-6 py-12">
        {/* Link groups grid */}
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          {/* Product */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-foreground">
              {t("landing.footer.product" as Parameters<typeof t>[0])}
            </h3>
            <ul className="space-y-2 text-sm text-muted">
              <li>
                <Link href="/" className="transition-colors hover:text-foreground">
                  {t("landing.footer.home" as Parameters<typeof t>[0])}
                </Link>
              </li>
              <li>
                <Link href="/app" className="transition-colors hover:text-foreground">
                  {t("landing.footer.app" as Parameters<typeof t>[0])}
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-foreground">
              {t("landing.footer.resources" as Parameters<typeof t>[0])}
            </h3>
            <ul className="space-y-2 text-sm text-muted">
              <li>
                <a
                  href="#"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-foreground"
                >
                  {t("landing.footer.github" as Parameters<typeof t>[0])}
                </a>
              </li>
              <li>
                <a
                  href="#"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-foreground"
                >
                  {t("landing.footer.docs" as Parameters<typeof t>[0])}
                </a>
              </li>
              <li>
                <a
                  href="#"
                  rel="noopener noreferrer"
                  className="transition-colors hover:text-foreground"
                >
                  {t("landing.footer.about" as Parameters<typeof t>[0])}
                </a>
              </li>
            </ul>
          </div>

          {/* Language / Theme */}
          <div>
            <div className="flex items-center gap-2">
              <LanguageToggle />
              <ThemeToggle />
            </div>
          </div>
        </div>

        {/* Bottom copyright */}
        <div className="mt-12 border-t border-border pt-8 text-center text-xs text-muted">
          <p>{t("landing.footer.copyright" as Parameters<typeof t>[0])}</p>
          <p className="mt-1">{t("home.footer_tagline" as Parameters<typeof t>[0])}</p>
        </div>
      </div>
    </footer>
  );
}
