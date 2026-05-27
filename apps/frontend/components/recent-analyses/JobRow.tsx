"use client";

import { useState, useCallback, useId } from "react";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { useTranslations, useFormatter, useNow } from "next-intl";
import { cn } from "@/lib/utils";
import { StatusBadge } from "./StatusBadge";
import { ExpandedDetail } from "./ExpandedDetail";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";

// ---------------------------------------------------------------------------
// InputKindBadge — small pill distinguishing upload mode from paste mode
// ---------------------------------------------------------------------------

interface InputKindBadgeProps {
  job: StoredJob;
}

function InputKindBadge({ job }: InputKindBadgeProps) {
  const t = useTranslations("recent.badge");
  const inputKind = job.inputKind ?? "file";

  if (inputKind === "text") {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium",
          "bg-accent/10 text-accent border border-accent/20"
        )}
        aria-label={t("text_tooltip")}
        title={t("text_tooltip")}
      >
        {/* i18n key: recent.badge.text */}
        {t("text")}
      </span>
    );
  }

  // File mode — infer PDF / DOCX from the display name extension.
  const displayName = job.fileName ?? "";
  const lower = displayName.toLowerCase();

  if (lower.endsWith(".pdf")) {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium",
          "bg-muted/20 text-muted border border-border"
        )}
        aria-label={t("pdf_tooltip")}
        title={t("pdf_tooltip")}
      >
        {/* i18n key: recent.badge.pdf */}
        {t("pdf")}
      </span>
    );
  }

  if (lower.endsWith(".docx")) {
    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium",
          "bg-muted/20 text-muted border border-border"
        )}
        aria-label={t("docx_tooltip")}
        title={t("docx_tooltip")}
      >
        {/* i18n key: recent.badge.docx */}
        {t("docx")}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium",
        "bg-muted/20 text-muted border border-border"
      )}
      aria-label={t("document_tooltip")}
      title={t("document_tooltip")}
    >
      {/* i18n key: recent.badge.document */}
      {t("document")}
    </span>
  );
}

export interface JobRowProps {
  job: StoredJob;
  onRemove: (jobId: string) => void;
}

export function JobRow({ job, onRemove }: JobRowProps) {
  const [expanded, setExpanded] = useState(false);
  const t = useTranslations("recent");
  const formatter = useFormatter();
  const now = useNow({ updateInterval: 60_000 });

  // Stable IDs for ARIA relationships.
  const baseId = useId();
  const buttonId = `${baseId}-toggle`;
  const panelId = `${baseId}-panel`;

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const handleRemove = useCallback(
    (e: React.MouseEvent<HTMLButtonElement>) => {
      // Prevent the row's toggle handler from firing.
      e.stopPropagation();
      onRemove(job.jobId);
    },
    [job.jobId, onRemove]
  );

  const handleRemoveKeyDown = useCallback((e: React.KeyboardEvent<HTMLButtonElement>) => {
    // Allow Space/Enter to activate without bubbling to the row.
    if (e.key === " " || e.key === "Enter") {
      e.stopPropagation();
    }
  }, []);

  const relativeTime = formatter.relativeTime(new Date(job.submittedAt), now);

  return (
    <tbody>
      <tr
        className={cn(
          "border-b border-border transition-colors",
          "hover:bg-surface/60 cursor-pointer",
          expanded && "bg-surface/40"
        )}
        onClick={handleToggle}
        // The row itself is not focusable — the toggle button inside handles
        // keyboard navigation.
      >
        {/* Display name + input-kind badge */}
        <td className="px-4 py-3 text-sm text-foreground max-w-[200px]">
          <div className="flex items-center gap-1.5 min-w-0">
            <InputKindBadge job={job} />
            {/*
             * User-supplied; React text-node escaping is the only XSS defense.
             * For text-mode rows, rawTextPreview (up to 500 chars) is used as the
             * tooltip so the user can see the full citation on hover.
             * For file-mode rows, the displayName itself is the tooltip.
             */}
            <span
              className="truncate"
              title={
                (job.inputKind ?? "file") === "text" && job.rawTextPreview !== undefined
                  ? job.rawTextPreview
                  : job.fileName
              }
            >
              {/* User-supplied; React text-node escaping is the only XSS defense. */}
              {job.fileName}
            </span>
          </div>
        </td>

        {/* Submitted at */}
        <td className="px-4 py-3 text-sm text-muted whitespace-nowrap">
          <time dateTime={job.submittedAt} title={new Date(job.submittedAt).toLocaleString()}>
            {relativeTime}
          </time>
        </td>

        {/* Status badge */}
        <td className="px-4 py-3">
          <StatusBadge status={job.status} />
        </td>

        {/* Actions */}
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {/* Expand/collapse toggle */}
            <button
              id={buttonId}
              type="button"
              aria-expanded={expanded}
              aria-controls={panelId}
              aria-label={expanded ? t("actions.hide_details") : t("actions.view_details")}
              onClick={handleToggle}
              className={cn(
                "flex items-center justify-center rounded-md p-1 transition-colors",
                "text-muted hover:text-foreground hover:bg-border/50",
                "focus-visible:outline focus-visible:outline-accent focus-visible:outline-offset-1"
              )}
            >
              {expanded ? (
                <ChevronUp className="h-4 w-4" aria-hidden="true" />
              ) : (
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              )}
            </button>

            {/* Remove button */}
            <button
              type="button"
              aria-label={t("actions.remove_job")}
              onClick={handleRemove}
              onKeyDown={handleRemoveKeyDown}
              className={cn(
                "flex items-center justify-center rounded-md p-1 transition-colors",
                "text-muted hover:text-red-400 hover:bg-red-500/10",
                "focus-visible:outline  focus-visible:outline-red-400 focus-visible:outline-offset-1"
              )}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </td>
      </tr>

      {/* Expanded detail panel — rendered as its own row spanning all columns */}
      {expanded && (
        <tr>
          <td colSpan={4} className="p-0">
            <ExpandedDetail job={job} panelId={panelId} />
          </td>
        </tr>
      )}
    </tbody>
  );
}
