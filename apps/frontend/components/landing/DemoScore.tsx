"use client";

import { useTranslations } from "next-intl";
import { AuthenticityScore } from "@/components/recent-analyses/AuthenticityScore";
import type { CountsByClassification } from "@/lib/computeScore";

/**
 * Demo Score section for the landing page.
 * Spec: landing-page/07-demo-score
 *
 * CLIENT COMPONENT — required because AuthenticityScore uses hooks.
 * This component is a client island; the parent page remains server-rendered.
 *
 * Static data produces a score of 38 (low/red band), intentionally showing
 * that the product catches bibliographic issues.
 *
 * Formula check:
 *   eligible    = 2+1+1+3+1 = 8
 *   weightedSum = 2×1.0 + 1×0.75 + 1×0.25 = 3.0
 *   score       = round(3.0/8 × 100) = 38
 */

const DEMO_COUNTS: CountsByClassification = {
  verified: 2,
  likely_verified: 1,
  ambiguous: 1,
  not_found: 3,
  suspicious: 1,
  processing_error: 0,
};

/**
 * Classification entries shown in the breakdown list.
 * Ordered from most positive to most problematic, matching result display conventions.
 */
const BREAKDOWN_ENTRIES = [
  { key: "verified", count: DEMO_COUNTS.verified },
  { key: "likely_verified", count: DEMO_COUNTS.likely_verified },
  { key: "ambiguous", count: DEMO_COUNTS.ambiguous },
  { key: "not_found", count: DEMO_COUNTS.not_found },
  { key: "suspicious", count: DEMO_COUNTS.suspicious },
] as const;

export function DemoScore() {
  const t = useTranslations();

  return (
    <section className="py-16 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section heading */}
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {t("landing.demo.title" as Parameters<typeof t>[0])}
          </h2>
          <p className="mt-4 text-muted">
            {t("landing.demo.subtitle" as Parameters<typeof t>[0])}
          </p>
        </div>

        {/* Demo card — centered, max-w-md */}
        <div className="mx-auto max-w-md rounded-lg border border-border bg-surface p-6">
          {/* Authenticity Score component — real component with static data */}
          <AuthenticityScore countsByClassification={DEMO_COUNTS} />

          {/* Classification breakdown list */}
          <dl className="mt-4 space-y-2">
            {BREAKDOWN_ENTRIES.map(({ key, count }) => (
              <div
                key={key}
                className="flex items-center justify-between text-sm"
              >
                <dt className="text-muted">
                  {t(`results.classification.${key}` as Parameters<typeof t>[0])}
                </dt>
                <dd className="font-medium text-foreground">{count}</dd>
              </div>
            ))}
          </dl>

          {/* Caption — clarifies this is a demo */}
          <p className="mt-4 text-center text-xs text-muted">
            {t("landing.demo.caption" as Parameters<typeof t>[0])}
          </p>
        </div>
      </div>
    </section>
  );
}
