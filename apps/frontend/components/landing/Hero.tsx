import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { getTranslations } from "next-intl/server";

/**
 * Hero section for the landing page.
 * Spec: landing-page/04-hero-section
 *
 * Server component — no client-side logic required.
 */
export async function Hero() {
  const t = await getTranslations();

  return (
    <section className="relative mx-auto max-w-4xl px-6 py-12 text-center sm:py-24">
      {/* Eyebrow */}
      <p className="mb-4 text-sm font-medium uppercase tracking-widest text-muted">
        {t("landing.hero.eyebrow" as Parameters<typeof t>[0])}
      </p>

      {/* Title — semantic h1, highest visual weight on the page */}
      <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
        {t("landing.hero.title" as Parameters<typeof t>[0])}
      </h1>

      {/* Subtitle */}
      <p className="mx-auto mt-6 max-w-2xl text-lg text-muted">
        {t("landing.hero.subtitle" as Parameters<typeof t>[0])}
      </p>

      {/* CTA group — side-by-side on desktop, stacked on mobile */}
      <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
        {/* Primary CTA — brand gradient */}
        <Link
          href="/app"
          className="inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg px-8 py-3 text-base font-semibold text-white transition-opacity hover:opacity-90 sm:w-auto"
          style={{
            background:
              "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
          }}
        >
          {t("landing.hero.cta_primary" as Parameters<typeof t>[0])}
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>

        {/* Secondary CTA — outlined / ghost style */}
        <Link
          href="/app?sample=1"
          className="inline-flex min-h-[44px] w-full items-center justify-center rounded-lg border border-border bg-surface px-8 py-3 text-base font-medium text-foreground transition-colors hover:border-accent/60 hover:text-accent sm:w-auto"
        >
          {t("landing.hero.cta_secondary" as Parameters<typeof t>[0])}
        </Link>
      </div>

      {/* Social proof line */}
      <p className="mt-8 text-sm text-muted">
        {t("landing.hero.socialProof" as Parameters<typeof t>[0])}
      </p>
    </section>
  );
}
