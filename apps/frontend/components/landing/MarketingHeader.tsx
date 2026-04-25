import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";

export async function MarketingHeader() {
  const t = await getTranslations();

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        {/* Logo */}
        <Link href="/" className="text-lg font-bold tracking-tight">
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
            }}
          >
            Biblio Checker
          </span>
        </Link>

        {/* Right nav */}
        <nav className="flex items-center gap-3" aria-label="Marketing navigation">
          {/* "Try now" button — hidden on mobile (< 640px) */}
          <Link
            href="/app"
            className="hidden rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors sm:inline-flex"
            style={{
              background:
                "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
            }}
          >
            {t("landing.hero.cta_primary")}
          </Link>

          <LanguageToggle />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
