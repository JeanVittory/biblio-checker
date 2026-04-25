"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronDown, ChevronUp, ExternalLink, Loader2 } from "lucide-react";
import { useTranslations, useFormatter } from "next-intl";
import { cn } from "@/lib/utils";
import { AuthenticityScore } from "@/components/recent-analyses/AuthenticityScore";
import { parseResultsV1 } from "@/lib/schemas/resultsV1";
import type { ResultsV1 } from "@/lib/schemas/resultsV1";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SharedAnalysisSuccess {
  success: true;
  jobId: string;
  status: "succeeded";
  result: ResultsV1 | null;
  completedAt: string;
  fileName: string | null;
  expiresAt: string;
}

type PageState =
  | { phase: "loading" }
  | { phase: "success"; data: SharedAnalysisSuccess }
  | { phase: "error" };

// ---------------------------------------------------------------------------
// Classification styles (mirrors ExpandedDetail)
// ---------------------------------------------------------------------------

const CLASSIFICATION_STYLES: Record<string, { border: string; bg: string; text: string }> = {
  verified:         { border: "border-green-500/40",  bg: "bg-green-500/10",  text: "text-green-500"  },
  likely_verified:  { border: "border-blue-500/40",   bg: "bg-blue-500/10",   text: "text-blue-500"   },
  ambiguous:        { border: "border-amber-500/40",  bg: "bg-amber-500/10",  text: "text-amber-500"  },
  not_found:        { border: "border-gray-400/40",   bg: "bg-gray-400/10",   text: "text-gray-400"   },
  suspicious:       { border: "border-red-500/40",    bg: "bg-red-500/10",    text: "text-red-500"    },
  processing_error: { border: "border-orange-500/40", bg: "bg-orange-500/10", text: "text-orange-500" },
};

// ---------------------------------------------------------------------------
// Field helper
// ---------------------------------------------------------------------------

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted">{label}: </span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Safe URL guard — only http/https rendered as links
// ---------------------------------------------------------------------------

function isSafeUrl(url: string): boolean {
  return url.startsWith("https://") || url.startsWith("http://");
}

// ---------------------------------------------------------------------------
// Reference card (replicated pattern from ExpandedDetail, read-only)
// ---------------------------------------------------------------------------

type ReferenceResult = ResultsV1["references"][number];

function ReferenceCard({
  reference,
  expanded,
  onToggle,
}: {
  reference: ReferenceResult;
  expanded: boolean;
  onToggle: () => void;
}) {
  const t = useTranslations();
  const style = CLASSIFICATION_STYLES[reference.classification] ?? CLASSIFICATION_STYLES.not_found;
  const classificationLabel = t(
    `results.classification.${reference.classification}` as Parameters<typeof t>[0]
  );
  const title = reference.normalized.title ?? reference.rawText.slice(0, 80);

  return (
    <div className={cn("rounded-lg border", style.border)}>
      {/* Header — always visible */}
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-surface/60 transition-colors rounded-lg"
      >
        <span
          className={cn(
            "shrink-0 rounded px-1.5 py-0.5 font-medium text-[10px] uppercase",
            style.bg,
            style.text
          )}
        >
          {classificationLabel}
        </span>
        <span className="text-muted shrink-0">{reference.referenceId}</span>
        <span className="truncate text-foreground flex-1" title={title}>
          {title}
        </span>
        {reference.confidenceScore !== null && (
          <span className="shrink-0 text-muted font-mono">
            {reference.confidenceScore.toFixed(2)}
          </span>
        )}
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5 shrink-0 text-muted" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted" />
        )}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border px-3 py-3 space-y-3 text-xs">
          {/* Raw text */}
          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.raw_text")}</p>
            <p className="text-foreground bg-surface rounded p-2 leading-relaxed">
              {reference.rawText}
            </p>
          </div>

          {/* Normalized fields */}
          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.normalized_fields")}</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 bg-surface rounded p-2">
              {reference.normalized.authors.length > 0 && (
                <Field
                  label={t("results.fields.authors")}
                  value={reference.normalized.authors.join("; ")}
                />
              )}
              {reference.normalized.year && (
                <Field
                  label={t("results.fields.year")}
                  value={String(reference.normalized.year)}
                />
              )}
              {reference.normalized.venue && (
                <Field label={t("results.fields.venue")} value={reference.normalized.venue} />
              )}
              {reference.normalized.publisher && (
                <Field
                  label={t("results.fields.publisher")}
                  value={reference.normalized.publisher}
                />
              )}
              {reference.normalized.doi && (
                <Field label={t("results.fields.doi")} value={reference.normalized.doi} />
              )}
              {reference.normalized.arxivId && (
                <Field
                  label={t("results.fields.arxiv_id")}
                  value={reference.normalized.arxivId}
                />
              )}
              {reference.normalized.issn && (
                <Field label={t("results.fields.issn")} value={reference.normalized.issn} />
              )}
              {reference.normalized.volume && (
                <Field label={t("results.fields.volume")} value={reference.normalized.volume} />
              )}
              {reference.normalized.issue && (
                <Field label={t("results.fields.issue")} value={reference.normalized.issue} />
              )}
              {reference.normalized.pages && (
                <Field label={t("results.fields.pages")} value={reference.normalized.pages} />
              )}
            </div>
          </div>

          {/* Decision reason */}
          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.decision_reason")}</p>
            <p className="text-foreground bg-surface rounded p-2">{reference.decisionReason}</p>
          </div>

          {/* Evidence / candidates */}
          {reference.evidence.length > 0 && (
            <div>
              <p className="text-muted font-medium mb-1">
                {t("results.section.candidates_found", { count: reference.evidence.length })}
              </p>
              <div className="space-y-2">
                {reference.evidence.map((ev, i) => (
                  <div
                    key={i}
                    className="rounded border border-border bg-surface p-2 space-y-2"
                  >
                    {/* Candidate header */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="rounded bg-accent/10 px-1.5 py-0.5 font-medium text-accent uppercase text-[10px]">
                        {ev.source}
                      </span>
                      <span className="text-muted">{ev.matchType.replace(/_/g, " ")}</span>
                      <span className="font-mono text-foreground">
                        score: {ev.score.toFixed(4)}
                      </span>
                    </div>

                    {/* Side-by-side comparison */}
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <p className="text-muted font-medium mb-0.5">
                          {t("results.section.reference")}
                        </p>
                        <p className="text-foreground">
                          {reference.normalized.title ?? "—"}
                        </p>
                        <p className="text-muted">
                          {t("results.fields.year")}: {reference.normalized.year ?? "—"}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted font-medium mb-0.5">
                          {t("results.section.candidate")}
                        </p>
                        <p
                          className={cn(
                            "text-foreground",
                            reference.normalized.title &&
                              ev.matchedRecord.title &&
                              reference.normalized.title.toLowerCase() !==
                                ev.matchedRecord.title.toLowerCase() &&
                              "text-amber-500"
                          )}
                        >
                          {ev.matchedRecord.title ?? "—"}
                        </p>
                        <p
                          className={cn(
                            "text-muted",
                            reference.normalized.year &&
                              ev.matchedRecord.year &&
                              reference.normalized.year !== ev.matchedRecord.year &&
                              "text-amber-500 font-medium"
                          )}
                        >
                          {t("results.fields.year")}: {ev.matchedRecord.year ?? "—"}
                        </p>
                      </div>
                    </div>

                    {/* DOI and link */}
                    <div className="flex items-center gap-3 flex-wrap">
                      {ev.matchedRecord.doi && (
                        <span className="text-muted">DOI: {ev.matchedRecord.doi}</span>
                      )}
                      {ev.matchedRecord.url && isSafeUrl(ev.matchedRecord.url) && (
                        <a
                          href={ev.matchedRecord.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-accent hover:underline"
                        >
                          {t("results.section.view_record")}{" "}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                      {ev.matchedRecord.url && !isSafeUrl(ev.matchedRecord.url) && (
                        <span className="text-muted">{ev.matchedRecord.url}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {reference.evidence.length === 0 && (
            <p className="text-muted italic">{t("results.no_candidates")}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page header (shared across all states)
// ---------------------------------------------------------------------------

function PageHeader({ subtitle }: { subtitle?: string }) {
  const t = useTranslations();
  return (
    <header className="mb-8">
      <h1 className="text-2xl font-bold tracking-tight">
        <span
          className="bg-clip-text text-transparent"
          style={{
            backgroundImage:
              "linear-gradient(135deg, var(--accent), var(--accent-secondary))",
          }}
        >
          {t("common.app_name" as Parameters<typeof t>[0])}
        </span>
      </h1>
      {subtitle && (
        <p className="mt-1 text-sm text-muted">{subtitle}</p>
      )}
    </header>
  );
}

// ---------------------------------------------------------------------------
// Main share page component
// ---------------------------------------------------------------------------

export default function SharePage() {
  const params = useParams<{ shareToken: string }>();
  const shareToken = params?.shareToken ?? "";

  const t = useTranslations();
  const formatter = useFormatter();

  const [state, setState] = useState<PageState>({ phase: "loading" });
  const [expandedRefs, setExpandedRefs] = useState<Set<string>>(new Set());

  const toggleRef = useCallback((refId: string) => {
    setExpandedRefs((prev) => {
      const next = new Set(prev);
      if (next.has(refId)) {
        next.delete(refId);
      } else {
        next.add(refId);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    if (!shareToken) {
      setState({ phase: "error" });
      return;
    }

    let cancelled = false;

    async function fetchSharedAnalysis() {
      try {
        const response = await fetch(`/api/shared/${encodeURIComponent(shareToken)}`);

        if (cancelled) return;

        if (!response.ok) {
          setState({ phase: "error" });
          return;
        }

        let body: unknown;
        try {
          body = await response.json();
        } catch {
          setState({ phase: "error" });
          return;
        }

        if (
          typeof body !== "object" ||
          body === null ||
          (body as Record<string, unknown>).success !== true
        ) {
          setState({ phase: "error" });
          return;
        }

        const raw = body as Record<string, unknown>;

        // Validate and parse result field through resultsV1 schema.
        const parsedResult = parseResultsV1(raw.result);

        const data: SharedAnalysisSuccess = {
          success: true,
          jobId: typeof raw.jobId === "string" ? raw.jobId : "",
          status: "succeeded",
          result: parsedResult,
          completedAt: typeof raw.completedAt === "string" ? raw.completedAt : "",
          fileName: typeof raw.fileName === "string" ? raw.fileName : null,
          expiresAt: typeof raw.expiresAt === "string" ? raw.expiresAt : "",
        };

        setState({ phase: "success", data });
      } catch {
        if (!cancelled) {
          setState({ phase: "error" });
        }
      }
    }

    fetchSharedAnalysis();

    return () => {
      cancelled = true;
    };
  }, [shareToken]);

  // --- Loading state ---
  if (state.phase === "loading") {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
          <PageHeader />
          <div className="flex items-center gap-3 text-muted">
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
            <p>{t("sharePage.loading" as Parameters<typeof t>[0])}</p>
          </div>
        </div>
      </div>
    );
  }

  // --- Error / not found state ---
  if (state.phase === "error") {
    return (
      <div className="min-h-screen bg-background text-foreground">
        <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
          <PageHeader />
          <div className="rounded-lg border border-border bg-surface p-6 space-y-4">
            <p className="text-foreground">
              {t("sharePage.notFound" as Parameters<typeof t>[0])}
            </p>
            <Link
              href="/"
              className="inline-flex items-center gap-1 text-sm text-accent hover:underline"
            >
              {t("sharePage.tryBiblio" as Parameters<typeof t>[0])} →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // --- Success state ---
  const { data } = state;
  const subtitle = t("sharePage.title" as Parameters<typeof t>[0]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 space-y-6">
        <PageHeader subtitle={subtitle} />

        {/* File name */}
        {data.fileName !== null && (
          <p className="text-sm text-muted">
            <span className="font-medium text-foreground">{data.fileName}</span>
          </p>
        )}

        {/* Result null — graceful degradation */}
        {data.result === null && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-500">
            {t("sharePage.resultError" as Parameters<typeof t>[0])}
          </div>
        )}

        {data.result !== null && (
          <>
            {/* Authenticity Score */}
            <AuthenticityScore
              countsByClassification={data.result.summary.countsByClassification}
            />

            {/* Summary counts */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-surface border border-border p-3">
                <p className="text-muted">{t("results.summary.detected")}</p>
                <p className="font-semibold text-foreground text-base">
                  {data.result.summary.totalReferencesDetected}
                </p>
              </div>
              <div className="rounded-lg bg-surface border border-border p-3">
                <p className="text-muted">{t("results.summary.analyzed")}</p>
                <p className="font-semibold text-foreground text-base">
                  {data.result.summary.totalReferencesAnalyzed}
                </p>
              </div>
            </div>

            {/* Classification breakdown */}
            <div className="rounded-lg bg-surface border border-border p-3 text-xs space-y-1">
              <p className="text-muted font-medium">
                {t("results.section.analysis_result")}
              </p>
              {(
                Object.entries(
                  data.result.summary.countsByClassification
                ) as [string, number][]
              )
                .filter(([, count]) => count > 0)
                .map(([key, count]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-muted">
                      {t(
                        `results.classification.${key}` as Parameters<typeof t>[0]
                      )}
                    </span>
                    <span className="font-semibold text-foreground">{count}</span>
                  </div>
                ))}
            </div>

            {/* Reference details */}
            {data.result.references.length > 0 && (
              <div className="space-y-2">
                <p className="font-medium text-foreground text-xs uppercase tracking-wide">
                  {t("results.section.reference_details")}
                </p>
                {data.result.references.map((reference) => (
                  <ReferenceCard
                    key={reference.referenceId}
                    reference={reference}
                    expanded={expandedRefs.has(reference.referenceId)}
                    onToggle={() => toggleRef(reference.referenceId)}
                  />
                ))}
              </div>
            )}
          </>
        )}

        {/* Footer */}
        <footer className="border-t border-border pt-6 space-y-2 text-sm text-muted">
          {data.expiresAt && (
            <p>
              {t("sharePage.expiresOn" as Parameters<typeof t>[0], {
                date: formatter.dateTime(new Date(data.expiresAt), "short"),
              })}
            </p>
          )}
          <p>{t("sharePage.poweredBy" as Parameters<typeof t>[0])}</p>
          <Link href="/" className="inline-flex items-center gap-1 text-accent hover:underline">
            {t("sharePage.tryBiblio" as Parameters<typeof t>[0])} →
          </Link>
        </footer>
      </div>
    </div>
  );
}
