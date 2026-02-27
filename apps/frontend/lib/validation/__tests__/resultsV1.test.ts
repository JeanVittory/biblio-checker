/**
 * Tests for parseResultsV1() and resultsV1Schema.
 *
 * Test framework: Vitest
 *
 * Note: the repo does not currently expose a `frontend` test script.
 * Run directly via `pnpm --filter frontend vitest run`.
 *
 * Coverage:
 *   - 6 valid canonical fixtures (one per classification) → parseResultsV1 !== null
 *   - 3 invalid canonical fixtures from spec → parseResultsV1 === null
 *       * verified + very_low (incompatible band)
 *       * not_found + very_high (incompatible band)
 *       * processing_error + non-null confidenceBand
 *   - null input            → null
 *   - string input          → null
 *   - schemaVersion="2.0"   → null
 *   - empty object          → null
 */

import { describe, it, expect } from "vitest";
import { parseResultsV1, resultsV1Schema } from "../resultsV1";

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/** Minimal normalized reference with all nullable fields set to null. */
const NORMALIZED_NULL = {
  title: null,
  authors: [] as string[],
  year: null,
  venue: null,
  doi: null,
  arxivId: null,
};

/** A valid EvidenceItem used in non-processing_error references. */
const EVIDENCE_ITEM = {
  source: "openalex",
  matchType: "exact_doi_match",
  score: 0.95,
  matchedRecord: {
    externalId: "W1234567890",
    title: "Título real",
    year: 2021,
    doi: "10.1234/abcd.2021.001",
    url: "https://openalex.org/W1234567890",
  },
};

/** Shared pipeline object used in all fixtures. */
const PIPELINE = { name: "reference_verification_pipeline", version: "v1" };

/** Build a minimal ResultsV1-shaped object for a single reference. */
function makeSingleRefPayload(ref: object, classification: string) {
  const counts = {
    verified: 0,
    likely_verified: 0,
    ambiguous: 0,
    not_found: 0,
    suspicious: 0,
    processing_error: 0,
    [classification]: 1,
  };
  return {
    schemaVersion: "1.0" as const,
    reportLanguage: "es" as const,
    pipeline: PIPELINE,
    summary: {
      totalReferencesDetected: 1,
      totalReferencesAnalyzed: 1,
      countsByClassification: counts,
    },
    references: [ref],
    warnings: [],
  };
}

// ---------------------------------------------------------------------------
// Canonical valid fixtures (one per classification)
// ---------------------------------------------------------------------------

const VALID_VERIFIED = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Ejemplo con DOI exacto",
    normalized: {
      title: "Título real",
      authors: ["Autor A"],
      year: 2021,
      venue: "Revista X",
      doi: "10.1234/abcd.2021.001",
      arxivId: null,
    },
    classification: "verified" as const,
    confidenceScore: 0.91,
    confidenceBand: "very_high" as const,
    manualReviewRequired: false,
    reasonCode: "exact_doi_match" as const,
    decisionReason: "El DOI coincide exactamente con un registro canónico.",
    evidence: [EVIDENCE_ITEM],
  },
  "verified"
);

const VALID_LIKELY_VERIFIED = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia con metadatos sólidos",
    normalized: {
      title: "Otro título",
      authors: ["Autor B"],
      year: 2019,
      venue: "Congreso Y",
      doi: null,
      arxivId: null,
    },
    classification: "likely_verified" as const,
    confidenceScore: 0.72,
    confidenceBand: "medium" as const,
    manualReviewRequired: false,
    reasonCode: "strong_metadata_match" as const,
    decisionReason: "Metadatos coinciden con alta probabilidad.",
    evidence: [],
  },
  "likely_verified"
);

const VALID_AMBIGUOUS = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia ambigua",
    normalized: NORMALIZED_NULL,
    classification: "ambiguous" as const,
    confidenceScore: 0.45,
    confidenceBand: "low" as const,
    manualReviewRequired: true,
    reasonCode: "multiple_plausible_candidates" as const,
    decisionReason: "Se encontraron múltiples candidatos plausibles.",
    evidence: [],
  },
  "ambiguous"
);

const VALID_NOT_FOUND = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia no encontrada",
    normalized: NORMALIZED_NULL,
    classification: "not_found" as const,
    confidenceScore: 0.05,
    confidenceBand: "very_low" as const,
    manualReviewRequired: true,
    reasonCode: "no_match_any_source" as const,
    decisionReason: "No se encontró coincidencia en ninguna fuente.",
    evidence: [],
  },
  "not_found"
);

const VALID_SUSPICIOUS = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia sospechosa",
    normalized: {
      title: "Título con conflicto",
      authors: ["Autor C"],
      year: 2018,
      venue: null,
      doi: "10.9999/conflict.2018",
      arxivId: null,
    },
    classification: "suspicious" as const,
    confidenceScore: 0.78,
    confidenceBand: "high" as const,
    manualReviewRequired: true,
    reasonCode: "strong_doi_conflict" as const,
    decisionReason: "El DOI apunta a un trabajo diferente.",
    evidence: [],
  },
  "suspicious"
);

const VALID_PROCESSING_ERROR = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia que falló al procesarse",
    normalized: NORMALIZED_NULL,
    classification: "processing_error" as const,
    confidenceScore: null,
    confidenceBand: null,
    manualReviewRequired: true,
    reasonCode: "reference_processing_failure" as const,
    decisionReason: "Ocurrió un error interno al procesar esta referencia.",
    evidence: [],
  },
  "processing_error"
);

// ---------------------------------------------------------------------------
// Invalid fixtures from spec
// ---------------------------------------------------------------------------

/** verified classification paired with very_low band — incompatible. */
const INVALID_VERIFIED_VERY_LOW = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia verificada con banda incorrecta",
    normalized: {
      title: "Título real",
      authors: ["Autor A"],
      year: 2021,
      venue: "Revista X",
      doi: "10.1234/abcd.2021.001",
      arxivId: null,
    },
    classification: "verified" as const,
    confidenceScore: 0.91,
    confidenceBand: "very_low", // incompatible with verified
    manualReviewRequired: false,
    reasonCode: "exact_doi_match" as const,
    decisionReason: "El DOI coincide exactamente con un registro canónico.",
    evidence: [EVIDENCE_ITEM],
  },
  "verified"
);

/** not_found classification paired with very_high band — incompatible. */
const INVALID_NOT_FOUND_VERY_HIGH = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Referencia no encontrada con banda incorrecta",
    normalized: NORMALIZED_NULL,
    classification: "not_found" as const,
    confidenceScore: 0.9,
    confidenceBand: "very_high", // incompatible with not_found
    manualReviewRequired: true,
    reasonCode: "no_match_any_source" as const,
    decisionReason: "No se encontró coincidencia.",
    evidence: [],
  },
  "not_found"
);

/** processing_error with a non-null confidenceBand — must be null. */
const INVALID_PROCESSING_ERROR_WITH_BAND = makeSingleRefPayload(
  {
    referenceId: "ref-001",
    rawText: "Error de procesamiento con banda",
    normalized: NORMALIZED_NULL,
    classification: "processing_error" as const,
    confidenceScore: null,
    confidenceBand: "low", // must be null for processing_error
    manualReviewRequired: true,
    reasonCode: "reference_processing_failure" as const,
    decisionReason: "Error interno.",
    evidence: [],
  },
  "processing_error"
);

// ---------------------------------------------------------------------------
// Test suites
// ---------------------------------------------------------------------------

describe("parseResultsV1 — valid fixtures", () => {
  it("returns a non-null object for verified + very_high", () => {
    const result = parseResultsV1(VALID_VERIFIED);
    expect(result).not.toBeNull();
    expect(result!.references[0].classification).toBe("verified");
  });

  it("returns a non-null object for likely_verified + medium", () => {
    const result = parseResultsV1(VALID_LIKELY_VERIFIED);
    expect(result).not.toBeNull();
    expect(result!.references[0].classification).toBe("likely_verified");
  });

  it("returns a non-null object for ambiguous + low + manualReviewRequired=true", () => {
    const result = parseResultsV1(VALID_AMBIGUOUS);
    expect(result).not.toBeNull();
    expect(result!.references[0].classification).toBe("ambiguous");
    expect(result!.references[0].manualReviewRequired).toBe(true);
  });

  it("returns a non-null object for not_found + very_low + manualReviewRequired=true", () => {
    const result = parseResultsV1(VALID_NOT_FOUND);
    expect(result).not.toBeNull();
    expect(result!.references[0].classification).toBe("not_found");
  });

  it("returns a non-null object for suspicious + high + manualReviewRequired=true", () => {
    const result = parseResultsV1(VALID_SUSPICIOUS);
    expect(result).not.toBeNull();
    expect(result!.references[0].classification).toBe("suspicious");
  });

  it("returns a non-null object for processing_error + null band + null score", () => {
    const result = parseResultsV1(VALID_PROCESSING_ERROR);
    expect(result).not.toBeNull();
    expect(result!.references[0].classification).toBe("processing_error");
    expect(result!.references[0].confidenceBand).toBeNull();
    expect(result!.references[0].confidenceScore).toBeNull();
  });
});

describe("parseResultsV1 — invalid fixtures (spec canonical invalids)", () => {
  it("returns null for verified + very_low (incompatible band)", () => {
    expect(parseResultsV1(INVALID_VERIFIED_VERY_LOW)).toBeNull();
  });

  it("returns null for not_found + very_high (incompatible band)", () => {
    expect(parseResultsV1(INVALID_NOT_FOUND_VERY_HIGH)).toBeNull();
  });

  it("returns null for processing_error + non-null confidenceBand", () => {
    expect(parseResultsV1(INVALID_PROCESSING_ERROR_WITH_BAND)).toBeNull();
  });
});

describe("parseResultsV1 — degenerate inputs", () => {
  it("returns null for null input", () => {
    expect(parseResultsV1(null)).toBeNull();
  });

  it("returns null for string input", () => {
    expect(parseResultsV1("foo")).toBeNull();
  });

  it("returns null when schemaVersion is '2.0'", () => {
    const data = { ...VALID_VERIFIED, schemaVersion: "2.0" };
    expect(parseResultsV1(data)).toBeNull();
  });

  it("returns null for an empty object", () => {
    expect(parseResultsV1({})).toBeNull();
  });
});

describe("resultsV1Schema — direct schema access", () => {
  it("safeParse returns success=true for the canonical verified fixture", () => {
    const parsed = resultsV1Schema.safeParse(VALID_VERIFIED);
    expect(parsed.success).toBe(true);
  });

  it("safeParse returns success=false for an incompatible band", () => {
    const parsed = resultsV1Schema.safeParse(INVALID_VERIFIED_VERY_LOW);
    expect(parsed.success).toBe(false);
  });
});
