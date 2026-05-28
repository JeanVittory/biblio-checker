"use client";

import { useState, useCallback } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, ExternalLink, Link2 } from "lucide-react";
import { useTranslations, useFormatter, useNow } from "next-intl";
import { cn } from "@/lib/utils";
import { formatElapsedTime } from "@/lib/time";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";
import type { ResultsV1 } from "@/lib/schemas/resultsV1";
import { AuthenticityScore } from "@/components/recent-analyses/AuthenticityScore";
import { ExportButtons } from "@/components/recent-analyses/ExportButtons";
import { ShareButton } from "@/components/recent-analyses/ShareButton";

/** poll_status_token TTL is 1 hour from job creation. */
const POLL_TOKEN_TTL_MS = 60 * 60 * 1000;

function isShareExpired(submittedAt: string): boolean {
  return Date.now() >= new Date(submittedAt).getTime() + POLL_TOKEN_TTL_MS;
}

export interface ExpandedDetailProps {
  job: StoredJob;
  panelId: string;
}

const CLASSIFICATION_STYLES: Record<string, { border: string; bg: string; text: string }> = {
  verified:         { border: "border-green-500/40",  bg: "bg-green-500/10",  text: "text-green-500"  },
  likely_verified:  { border: "border-blue-500/40",   bg: "bg-blue-500/10",   text: "text-blue-500"   },
  ambiguous:        { border: "border-amber-500/40",  bg: "bg-amber-500/10",  text: "text-amber-500"  },
  not_found:        { border: "border-gray-400/40",   bg: "bg-gray-400/10",   text: "text-gray-400"   },
  suspicious:       { border: "border-red-500/40",    bg: "bg-red-500/10",    text: "text-red-500"    },
  processing_error: { border: "border-orange-500/40", bg: "bg-orange-500/10", text: "text-orange-500" },
};

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
      {/* Header - always visible */}
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-surface/60 transition-colors rounded-lg"
      >
        <span className={cn("shrink-0 rounded px-1.5 py-0.5 font-medium text-[10px] uppercase", style.bg, style.text)}>
          {classificationLabel}
        </span>
        <span className="text-muted shrink-0">{reference.referenceId}</span>
        <span className="truncate text-foreground flex-1" title={title}>{title}</span>
        {reference.confidenceScore !== null && (
          <span className="shrink-0 text-muted font-mono">{reference.confidenceScore.toFixed(2)}</span>
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
            <p className="text-foreground bg-surface rounded p-2 leading-relaxed">{reference.rawText}</p>
          </div>

          {/* Normalized fields */}
          <div>
            <p className="text-muted font-medium mb-1">{t("results.section.normalized_fields")}</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 bg-surface rounded p-2">
              {reference.normalized.authors.length > 0 && (
                <Field label={t("results.fields.authors")} value={reference.normalized.authors.join("; ")} />
              )}
              {reference.normalized.year && (
                <Field label={t("results.fields.year")} value={String(reference.normalized.year)} />
              )}
              {reference.normalized.venue && (
                <Field label={t("results.fields.venue")} value={reference.normalized.venue} />
              )}
              {reference.normalized.publisher && (
                <Field label={t("results.fields.publisher")} value={reference.normalized.publisher} />
              )}
              {reference.normalized.doi && (
                <Field label={t("results.fields.doi")} value={reference.normalized.doi} />
              )}
              {reference.normalized.arxivId && (
                <Field label={t("results.fields.arxiv_id")} value={reference.normalized.arxivId} />
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

          {/* Decision reason — pre-translated by worker, rendered verbatim */}
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
                  <div key={i} className="rounded border border-border bg-surface p-2 space-y-2">
                    {/* Candidate header */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="rounded bg-accent/10 px-1.5 py-0.5 font-medium text-accent uppercase text-[10px]">
                        {ev.source}
                      </span>
                      <span className="text-muted">{ev.matchType.replace(/_/g, " ")}</span>
                      <span className="font-mono text-foreground">score: {ev.score.toFixed(4)}</span>
                    </div>

                    {/* Side-by-side comparison */}
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <p className="text-muted font-medium mb-0.5">{t("results.section.reference")}</p>
                        <p className="text-foreground">{reference.normalized.title ?? "—"}</p>
                        <p className="text-muted">{t("results.fields.year")}: {reference.normalized.year ?? "—"}</p>
                      </div>
                      <div>
                        <p className="text-muted font-medium mb-0.5">{t("results.section.candidate")}</p>
                        <p className={cn(
                          "text-foreground",
                          reference.normalized.title &&
                            ev.matchedRecord.title &&
                            reference.normalized.title.toLowerCase() !== ev.matchedRecord.title.toLowerCase() &&
                            "text-amber-500"
                        )}>
                          {ev.matchedRecord.title ?? "—"}
                        </p>
                        <p className={cn(
                          "text-muted",
                          reference.normalized.year &&
                            ev.matchedRecord.year &&
                            reference.normalized.year !== ev.matchedRecord.year &&
                            "text-amber-500 font-medium"
                        )}>
                          {t("results.fields.year")}: {ev.matchedRecord.year ?? "—"}
                        </p>
                      </div>
                    </div>

                    {/* DOI and link */}
                    <div className="flex items-center gap-3 flex-wrap">
                      {ev.matchedRecord.doi && (
                        <span className="text-muted">DOI: {ev.matchedRecord.doi}</span>
                      )}
                      {ev.matchedRecord.url && (
                        <a
                          href={ev.matchedRecord.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-accent hover:underline"
                        >
                          {t("results.section.view_record")} <ExternalLink className="h-3 w-3" />
                        </a>
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

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-muted">{label}: </span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}

export function ExpandedDetail({ job, panelId }: ExpandedDetailProps) {
  const [expandedRefs, setExpandedRefs] = useState<Set<string>>(new Set());
  const t = useTranslations();
  const formatter = useFormatter();
  const now = useNow({ updateInterval: 60_000 });
  const panelBase = "px-4 py-3 text-sm border-t border-border bg-background/50";

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

  switch (job.status) {
    case "queued":
      return (
        <div id={panelId} role="region" className={panelBase}>
          <p className="text-muted italic">{t("status.waiting")}</p>
        </div>
      );

    case "running": {
      const elapsedLabel = formatElapsedTime(job.submittedAt);

      return (
        <div id={panelId} role="region" className={panelBase}>
          {job.stage ? (
            <p className="text-muted">
              {t("status.stage_label", { stage: job.stage })}
              <span className="text-muted"> {t("status.processing_elapsed", { elapsedLabel })}</span>
            </p>
          ) : (
            <p className="text-muted italic">{t("status.processing_started", { elapsedLabel })}</p>
          )}
        </div>
      );
    }

    case "succeeded":
      if (job.result === null) {
        return (
          <div id={panelId} role="region" className={cn(panelBase, "space-y-2")}>
            <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-500">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{t("errors.invalid_results_format")}</span>
            </div>
            {job.completedAt !== null && (
              <p className="text-xs text-muted">
                {formatter.relativeTime(new Date(job.completedAt), now)}
              </p>
            )}
          </div>
        );
      }
      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-3")}>
          {/* Summary */}
          <p className="font-medium text-foreground text-xs uppercase tracking-wide">
            {t("results.section.analysis_result")}
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-surface border border-border p-2">
              <p className="text-muted">{t("results.summary.detected")}</p>
              <p className="font-semibold text-foreground">
                {job.result.summary.totalReferencesDetected}
              </p>
            </div>
            <div className="rounded-lg bg-surface border border-border p-2">
              <p className="text-muted">{t("results.summary.analyzed")}</p>
              <p className="font-semibold text-foreground">
                {job.result.summary.totalReferencesAnalyzed}
              </p>
            </div>
          </div>
          <AuthenticityScore
            countsByClassification={job.result.summary.countsByClassification}
          />
          <div className="rounded-lg bg-surface border border-border p-2 text-xs space-y-1">
            <p className="text-muted font-medium">{t("results.section.analysis_result")}</p>
            {(Object.entries(job.result.summary.countsByClassification) as [string, number][])
              .filter(([, count]) => count > 0)
              .map(([key, count]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted">
                    {t(`results.classification.${key}` as Parameters<typeof t>[0])}
                  </span>
                  <span className="font-semibold text-foreground">{count}</span>
                </div>
              ))}
          </div>

          {/* Reference details */}
          {job.result.references.length > 0 && (
            <div className="space-y-2">
              <p className="font-medium text-foreground text-xs uppercase tracking-wide">
                {t("results.section.reference_details")}
              </p>
              {job.result.references.map((reference) => (
                <ReferenceCard
                  key={reference.referenceId}
                  reference={reference}
                  expanded={expandedRefs.has(reference.referenceId)}
                  onToggle={() => toggleRef(reference.referenceId)}
                />
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            {job.completedAt !== null && (
              <p className="text-xs text-muted">
                {formatter.relativeTime(new Date(job.completedAt), now)}
              </p>
            )}
            <div className="flex items-center gap-2">
              {job.jobToken && !isShareExpired(job.submittedAt) ? (
                <ShareButton jobId={job.jobId} jobToken={job.jobToken} />
              ) : (
                <span
                  className="inline-flex items-center gap-1 rounded px-2 py-1 text-[10px] font-medium text-muted bg-surface border border-border cursor-default"
                  title={t("results.share.expired" as Parameters<typeof t>[0])}
                >
                  <Link2 className="h-3 w-3" />
                  {t("results.share.expired" as Parameters<typeof t>[0])}
                </span>
              )}
              <ExportButtons result={job.result} fileName={job.fileName} />
            </div>
          </div>
        </div>
      );

    case "failed": {
      const GENERIC_INFRA_CODES = new Set([
        "trial_limit_reached",
        "langgraph_flow_failed",
        "unexpected_worker_error",
      ]);
      // Defense-in-depth: legacy jobs in the DB may carry the hardcoded
      // technical error_detail without an error_code propagated. Hide those
      // technical strings from end users regardless.
      const TECHNICAL_DETAIL_STRINGS = new Set([
        "LangGraph analysis flow failed.",
        "An unexpected internal error occurred.",
        "Analysis trial limit reached.",
      ]);

      let failedMessage: string;
      if (job.errorCode === "service_offline") {
        failedMessage = t("errors.service_offline");
      } else if (
        job.errorCode !== null &&
        job.errorCode !== undefined &&
        GENERIC_INFRA_CODES.has(job.errorCode)
      ) {
        failedMessage = t("errors.trial_limit_reached");
      } else if (job.error !== null && TECHNICAL_DETAIL_STRINGS.has(job.error)) {
        failedMessage = t("errors.trial_limit_reached");
      } else {
        failedMessage = job.error ?? t("errors.status_fetch_failed");
      }

      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-1")}>
          <p className="text-red-400">{failedMessage}</p>
          {job.completedAt !== null && (
            <p className="text-xs text-muted">
              {formatter.relativeTime(new Date(job.completedAt), now)}
            </p>
          )}
        </div>
      );
    }

    case "expired":
      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-1")}>
          <p className="text-muted font-medium">{t("status.expired")}</p>
          <p className="text-muted text-xs">{t("errors.status_fetch_failed")}</p>
        </div>
      );
  }
}
