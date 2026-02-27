export type Classification =
  | "verified"
  | "likely_verified"
  | "ambiguous"
  | "not_found"
  | "suspicious"
  | "processing_error";

export type ConfidenceBand = "very_high" | "high" | "medium" | "low" | "very_low";

export type ReasonCode =
  | "exact_doi_match"
  | "exact_identifier_match"
  | "strong_metadata_match"
  | "multiple_plausible_candidates"
  | "insufficient_metadata"
  | "no_match_any_source"
  | "strong_doi_conflict"
  | "cross_source_metadata_conflict"
  | "source_timeout_partial"
  | "reference_processing_failure";

// ---------------------------------------------------------------------------
// Nested object types
// ---------------------------------------------------------------------------

export interface NormalizedReference {
  title: string | null;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  arxivId: string | null;
}

export interface MatchedRecord {
  externalId: string;
  title: string | null;
  year: number | null;
  doi: string | null;
  url: string | null;
}

export interface EvidenceItem {
  source: string;
  matchType: string;
  /** Normalised score in the range [0.0, 1.0]. */
  score: number;
  matchedRecord: MatchedRecord;
}

export interface Warning {
  code: string;
  message: string;
  referenceId: string | null;
  details: Record<string, unknown> | null;
}

export interface CountsByClassification {
  verified: number;
  likely_verified: number;
  ambiguous: number;
  not_found: number;
  suspicious: number;
  processing_error: number;
}

export interface Summary {
  totalReferencesDetected: number;
  totalReferencesAnalyzed: number;
  countsByClassification: CountsByClassification;
}

export interface Pipeline {
  name: string;
  version: string;
}

export interface ReferenceResult {
  referenceId: string;
  rawText: string;
  normalized: NormalizedReference;
  classification: Classification;
  /** Normalised score in the range [0.0, 1.0], or null for processing_error. */
  confidenceScore: number | null;
  confidenceBand: ConfidenceBand | null;
  manualReviewRequired: boolean;
  reasonCode: ReasonCode;
  decisionReason: string;
  evidence: EvidenceItem[];
}

// ---------------------------------------------------------------------------
// Root result type
// ---------------------------------------------------------------------------

export interface ResultsV1 {
  schemaVersion: "1.0";
  reportLanguage: "es";
  pipeline: Pipeline;
  summary: Summary;
  references: ReferenceResult[];
  warnings: Warning[];
}
