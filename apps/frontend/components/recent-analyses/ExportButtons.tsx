"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { sanitizeFileName } from "@/lib/file";
import { computeScore } from "@/lib/computeScore";
import { exportCsv } from "@/lib/exportCsv";
import type { ResultsV1 } from "@/lib/schemas/resultsV1";

export interface ExportButtonsProps {
  result: ResultsV1;
  fileName: string;
}

/**
 * Strips the file extension from a file name and sanitizes it for use as a
 * download attribute value. Path separators are removed by sanitizeFileName.
 */
function buildDownloadBaseName(fileName: string): string {
  const withoutExt = fileName.replace(/\.[^/.]+$/, "");
  return sanitizeFileName(withoutExt);
}

export function ExportButtons({ result, fileName }: ExportButtonsProps) {
  const t = useTranslations();
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState(false);

  const baseName = buildDownloadBaseName(fileName);

  function handleCsvClick() {
    exportCsv(result, fileName);
  }

  // ---- PDF handler ----
  async function handlePdfClick() {
    if (pdfLoading) return;

    setPdfLoading(true);
    setPdfError(false);

    try {
      // Resolve all i18n strings before entering the non-React renderer path.
      // Keys may not yet exist in the catalog (added by another agent); the
      // ExportPdfDocument component has fallback strings for all of them.
      const translationKeys = [
        "results.pdf.title",
        "results.pdf.disclaimer",
        "results.score.title",
        "results.score.high",
        "results.score.medium",
        "results.score.low",
        "results.pdf.summary",
        "results.pdf.references",
        "results.pdf.evidence",
        "results.pdf.noEvidence",
        "results.pdf.notAvailable",
        "results.section.raw_text",
        "results.section.decision_reason",
        "results.summary.detected",
        "results.summary.analyzed",
        "results.classification.verified",
        "results.classification.likely_verified",
        "results.classification.ambiguous",
        "results.classification.not_found",
        "results.classification.suspicious",
        "results.classification.processing_error",
      ] as const;

      const translations: Record<string, string> = {};
      for (const key of translationKeys) {
        try {
          translations[key] = t(key as Parameters<typeof t>[0]);
        } catch {
          // Key not yet in catalog — ExportPdfDocument fallback strings apply.
        }
      }

      // results.pdf.page has ICU placeholders — resolve with dummy values
      // then the PDF component does its own string replacement at render time.
      try {
        translations["results.pdf.page"] = t("results.pdf.page" as Parameters<typeof t>[0], { current: "{current}", total: "{total}" });
      } catch {
        // fallback handled in ExportPdfDocument
      }

      const score = computeScore(result.summary.countsByClassification);

      // Dynamic imports keep the PDF library out of the initial bundle.
      const [{ pdf }, { ExportPdfDocument }] = await Promise.all([
        import("@react-pdf/renderer"),
        import("./ExportPdfDocument"),
      ]);

      const blob = await pdf(
        <ExportPdfDocument
          result={result}
          fileName={fileName}
          score={score}
          translations={translations}
        />
      ).toBlob();

      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${baseName}-report.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("[ExportButtons] PDF generation failed:", err);
      setPdfError(true);
      // Clear error indicator after 4 seconds so the button recovers.
      setTimeout(() => setPdfError(false), 4000);
    } finally {
      setPdfLoading(false);
    }
  }

  const baseButtonClass =
    "inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";

  return (
    <div className="flex items-center gap-2">
      {/* CSV button */}
      <button
        type="button"
        onClick={handleCsvClick}
        aria-label={t("results.export.csv_aria" as Parameters<typeof t>[0])}
        className={cn(
          baseButtonClass,
          "text-muted hover:text-accent border border-border hover:border-accent/50"
        )}
      >
        <Download className="h-3 w-3" aria-hidden="true" />
        {t("results.export.csv" as Parameters<typeof t>[0])}
      </button>

      {/* PDF button */}
      <button
        type="button"
        onClick={handlePdfClick}
        disabled={pdfLoading}
        aria-label={t("results.export.pdf_aria" as Parameters<typeof t>[0])}
        aria-busy={pdfLoading}
        className={cn(
          baseButtonClass,
          "border",
          pdfError
            ? "text-red-400 border-red-400/50 hover:text-red-400"
            : pdfLoading
              ? "text-muted border-border cursor-not-allowed opacity-70"
              : "text-muted hover:text-accent border-border hover:border-accent/50"
        )}
      >
        {pdfLoading ? (
          <>
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            {t("results.export.generating" as Parameters<typeof t>[0])}
          </>
        ) : (
          <>
            <Download className="h-3 w-3" aria-hidden="true" />
            {pdfError
              ? (t("errors.pdf_generation_failed" as Parameters<typeof t>[0]))
              : t("results.export.pdf" as Parameters<typeof t>[0])}
          </>
        )}
      </button>
    </div>
  );
}
