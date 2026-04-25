"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { computeScore } from "@/lib/computeScore";
import type { CountsByClassification } from "@/lib/computeScore";

export interface AuthenticityScoreProps {
  countsByClassification: CountsByClassification;
}

const BAND_SCORE_COLOR: Record<"high" | "medium" | "low", string> = {
  high: "text-green-500",
  medium: "text-amber-500",
  low: "text-red-500",
};

/**
 * Renders the Authenticity Score card for a succeeded analysis job.
 *
 * Spec: momento-wow/03-authenticity-score-component
 *
 * Placed between the 2-column summary grid and the classification breakdown
 * box inside ExpandedDetail.
 */
export function AuthenticityScore({ countsByClassification }: AuthenticityScoreProps) {
  const t = useTranslations();
  const { score, band } = computeScore(countsByClassification);

  const bandLabel = t(`results.score.${band}` as Parameters<typeof t>[0]);
  const title = t("results.score.title" as Parameters<typeof t>[0]);
  const ariaLabel = `${title}: ${score}, ${bandLabel}`;

  return (
    <div className="rounded-lg bg-surface border border-border p-3 text-center">
      <p className="text-xs text-muted font-medium mb-1">{title}</p>
      <p
        className={cn("text-3xl font-bold", BAND_SCORE_COLOR[band])}
        aria-label={ariaLabel}
      >
        {score}
      </p>
      <p className={cn("text-xs font-medium mt-1", BAND_SCORE_COLOR[band])}>
        {bandLabel}
      </p>
    </div>
  );
}
