import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { FEATURE_FLAGS, getFeatureFlag } from "@/lib/featureFlags";
import { FeatureLockedTooltip } from "@/components/ui/feature-locked-tooltip";

/**
 * Final CTA section for the landing page.
 * Spec: landing-page/10-final-cta
 *
 * Server component — repeats the hero CTAs at the bottom of the page to
 * recapture visitors who read all content. Uses an accent-tinted background
 * to visually differentiate this section from neutral sections above.
 */
export async function FinalCTA() {
  const t = await getTranslations();
  const uploadEnabled = await getFeatureFlag(FEATURE_FLAGS.UPLOAD_ENABLED);

  const primaryCtaClasses =
    "inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg px-8 py-3 text-base font-semibold text-white transition-opacity hover:opacity-90 sm:w-auto";
  const primaryCtaStyle = {
    background:
      "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
  };
  const primaryLabel = t("landing.hero.cta_primary" as Parameters<typeof t>[0]);

  return (
    <section className="py-20 sm:py-24" style={{ background: "color-mix(in srgb, var(--accent) 8%, transparent)" }}>
      <div className="mx-auto max-w-4xl px-6 text-center">
        {/* Title */}
        <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          {t("landing.cta.title" as Parameters<typeof t>[0])}
        </h2>

        {/* Subtitle */}
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
          {t("landing.cta.subtitle" as Parameters<typeof t>[0])}
        </p>

        {/* CTA group — identical to Hero CTAs (same keys, same styles, same destinations) */}
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          {/* Primary CTA — brand gradient. Locked behind feature flag. */}
          {uploadEnabled ? (
            <Link href="/app" className={primaryCtaClasses} style={primaryCtaStyle}>
              {primaryLabel}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          ) : (
            <FeatureLockedTooltip
              message={t("featureLocked.uploadTooltip" as Parameters<typeof t>[0])}
              className="w-full sm:w-auto"
            >
              <button
                type="button"
                disabled
                aria-disabled="true"
                className={`${primaryCtaClasses} cursor-not-allowed opacity-60`}
                style={primaryCtaStyle}
              >
                {primaryLabel}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </FeatureLockedTooltip>
          )}

          {/* Secondary CTA — outlined / ghost style */}
          <Link
            href="/app?sample=1"
            className="inline-flex min-h-[44px] w-full items-center justify-center rounded-lg border border-border bg-surface px-8 py-3 text-base font-medium text-foreground transition-colors hover:border-accent/60 hover:text-accent sm:w-auto"
          >
            {t("landing.hero.cta_secondary" as Parameters<typeof t>[0])}
          </Link>
        </div>
      </div>
    </section>
  );
}
