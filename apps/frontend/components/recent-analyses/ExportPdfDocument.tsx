/**
 * ExportPdfDocument — @react-pdf/renderer PDF layout component.
 *
 * This file is NOT a client component (no "use client" directive). It is loaded
 * exclusively via dynamic import inside ExportButtons.tsx and rendered by the
 * @react-pdf/renderer `pdf()` function — never by the DOM renderer.
 *
 * Security notes:
 * - All user-controlled strings (rawText, decisionReason, matchedRecord fields)
 *   are rendered as <Text> nodes, never via HTML interpretation.
 * - URLs are rendered as clickable links ONLY when they begin with https:// or
 *   http://. Any other scheme is rendered as plain text.
 */

import {
  Document,
  Page,
  View,
  Text,
  StyleSheet,
  Link,
} from "@react-pdf/renderer";
import type { ResultsV1 } from "@/lib/schemas/resultsV1";
import type { ScoreResult } from "@/lib/computeScore";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExportPdfDocumentProps {
  result: ResultsV1;
  fileName: string;
  score: ScoreResult;
  /** Pre-resolved i18n strings keyed by i18n path. */
  translations: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Color constants (spec: step 07, section 3)
// ---------------------------------------------------------------------------

const COLORS = {
  brand: "#00d9ff",
  scoreHigh: "#22c55e",
  scoreMedium: "#f59e0b",
  scoreLow: "#ef4444",
  classificationVerified: "#22c55e",
  classificationLikelyVerified: "#3b82f6",
  classificationAmbiguous: "#f59e0b",
  classificationNotFound: "#ef4444",
  classificationSuspicious: "#dc2626",
  classificationProcessingError: "#6b7280",
  textPrimary: "#111827",
  textMuted: "#6b7280",
  border: "#e5e7eb",
  surface: "#f9fafb",
  white: "#ffffff",
} as const;

function classificationColor(classification: string): string {
  switch (classification) {
    case "verified":
      return COLORS.classificationVerified;
    case "likely_verified":
      return COLORS.classificationLikelyVerified;
    case "ambiguous":
      return COLORS.classificationAmbiguous;
    case "not_found":
      return COLORS.classificationNotFound;
    case "suspicious":
      return COLORS.classificationSuspicious;
    case "processing_error":
      return COLORS.classificationProcessingError;
    default:
      return COLORS.textMuted;
  }
}

function scoreColor(band: ScoreResult["band"]): string {
  switch (band) {
    case "high":
      return COLORS.scoreHigh;
    case "medium":
      return COLORS.scoreMedium;
    case "low":
      return COLORS.scoreLow;
  }
}

/**
 * Returns true if the URL is safe to render as a hyperlink.
 * Only https:// and http:// schemes are allowed (spec: step 07, section 9).
 */
function isSafeUrl(url: string): boolean {
  return url.startsWith("https://") || url.startsWith("http://");
}

// ---------------------------------------------------------------------------
// StyleSheet
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  page: {
    fontFamily: "Helvetica",
    fontSize: 10,
    color: COLORS.textPrimary,
    paddingTop: 44,
    paddingBottom: 60,
    paddingHorizontal: 44,
  },
  // ---- Header ----
  headerSection: {
    marginBottom: 20,
    borderBottom: `2 solid ${COLORS.brand}`,
    paddingBottom: 12,
  },
  headerTitle: {
    fontSize: 22,
    fontFamily: "Helvetica-Bold",
    color: COLORS.brand,
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 12,
    fontFamily: "Helvetica-Bold",
    color: COLORS.textPrimary,
    marginBottom: 6,
  },
  headerMeta: {
    fontSize: 9,
    color: COLORS.textMuted,
  },
  // ---- Section headings ----
  sectionHeading: {
    fontSize: 11,
    fontFamily: "Helvetica-Bold",
    marginBottom: 8,
    marginTop: 16,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    color: COLORS.textPrimary,
  },
  // ---- Score section ----
  scoreContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: COLORS.surface,
    borderRadius: 6,
    padding: 12,
    marginBottom: 4,
  },
  scoreNumber: {
    fontSize: 36,
    fontFamily: "Helvetica-Bold",
  },
  scoreBand: {
    fontSize: 12,
    fontFamily: "Helvetica-Bold",
  },
  // ---- Summary ----
  summaryRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 8,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: COLORS.surface,
    borderRadius: 4,
    padding: 8,
  },
  summaryLabel: {
    fontSize: 9,
    color: COLORS.textMuted,
    marginBottom: 2,
  },
  summaryValue: {
    fontSize: 14,
    fontFamily: "Helvetica-Bold",
    color: COLORS.textPrimary,
  },
  classBreakdownRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 3,
    borderBottom: `1 solid ${COLORS.border}`,
  },
  classLabel: {
    fontSize: 9,
    color: COLORS.textMuted,
  },
  classCount: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: COLORS.textPrimary,
  },
  // ---- Reference entry ----
  referenceEntry: {
    marginBottom: 12,
    borderRadius: 4,
    border: `1 solid ${COLORS.border}`,
    padding: 10,
  },
  referenceHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
  referenceId: {
    fontSize: 9,
    color: COLORS.textMuted,
  },
  classificationBadge: {
    fontSize: 8,
    fontFamily: "Helvetica-Bold",
    textTransform: "uppercase",
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 3,
    backgroundColor: COLORS.surface,
  },
  fieldLabel: {
    fontSize: 8,
    fontFamily: "Helvetica-Bold",
    color: COLORS.textMuted,
    marginBottom: 2,
    marginTop: 5,
  },
  fieldValue: {
    fontSize: 9,
    color: COLORS.textPrimary,
    lineHeight: 1.5,
  },
  evidenceBox: {
    backgroundColor: COLORS.surface,
    borderRadius: 3,
    padding: 6,
    marginBottom: 4,
  },
  evidenceSource: {
    fontSize: 8,
    fontFamily: "Helvetica-Bold",
    color: COLORS.brand,
    textTransform: "uppercase",
    marginBottom: 3,
  },
  evidenceMeta: {
    fontSize: 8,
    color: COLORS.textMuted,
  },
  safeLink: {
    fontSize: 8,
    color: COLORS.classificationLikelyVerified,
    textDecoration: "underline",
  },
  noEvidence: {
    fontSize: 9,
    color: COLORS.textMuted,
    fontStyle: "italic",
  },
  // ---- Footer ----
  footer: {
    position: "absolute",
    bottom: 30,
    left: 40,
    right: 40,
    borderTop: `1 solid ${COLORS.border}`,
    paddingTop: 8,
  },
  footerPipeline: {
    fontSize: 8,
    color: COLORS.textMuted,
    marginBottom: 3,
  },
  footerDisclaimer: {
    fontSize: 8,
    color: COLORS.textMuted,
    fontStyle: "italic",
    marginBottom: 3,
  },
  footerPageNumber: {
    fontSize: 8,
    color: COLORS.textMuted,
    textAlign: "right",
  },
  // ---- Page header (repeated on each page) ----
  pageHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 12,
    paddingBottom: 6,
    borderBottom: `1 solid ${COLORS.border}`,
  },
  pageHeaderBrand: {
    fontSize: 9,
    fontFamily: "Helvetica-Bold",
    color: COLORS.brand,
  },
  pageHeaderFile: {
    fontSize: 9,
    color: COLORS.textMuted,
  },
});

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RepeatingPageHeader({ fileName }: { fileName: string }) {
  return (
    <View fixed style={styles.pageHeader}>
      <Text style={styles.pageHeaderBrand}>Biblio Checker</Text>
      <Text style={styles.pageHeaderFile}>{fileName}</Text>
    </View>
  );
}

function SectionHeading({ children }: { children: string }) {
  return <Text style={styles.sectionHeading}>{children}</Text>;
}

function ReferenceEntry({
  reference,
  translations,
}: {
  reference: ResultsV1["references"][number];
  translations: Record<string, string>;
}) {
  const color = classificationColor(reference.classification);
  const classLabel =
    translations[`results.classification.${reference.classification}`] ??
    reference.classification;
  const naText = translations["results.pdf.notAvailable"] ?? "N/A";
  const confidenceScore =
    reference.confidenceScore !== null
      ? reference.confidenceScore.toFixed(2)
      : naText;
  const confidenceBand = reference.confidenceBand ?? naText;

  return (
    <View style={styles.referenceEntry} wrap={false}>
      {/* Header row: ID + classification badge */}
      <View style={styles.referenceHeader}>
        <Text style={styles.referenceId}>{reference.referenceId}</Text>
        <Text style={[styles.classificationBadge, { color }]}>{classLabel}</Text>
        <Text style={styles.referenceId}>
          {translations["results.fields.confidence"] ?? "Confidence"}:{" "}
          {confidenceScore} ({confidenceBand})
        </Text>
      </View>

      {/* Raw text */}
      <Text style={styles.fieldLabel}>
        {translations["results.section.raw_text"] ?? "Raw Text"}
      </Text>
      <Text style={styles.fieldValue}>{reference.rawText}</Text>

      {/* Decision reason */}
      <Text style={styles.fieldLabel}>
        {translations["results.section.decision_reason"] ?? "Decision Reason"}
      </Text>
      <Text style={styles.fieldValue}>{reference.decisionReason}</Text>

      {/* Evidence */}
      <Text style={styles.fieldLabel}>
        {translations["results.pdf.evidence"] ?? "Evidence"}
      </Text>
      {reference.evidence.length === 0 ? (
        <Text style={styles.noEvidence}>
          {translations["results.pdf.noEvidence"] ?? "No evidence found"}
        </Text>
      ) : (
        reference.evidence.map((ev, i) => (
          <View key={i} style={styles.evidenceBox}>
            <Text style={styles.evidenceSource}>{ev.source}</Text>
            {ev.matchedRecord.doi && (
              <Text style={styles.evidenceMeta}>DOI: {ev.matchedRecord.doi}</Text>
            )}
            {ev.matchedRecord.url && isSafeUrl(ev.matchedRecord.url) ? (
              <Link src={ev.matchedRecord.url} style={styles.safeLink}>
                {ev.matchedRecord.url}
              </Link>
            ) : ev.matchedRecord.url ? (
              <Text style={styles.evidenceMeta}>{ev.matchedRecord.url}</Text>
            ) : null}
          </View>
        ))
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main document component
// ---------------------------------------------------------------------------

export function ExportPdfDocument({
  result,
  fileName,
  score,
  translations,
}: ExportPdfDocumentProps) {
  const generationDate = new Date().toLocaleDateString(
    result.reportLanguage === "en"
      ? "en-US"
      : result.reportLanguage === "es"
        ? "es-ES"
        : "pt-BR",
    { year: "numeric", month: "long", day: "numeric" }
  );

  const bandLabel =
    score.band === "high"
      ? (translations["results.score.high"] ?? "High authenticity")
      : score.band === "medium"
        ? (translations["results.score.medium"] ?? "Needs review")
        : (translations["results.score.low"] ?? "Low authenticity");

  const scoreHex = scoreColor(score.band);

  const classificationOrder: Array<keyof typeof result.summary.countsByClassification> = [
    "verified",
    "likely_verified",
    "ambiguous",
    "not_found",
    "suspicious",
    "processing_error",
  ];

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Repeating page header (fixed — shows on every page) */}
        <RepeatingPageHeader fileName={fileName} />

        {/* ---- Section 1: Header (first page only) ---- */}
        <View style={styles.headerSection}>
          <Text style={styles.headerTitle}>Biblio Checker</Text>
          <Text style={styles.headerSubtitle}>
            {translations["results.pdf.title"] ??
              "Bibliographic Reference Analysis Report"}
          </Text>
          <Text style={styles.headerMeta}>
            {generationDate} · {fileName}
          </Text>
        </View>

        {/* ---- Section 2: Authenticity Score ---- */}
        <SectionHeading>
          {translations["results.score.title"] ??
            "Authenticity Score"}
        </SectionHeading>
        <View style={styles.scoreContainer}>
          <Text style={[styles.scoreNumber, { color: scoreHex }]}>
            {score.score}
          </Text>
          <View>
            <Text style={[styles.scoreBand, { color: scoreHex }]}>
              {bandLabel}
            </Text>
          </View>
        </View>

        {/* ---- Section 3: Summary ---- */}
        <SectionHeading>
          {translations["results.pdf.summary"] ?? "Summary"}
        </SectionHeading>
        <View style={styles.summaryRow}>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>
              {translations["results.summary.detected"] ?? "References Detected"}
            </Text>
            <Text style={styles.summaryValue}>
              {result.summary.totalReferencesDetected}
            </Text>
          </View>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>
              {translations["results.summary.analyzed"] ?? "References Analyzed"}
            </Text>
            <Text style={styles.summaryValue}>
              {result.summary.totalReferencesAnalyzed}
            </Text>
          </View>
        </View>

        {/* Classification breakdown */}
        {classificationOrder
          .filter((key) => result.summary.countsByClassification[key] > 0)
          .map((key) => (
            <View key={key} style={styles.classBreakdownRow}>
              <Text style={styles.classLabel}>
                {translations[`results.classification.${key}`] ?? key}
              </Text>
              <Text style={styles.classCount}>
                {result.summary.countsByClassification[key]}
              </Text>
            </View>
          ))}

        {/* ---- Section 4: Reference Details ---- */}
        {result.references.length > 0 && (
          <>
            <SectionHeading>
              {translations["results.pdf.references"] ??
                "Reference Details"}
            </SectionHeading>
            {result.references.map((reference) => (
              <ReferenceEntry
                key={reference.referenceId}
                reference={reference}
                translations={translations}
              />
            ))}
          </>
        )}

        {result.references.length === 0 && (
          <>
            <SectionHeading>
              {translations["results.pdf.references"] ??
                "Reference Details"}
            </SectionHeading>
            <Text style={styles.noEvidence}>
              {translations["results.no_references"] ?? "No references found"}
            </Text>
          </>
        )}

        {/* ---- Section 5: Footer (fixed — shows on every page) ---- */}
        <View style={styles.footer} fixed>
          <Text style={styles.footerPipeline}>
            {result.pipeline.name} v{result.pipeline.version} · Schema{" "}
            {result.schemaVersion}
          </Text>
          <Text style={styles.footerDisclaimer}>
            {translations["results.pdf.disclaimer"] ??
              "This report was generated automatically. Results should be verified manually for critical decisions."}
          </Text>
          <Text
            style={styles.footerPageNumber}
            render={({ pageNumber, totalPages }) => {
              const template = translations["results.pdf.page"] ?? "Page {current} of {total}";
              return template.replace("{current}", String(pageNumber)).replace("{total}", String(totalPages));
            }}
          />
        </View>
      </Page>
    </Document>
  );
}
