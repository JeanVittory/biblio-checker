/**
 * Zod validation schema for Results Contract v1.
 *
 * The discriminated union on `classification` enforces the compatibility
 * matrix defined in the spec: each classification variant fixes the allowed
 * confidenceBand values and the manualReviewRequired literal.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Leaf schemas (shared across union branches)
// ---------------------------------------------------------------------------

const normalizedReferenceSchema = z.object({
  title: z.string().nullable(),
  authors: z.array(z.string()),
  year: z.number().int().nullable(),
  venue: z.string().nullable(),
  doi: z.string().nullable(),
  arxivId: z.string().nullable(),
});

const matchedRecordSchema = z.object({
  externalId: z.string(),
  title: z.string().nullable(),
  year: z.number().int().nullable(),
  doi: z.string().nullable(),
  url: z.string().nullable(),
});

const evidenceItemSchema = z.object({
  source: z.string(),
  matchType: z.string(),
  score: z.number().min(0).max(1),
  matchedRecord: matchedRecordSchema,
});

const reasonCodeSchema = z.enum([
  "exact_doi_match",
  "exact_identifier_match",
  "strong_metadata_match",
  "multiple_plausible_candidates",
  "insufficient_metadata",
  "no_match_any_source",
  "strong_doi_conflict",
  "cross_source_metadata_conflict",
  "source_timeout_partial",
  "reference_processing_failure",
]);

// ---------------------------------------------------------------------------
// Shared fields for all ReferenceResult branches (excluding the discriminated
// fields: classification, confidenceBand, confidenceScore, manualReviewRequired)
// ---------------------------------------------------------------------------

const referenceResultBaseSchema = {
  referenceId: z.string(),
  rawText: z.string(),
  normalized: normalizedReferenceSchema,
  reasonCode: reasonCodeSchema,
  decisionReason: z.string(),
  evidence: z.array(evidenceItemSchema),
};

// ---------------------------------------------------------------------------
// Compatibility matrix — one branch per classification value
//
// verified        → confidenceBand ∈ { high, very_high }, manualReviewRequired=false
// likely_verified → confidenceBand ∈ { medium, high },    manualReviewRequired=false
// ambiguous       → confidenceBand ∈ { low, medium },     manualReviewRequired=true
// not_found       → confidenceBand ∈ { very_low, low },   manualReviewRequired=true
// suspicious      → confidenceBand ∈ { medium, high, very_high }, manualReviewRequired=true
// processing_error → confidenceBand=null, confidenceScore=null,   manualReviewRequired=true
// ---------------------------------------------------------------------------

const verifiedBranchSchema = z.object({
  ...referenceResultBaseSchema,
  classification: z.literal("verified"),
  confidenceScore: z.number().min(0).max(1).nullable(),
  confidenceBand: z.enum(["high", "very_high"]),
  manualReviewRequired: z.literal(false),
});

const likelyVerifiedBranchSchema = z.object({
  ...referenceResultBaseSchema,
  classification: z.literal("likely_verified"),
  confidenceScore: z.number().min(0).max(1).nullable(),
  confidenceBand: z.enum(["medium", "high"]),
  manualReviewRequired: z.literal(false),
});

const ambiguousBranchSchema = z.object({
  ...referenceResultBaseSchema,
  classification: z.literal("ambiguous"),
  confidenceScore: z.number().min(0).max(1).nullable(),
  confidenceBand: z.enum(["low", "medium"]),
  manualReviewRequired: z.literal(true),
});

const notFoundBranchSchema = z.object({
  ...referenceResultBaseSchema,
  classification: z.literal("not_found"),
  confidenceScore: z.number().min(0).max(1).nullable(),
  confidenceBand: z.enum(["very_low", "low"]),
  manualReviewRequired: z.literal(true),
});

const suspiciousBranchSchema = z.object({
  ...referenceResultBaseSchema,
  classification: z.literal("suspicious"),
  confidenceScore: z.number().min(0).max(1).nullable(),
  confidenceBand: z.enum(["medium", "high", "very_high"]),
  manualReviewRequired: z.literal(true),
});

const processingErrorBranchSchema = z.object({
  ...referenceResultBaseSchema,
  classification: z.literal("processing_error"),
  confidenceScore: z.null(),
  confidenceBand: z.null(),
  manualReviewRequired: z.literal(true),
});

const referenceResultSchema = z.discriminatedUnion("classification", [
  verifiedBranchSchema,
  likelyVerifiedBranchSchema,
  ambiguousBranchSchema,
  notFoundBranchSchema,
  suspiciousBranchSchema,
  processingErrorBranchSchema,
]);

// ---------------------------------------------------------------------------
// Warning schema
// ---------------------------------------------------------------------------

const warningSchema = z.object({
  code: z.string(),
  message: z.string(),
  referenceId: z.string().nullable(),
  details: z.record(z.string(), z.unknown()).nullable(),
});

// ---------------------------------------------------------------------------
// Root schema
// ---------------------------------------------------------------------------

export const resultsV1Schema = z.object({
  schemaVersion: z.literal("1.0"),
  reportLanguage: z.literal("es"),
  pipeline: z.object({
    name: z.string(),
    version: z.string(),
  }),
  summary: z.object({
    totalReferencesDetected: z.number().int().nonnegative(),
    totalReferencesAnalyzed: z.number().int().nonnegative(),
    countsByClassification: z.object({
      verified: z.number().int().nonnegative(),
      likely_verified: z.number().int().nonnegative(),
      ambiguous: z.number().int().nonnegative(),
      not_found: z.number().int().nonnegative(),
      suspicious: z.number().int().nonnegative(),
      processing_error: z.number().int().nonnegative(),
    }),
  }),
  references: z.array(referenceResultSchema),
  warnings: z.array(warningSchema),
});

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

/** Fully validated, typed ResultsV1 object. Inferred from the Zod schema. */
export type ResultsV1 = z.infer<typeof resultsV1Schema>;

/**
 * Parses `data` against the ResultsV1 schema.
 * Returns the parsed object on success, or null if validation fails.
 * Validation failures are logged to the console for observability.
 */
export function parseResultsV1(data: unknown): ResultsV1 | null {
  const parsed = resultsV1Schema.safeParse(data);
  if (!parsed.success) {
    console.error("[resultsV1] Validation failed:", parsed.error.issues);
    return null;
  }
  return parsed.data;
}
