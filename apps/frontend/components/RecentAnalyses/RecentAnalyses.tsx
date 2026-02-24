"use client";

/**
 * RecentAnalyses
 *
 * Displays a table of recently submitted analysis jobs sourced from
 * localStorage via the useRecentAnalysesPolling hook. Each row is expandable
 * to reveal per-job detail appropriate to its current status.
 *
 * Accepts an explicit `jobs` prop (from the hook) and an `onRemoveJob`
 * callback so the parent controls the data lifecycle while this component
 * remains purely presentational.
 */

import { useState, useCallback, useId } from "react";
import { Loader2, ChevronDown, ChevronUp, Trash2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StoredJob, JobStatus } from "@/lib/storage/recentAnalyses";

// ---------------------------------------------------------------------------
// Public component props
// ---------------------------------------------------------------------------

export interface RecentAnalysesProps {
  jobs: StoredJob[];
  onRemoveJob: (jobId: string) => void;
  /** Set to true when a localStorage quota error has occurred. */
  storageFullError?: boolean;
  /** Set to true when localStorage data could not be parsed. */
  storageCorruptedError?: boolean;
}

// ---------------------------------------------------------------------------
// Relative time helper
// ---------------------------------------------------------------------------

function formatRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffSeconds = Math.floor(diffMs / 1_000);

  if (diffSeconds < 60) return "Just now";

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

// ---------------------------------------------------------------------------
// Status badge sub-component
// ---------------------------------------------------------------------------

interface StatusBadgeProps {
  status: JobStatus;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const base =
    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium";

  switch (status) {
    case "queued":
      return (
        <span aria-label="queued" className={cn(base, "bg-amber-500/15 text-amber-500 border border-amber-500/30")}>
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Queued
        </span>
      );
    case "running":
      return (
        <span aria-label="running" className={cn(base, "bg-blue-500/15 text-blue-400 border border-blue-500/30")}>
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          Running
        </span>
      );
    case "succeeded":
      return (
        <span aria-label="succeeded" className={cn(base, "bg-green-500/15 text-green-400 border border-green-500/30")}>
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
          Succeeded
        </span>
      );
    case "failed":
      return (
        <span aria-label="failed" className={cn(base, "bg-red-500/15 text-red-400 border border-red-500/30")}>
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          Failed
        </span>
      );
    case "expired":
      return (
        <span aria-label="expired" className={cn(base, "bg-surface text-muted border border-border")}>
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Expired
        </span>
      );
  }
}

// ---------------------------------------------------------------------------
// Expanded detail panel sub-component
// ---------------------------------------------------------------------------

interface ExpandedDetailProps {
  job: StoredJob;
  panelId: string;
}

function ExpandedDetail({ job, panelId }: ExpandedDetailProps) {
  const panelBase =
    "px-4 py-3 text-sm border-t border-border bg-background/50";

  switch (job.status) {
    case "queued":
      return (
        <div id={panelId} role="region" className={panelBase}>
          <p className="text-muted italic">Waiting to be processed...</p>
        </div>
      );

    case "running": {
      const elapsedMs = Date.now() - new Date(job.submittedAt).getTime();
      const elapsedMinutes = Math.floor(elapsedMs / 60_000);
      const elapsedLabel =
        elapsedMinutes < 1 ? "less than a minute" : `${elapsedMinutes} minute${elapsedMinutes === 1 ? "" : "s"}`;

      return (
        <div id={panelId} role="region" className={panelBase}>
          {job.stage ? (
            <p className="text-muted">
              <span className="font-medium text-foreground">Stage: </span>
              {job.stage}{" "}
              <span className="text-muted">(processing for {elapsedLabel})</span>
            </p>
          ) : (
            <p className="text-muted italic">
              Processing... (started {elapsedLabel} ago)
            </p>
          )}
        </div>
      );
    }

    case "succeeded":
      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-2")}>
          <p className="font-medium text-foreground text-xs uppercase tracking-wide text-muted">
            Result
          </p>
          <pre className="overflow-x-auto rounded-lg bg-surface border border-border p-3 text-xs text-foreground leading-relaxed">
            {JSON.stringify(job.result, null, 2)}
          </pre>
          {job.completedAt !== null && (
            <p className="text-xs text-muted">
              Completed {formatRelativeTime(job.completedAt)}
            </p>
          )}
        </div>
      );

    case "failed":
      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-1")}>
          <p className="text-red-400">
            <span className="font-medium">Error: </span>
            {job.error ?? "An unknown error occurred during processing."}
          </p>
          {job.completedAt !== null && (
            <p className="text-xs text-muted">
              Failed {formatRelativeTime(job.completedAt)} ago
            </p>
          )}
        </div>
      );

    case "expired":
      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-1")}>
          <p className="text-muted font-medium">Token invalid or expired</p>
          <p className="text-muted text-xs">
            This job cannot be accessed anymore (token expired or not found).
          </p>
          <p className="text-muted text-xs">
            You can remove this entry and re-upload the document if needed.
          </p>
        </div>
      );
  }
}

// ---------------------------------------------------------------------------
// Individual table row sub-component
// ---------------------------------------------------------------------------

interface JobRowProps {
  job: StoredJob;
  onRemove: (jobId: string) => void;
}

function JobRow({ job, onRemove }: JobRowProps) {
  const [expanded, setExpanded] = useState(false);

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

  const handleRemoveKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>) => {
      // Allow Space/Enter to activate without bubbling to the row.
      if (e.key === " " || e.key === "Enter") {
        e.stopPropagation();
      }
    },
    []
  );

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
        {/* File name */}
        <td className="px-4 py-3 text-sm text-foreground max-w-[200px] truncate">
          <span title={job.fileName}>{job.fileName}</span>
        </td>

        {/* Submitted at */}
        <td className="px-4 py-3 text-sm text-muted whitespace-nowrap">
          <time dateTime={job.submittedAt} title={new Date(job.submittedAt).toLocaleString()}>
            {formatRelativeTime(job.submittedAt)}
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
              aria-label={expanded ? "Collapse details" : "Expand details"}
              onClick={handleToggle}
              className={cn(
                "flex items-center justify-center rounded-md p-1 transition-colors",
                "text-muted hover:text-foreground hover:bg-border/50",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-1"
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
              aria-label={`Remove job for ${job.fileName}`}
              onClick={handleRemove}
              onKeyDown={handleRemoveKeyDown}
              className={cn(
                "flex items-center justify-center rounded-md p-1 transition-colors",
                "text-muted hover:text-red-400 hover:bg-red-500/10",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-red-400 focus-visible:outline-offset-1"
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

// ---------------------------------------------------------------------------
// Storage error banner sub-component
// ---------------------------------------------------------------------------

type StorageErrorBannerProps = {
  variant: "full" | "corrupted";
};

function StorageErrorBanner({ variant }: StorageErrorBannerProps) {
  const message =
    variant === "full"
      ? "Storage full. Please remove old jobs to continue."
      : "Unable to load job history. Data may be corrupted.";

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-2 rounded-lg border p-3 text-sm",
        "border-amber-500/30 bg-amber-500/5 text-amber-500"
      )}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------

export function RecentAnalyses({
  jobs,
  onRemoveJob,
  storageFullError = false,
  storageCorruptedError = false,
}: RecentAnalysesProps) {
  const tableId = useId();

  const hasStorageErrors = storageFullError || storageCorruptedError;

  // When there are no jobs and no storage errors, render nothing per spec.
  if (jobs.length === 0 && !hasStorageErrors) {
    return null;
  }

  // When there are no jobs but there are storage error banners to show,
  // render the banners without the table.
  if (jobs.length === 0) {
    return (
      <div className="w-full space-y-3">
        {storageFullError && <StorageErrorBanner variant="full" />}
        {storageCorruptedError && <StorageErrorBanner variant="corrupted" />}
      </div>
    );
  }

  return (
    <section aria-labelledby={`${tableId}-heading`} className="w-full space-y-3">
      <h3
        id={`${tableId}-heading`}
        className="text-sm font-semibold text-foreground"
      >
        Recent Analyses
      </h3>

      {/* Storage error banners */}
      {storageFullError && <StorageErrorBanner variant="full" />}
      {storageCorruptedError && <StorageErrorBanner variant="corrupted" />}

      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left">
            <thead>
              <tr className="border-b border-border">
                <th
                  scope="col"
                  className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  File
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted whitespace-nowrap"
                >
                  Submitted
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  Status
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  Actions
                </th>
              </tr>
            </thead>

            {jobs.map((job) => (
              <JobRow key={job.jobId} job={job} onRemove={onRemoveJob} />
            ))}
          </table>
        </div>
      </div>
    </section>
  );
}
