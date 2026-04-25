/**
 * Unit tests for the exportCsv utility.
 *
 * Tests cover buildCsvString only (pure function).
 * exportCsv() requires a DOM and is not tested here.
 */

import { describe, it, expect } from "vitest";
import { buildCsvString } from "@/lib/exportCsv";
import type { ResultsV1 } from "@/lib/schemas/resultsV1";

// ---------------------------------------------------------------------------
// Minimal fixture helpers
// ---------------------------------------------------------------------------

/**
 * Parses a single CSV data row (post-BOM, post-header) into an array of
 * field values, correctly handling RFC 4180 quoted fields.
 * This is intentionally simple: handles the cases produced by buildCsvString.
 */
function parseCsvRow(row: string): string[] {
  const fields: string[] = [];
  let i = 0;
  while (i < row.length) {
    if (row[i] === '"') {
      // Quoted field
      i++; // skip opening quote
      let field = "";
      while (i < row.length) {
        if (row[i] === '"' && row[i + 1] === '"') {
          field += '"';
          i += 2;
        } else if (row[i] === '"') {
          i++; // skip closing quote
          break;
        } else {
          field += row[i++];
        }
      }
      fields.push(field);
      if (row[i] === ",") i++; // skip comma separator
      else break; // end of row
    } else {
      // Unquoted field
      const end = row.indexOf(",", i);
      if (end === -1) {
        fields.push(row.slice(i));
        break;
      } else {
        fields.push(row.slice(i, end));
        i = end + 1;
        // If we just consumed the last comma and nothing follows, push empty field
        if (i === row.length) {
          fields.push("");
          break;
        }
      }
    }
  }
  return fields;
}

function makeResult(overrides: Partial<ResultsV1["references"][number]>[] = []): ResultsV1 {
  const baseRef: ResultsV1["references"][number] = {
    referenceId: "ref-1",
    rawText: "Smith J 2020 A study Journal of Science",
    normalized: {
      title: "A study",
      authors: ["Smith J"],
      year: 2020,
      venue: "Journal of Science",
      doi: "10.1234/js.2020",
      arxivId: null,
    },
    classification: "verified",
    confidenceScore: 0.95,
    confidenceBand: "very_high",
    manualReviewRequired: false,
    reasonCode: "exact_doi_match",
    decisionReason: "DOI matched exactly in OpenAlex.",
    evidence: [
      {
        source: "OpenAlex",
        matchType: "doi_exact",
        score: 0.95,
        matchedRecord: {
          externalId: "W123",
          title: "A study",
          year: 2020,
          doi: "10.1234/js.2020",
          url: "https://openalex.org/W123",
        },
      },
    ],
  };

  const references = overrides.map(
    (o) => ({ ...baseRef, ...o } as ResultsV1["references"][number])
  );
  return {
    schemaVersion: "1.0",
    reportLanguage: "en",
    pipeline: { name: "biblio-checker", version: "1.0" },
    summary: {
      totalReferencesDetected: references.length,
      totalReferencesAnalyzed: references.length,
      countsByClassification: {
        verified: references.filter((r) => r.classification === "verified").length,
        likely_verified: 0,
        ambiguous: 0,
        not_found: 0,
        suspicious: 0,
        processing_error: 0,
      },
    },
    references,
    warnings: [],
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

const EXPECTED_HEADERS =
  "referenceId,rawText,title,authors,year,classification,confidenceScore,confidenceBand,reasonCode,decisionReason,evidenceSources,bestMatchDoi,bestMatchUrl";

describe("buildCsvString", () => {
  it("produces a UTF-8 BOM as the first character", () => {
    const csv = buildCsvString(makeResult([{}]));
    expect(csv.charCodeAt(0)).toBe(0xfeff);
  });

  it("includes the correct 13-column header row", () => {
    const csv = buildCsvString(makeResult([{}]));
    // Strip BOM, grab first line
    const firstLine = csv.slice(1).split("\r\n")[0];
    expect(firstLine).toBe(EXPECTED_HEADERS);
  });

  it("uses CRLF line endings", () => {
    const csv = buildCsvString(makeResult([{}]));
    // Every line break must be CRLF
    expect(csv).toContain("\r\n");
    // No bare LF without a preceding CR
    const withoutCRLF = csv.replace(/\r\n/g, "");
    expect(withoutCRLF).not.toContain("\n");
  });

  it("produces only a header row (plus trailing CRLF) when references is empty", () => {
    const result = makeResult();
    const csv = buildCsvString(result);
    // BOM + header + CRLF
    const withoutBOM = csv.slice(1);
    expect(withoutBOM).toBe(EXPECTED_HEADERS + "\r\n");
  });

  it("escapes a field containing a comma by wrapping in double quotes", () => {
    const csv = buildCsvString(
      makeResult([{ normalized: { title: "Title, with comma", authors: [], year: null, venue: null, doi: null, arxivId: null } }])
    );
    expect(csv).toContain('"Title, with comma"');
  });

  it("escapes inner double quotes by doubling them (RFC 4180)", () => {
    const csv = buildCsvString(
      makeResult([{ normalized: { title: 'He said "hello"', authors: [], year: null, venue: null, doi: null, arxivId: null } }])
    );
    expect(csv).toContain('"He said ""hello"""');
  });

  it("escapes a field containing a newline by wrapping in double quotes", () => {
    const csv = buildCsvString(
      makeResult([{ rawText: "Line one\nLine two" }])
    );
    expect(csv).toContain('"Line one\nLine two"');
  });

  it("prefixes fields starting with '=' with a tab (formula injection defense)", () => {
    const csv = buildCsvString(
      makeResult([{ rawText: "=CMD(danger)" }])
    );
    expect(csv).toContain("\t=CMD(danger)");
  });

  it("prefixes fields starting with '+' with a tab", () => {
    const csv = buildCsvString(
      makeResult([{ rawText: "+1234" }])
    );
    expect(csv).toContain("\t+1234");
  });

  it("prefixes fields starting with '-' with a tab", () => {
    const csv = buildCsvString(
      makeResult([{ rawText: "-DROP TABLE" }])
    );
    expect(csv).toContain("\t-DROP TABLE");
  });

  it("prefixes fields starting with '@' with a tab", () => {
    const csv = buildCsvString(
      makeResult([{ rawText: "@SUM(A1:A10)" }])
    );
    expect(csv).toContain("\t@SUM(A1:A10)");
  });

  it("outputs empty string for null year", () => {
    const csv = buildCsvString(
      makeResult([{ normalized: { title: "T", authors: [], year: null, venue: null, doi: null, arxivId: null } }])
    );
    // year column is index 4 — use proper CSV parser to handle quoted fields
    const dataRow = csv.slice(1).split("\r\n")[1]!;
    const cols = parseCsvRow(dataRow);
    expect(cols[4]).toBe("");
  });

  it("outputs empty string for null confidenceScore (processing_error branch)", () => {
    const processingErrorRef: ResultsV1["references"][number] = {
      referenceId: "ref-err",
      rawText: "Malformed reference.",
      normalized: {
        title: null,
        authors: [],
        year: null,
        venue: null,
        doi: null,
        arxivId: null,
      },
      classification: "processing_error",
      confidenceScore: null,
      confidenceBand: null,
      manualReviewRequired: true,
      reasonCode: "reference_processing_failure",
      decisionReason: "Could not process.",
      evidence: [],
    };
    const result = makeResult();
    result.references = [processingErrorRef];
    const csv = buildCsvString(result);
    const dataRow = csv.slice(1).split("\r\n")[1]!;
    const cols = parseCsvRow(dataRow);
    // confidenceScore is index 6, confidenceBand is index 7
    expect(cols[6]).toBe("");
    expect(cols[7]).toBe("");
  });

  it("joins multiple authors with '; '", () => {
    const csv = buildCsvString(
      makeResult([{ normalized: { title: "T", authors: ["Smith, J.", "Doe, A."], year: 2020, venue: null, doi: null, arxivId: null } }])
    );
    expect(csv).toContain("Smith, J.; Doe, A.");
  });

  it("joins multiple evidence sources with '; '", () => {
    const ref: Partial<ResultsV1["references"][number]> = {
      evidence: [
        { source: "OpenAlex", matchType: "doi_exact", score: 0.9, matchedRecord: { externalId: "W1", title: null, year: null, doi: "10.1/a", url: null } },
        { source: "arXiv", matchType: "title_fuzzy", score: 0.7, matchedRecord: { externalId: "arxiv:1", title: null, year: null, doi: null, url: "https://arxiv.org/1" } },
      ],
    };
    const csv = buildCsvString(makeResult([ref]));
    expect(csv).toContain("OpenAlex; arXiv");
  });

  it("takes bestMatchDoi and bestMatchUrl from first evidence item", () => {
    const ref: Partial<ResultsV1["references"][number]> = {
      evidence: [
        { source: "OpenAlex", matchType: "doi_exact", score: 0.9, matchedRecord: { externalId: "W1", title: null, year: null, doi: "10.1/first", url: "https://first.example" } },
        { source: "arXiv", matchType: "title_fuzzy", score: 0.7, matchedRecord: { externalId: "arxiv:2", title: null, year: null, doi: "10.1/second", url: "https://second.example" } },
      ],
    };
    const csv = buildCsvString(makeResult([ref]));
    expect(csv).toContain("10.1/first");
    expect(csv).toContain("https://first.example");
    // Second evidence DOI/URL should NOT appear in bestMatch columns
    const dataRow = csv.slice(1).split("\r\n")[1]!;
    const cols = parseCsvRow(dataRow);
    expect(cols[11]).toBe("10.1/first");
    expect(cols[12]).toBe("https://first.example");
  });

  it("outputs empty strings for bestMatchDoi and bestMatchUrl when evidence is empty", () => {
    const ref: Partial<ResultsV1["references"][number]> = {
      evidence: [],
    };
    const csv = buildCsvString(makeResult([ref]));
    const dataRow = csv.slice(1).split("\r\n")[1]!;
    const cols = parseCsvRow(dataRow);
    expect(cols[11]).toBe("");
    expect(cols[12]).toBe("");
  });
});
