import type { ResultsV1 } from "@/lib/schemas/resultsV1";

/**
 * The `countsByClassification` object from `ResultsV1.summary`.
 * Reused from the resultsV1 schema so both stay in sync.
 */
export type CountsByClassification =
  ResultsV1["summary"]["countsByClassification"];

/** The return value of `computeScore`. */
export interface ScoreResult {
  score: number;
  band: "high" | "medium" | "low";
}

/**
 * Computes the Authenticity Score from a `countsByClassification` object.
 *
 * Formula (spec: momento-wow/02-authenticity-score-formula):
 *   eligible    = verified + likely_verified + ambiguous + not_found + suspicious
 *   weightedSum = (verified × 1.00) + (likely_verified × 0.75) + (ambiguous × 0.25)
 *   score       = Math.round((weightedSum / eligible) × 100)
 *
 * `processing_error` is excluded from both numerator and denominator.
 * When eligible is 0 the score is 0 and the band is "low".
 *
 * Band thresholds (inclusive):
 *   80–100 → "high"
 *   50–79  → "medium"
 *   0–49   → "low"
 */
export function computeScore(
  countsByClassification: CountsByClassification
): ScoreResult {
  const {
    verified,
    likely_verified,
    ambiguous,
    not_found,
    suspicious,
  } = countsByClassification;

  const eligible = verified + likely_verified + ambiguous + not_found + suspicious;

  if (eligible === 0) {
    return { score: 0, band: "low" };
  }

  const weightedSum =
    verified * 1.0 +
    likely_verified * 0.75 +
    ambiguous * 0.25 +
    not_found * 0.0 +
    suspicious * 0.0;

  const score = Math.round((weightedSum / eligible) * 100);

  const band: "high" | "medium" | "low" =
    score >= 80 ? "high" : score >= 50 ? "medium" : "low";

  return { score, band };
}
