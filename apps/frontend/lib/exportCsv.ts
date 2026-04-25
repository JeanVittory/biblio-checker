/**
 * CSV export utility for ResultsV1 analysis reports.
 *
 * Spec: spec/momento-wow/06-export-csv/spec.md
 *
 * Column order (13 columns):
 *   referenceId, rawText, title, authors, year, classification,
 *   confidenceScore, confidenceBand, reasonCode, decisionReason,
 *   evidenceSources, bestMatchDoi, bestMatchUrl
 */

import type { ResultsV1 } from "@/lib/schemas/resultsV1";
import { sanitizeFileName } from "@/lib/file";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CSV_HEADERS = [
  "referenceId",
  "rawText",
  "title",
  "authors",
  "year",
  "classification",
  "confidenceScore",
  "confidenceBand",
  "reasonCode",
  "decisionReason",
  "evidenceSources",
  "bestMatchDoi",
  "bestMatchUrl",
] as const;

/** Characters that trigger formula injection in spreadsheet apps. */
const FORMULA_INJECTION_PREFIXES = ["=", "+", "-", "@"];

// ---------------------------------------------------------------------------
// RFC 4180 helpers
// ---------------------------------------------------------------------------

/**
 * Escapes a single CSV field value per RFC 4180:
 * - Wraps in double quotes if the value contains commas, double quotes, or newlines.
 * - Doubles any inner double-quote characters.
 * - Prefixes with a tab character if the value starts with a formula-injection char.
 */
function escapeCsvField(raw: string): string {
  // Formula injection defense — must run before quoting
  const defended =
    FORMULA_INJECTION_PREFIXES.some((prefix) => raw.startsWith(prefix))
      ? `\t${raw}`
      : raw;

  // RFC 4180: quote the field if it contains comma, double-quote, or newline
  if (
    defended.includes(",") ||
    defended.includes('"') ||
    defended.includes("\n") ||
    defended.includes("\r")
  ) {
    return `"${defended.replace(/"/g, '""')}"`;
  }

  return defended;
}

/** Converts a nullable value to an empty string. */
function toStr(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

// ---------------------------------------------------------------------------
// Core builder
// ---------------------------------------------------------------------------

/**
 * Builds the full CSV string for a ResultsV1 report.
 *
 * - UTF-8 BOM prefix for Excel compatibility.
 * - CRLF line endings per RFC 4180.
 * - Returns header-only row when references array is empty.
 *
 * Pure function — no side effects; safe to unit-test.
 */
export function buildCsvString(result: ResultsV1): string {
  const CRLF = "\r\n";
  const BOM = "\uFEFF";

  const headerRow = CSV_HEADERS.map(escapeCsvField).join(",");

  const dataRows = result.references.map((ref) => {
    const authorsJoined = ref.normalized.authors.join("; ");
    const evidenceSources = ref.evidence.map((e) => e.source).join("; ");
    const firstEvidence = ref.evidence[0] ?? null;
    const bestMatchDoi = firstEvidence?.matchedRecord.doi ?? null;
    const bestMatchUrl = firstEvidence?.matchedRecord.url ?? null;

    const fields: string[] = [
      toStr(ref.referenceId),
      toStr(ref.rawText),
      toStr(ref.normalized.title),
      authorsJoined,
      toStr(ref.normalized.year),
      toStr(ref.classification),
      toStr(ref.confidenceScore),
      toStr(ref.confidenceBand),
      toStr(ref.reasonCode),
      toStr(ref.decisionReason),
      evidenceSources,
      toStr(bestMatchDoi),
      toStr(bestMatchUrl),
    ];

    return fields.map(escapeCsvField).join(",");
  });

  const rows = [headerRow, ...dataRows];
  return BOM + rows.join(CRLF) + CRLF;
}

// ---------------------------------------------------------------------------
// Browser download trigger
// ---------------------------------------------------------------------------

/**
 * Triggers a browser download of the CSV report.
 *
 * @param result   - Validated ResultsV1 payload to export.
 * @param fileName - Original file name (e.g. "thesis.pdf"). The extension is
 *                   stripped and "-report.csv" is appended.
 */
export function exportCsv(result: ResultsV1, fileName: string): void {
  // Derive output file name: strip extension, sanitize, append suffix
  const withoutExtension = fileName.replace(/\.[^/.]+$/, "");
  const sanitized = sanitizeFileName(withoutExtension);
  const outputName = `${sanitized}-report.csv`;

  const csvContent = buildCsvString(result);
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = outputName;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
