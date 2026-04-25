import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ThemeToggle } from "@/components/theme-toggle";
import { LanguageToggle } from "@/components/language-toggle";
import { FEATURE_FLAGS, getFeatureFlag } from "@/lib/featureFlags";
import { FeatureLockedTooltip } from "@/components/ui/feature-locked-tooltip";

export async function MarketingHeader() {
  const t = await getTranslations();
  const uploadEnabled = await getFeatureFlag(FEATURE_FLAGS.UPLOAD_ENABLED);

  const ctaClasses =
    "hidden rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors sm:inline-flex";
  const ctaStyle = {
    background:
      "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
  };
  const ctaLabel = t("landing.hero.cta_primary");

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
          {/* "Try now" button — hidden on mobile (< 640px). Locked behind feature flag. */}
          {uploadEnabled ? (
            <Link href="/app" className={ctaClasses} style={ctaStyle}>
              {ctaLabel}
            </Link>
          ) : (
            <FeatureLockedTooltip
              message={t("featureLocked.uploadTooltip")}
              className="hidden sm:inline-flex"
            >
              <button
                type="button"
                disabled
                aria-disabled="true"
                className={`${ctaClasses} cursor-not-allowed opacity-60`}
                style={ctaStyle}
              >
                {ctaLabel}
              </button>
            </FeatureLockedTooltip>
          )}

          <LanguageToggle />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
