import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime, formatElapsedTime } from "@/lib/time";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";

export interface ExpandedDetailProps {
  job: StoredJob;
  panelId: string;
}

export function ExpandedDetail({ job, panelId }: ExpandedDetailProps) {
  const panelBase = "px-4 py-3 text-sm border-t border-border bg-background/50";

  switch (job.status) {
    case "queued":
      return (
        <div id={panelId} role="region" className={panelBase}>
          <p className="text-muted italic">Waiting to be processed...</p>
        </div>
      );

    case "running": {
      const elapsedLabel = formatElapsedTime(job.submittedAt);

      return (
        <div id={panelId} role="region" className={panelBase}>
          {job.stage ? (
            <p className="text-muted">
              <span className="font-medium text-foreground">Stage: </span>
              {job.stage} <span className="text-muted">(processing for {elapsedLabel})</span>
            </p>
          ) : (
            <p className="text-muted italic">Processing... (started {elapsedLabel} ago)</p>
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
              <span>Unsupported or invalid results format</span>
            </div>
            {job.completedAt !== null && (
              <p className="text-xs text-muted">Completed {formatRelativeTime(job.completedAt)}</p>
            )}
          </div>
        );
      }
      return (
        <div id={panelId} role="region" className={cn(panelBase, "space-y-3")}>
          <p className="font-medium text-foreground text-xs uppercase tracking-wide">
            Analysis Result
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-surface border border-border p-2">
              <p className="text-muted">References detected</p>
              <p className="font-semibold text-foreground">
                {job.result.summary.totalReferencesDetected}
              </p>
            </div>
            <div className="rounded-lg bg-surface border border-border p-2">
              <p className="text-muted">References analyzed</p>
              <p className="font-semibold text-foreground">
                {job.result.summary.totalReferencesAnalyzed}
              </p>
            </div>
          </div>
          <div className="rounded-lg bg-surface border border-border p-2 text-xs space-y-1">
            <p className="text-muted font-medium">By classification</p>
            {(Object.entries(job.result.summary.countsByClassification) as [string, number][])
              .filter(([, count]) => count > 0)
              .map(([key, count]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-muted">{key.replace(/_/g, " ")}</span>
                  <span className="font-semibold text-foreground">{count}</span>
                </div>
              ))}
          </div>
          {job.completedAt !== null && (
            <p className="text-xs text-muted">Completed {formatRelativeTime(job.completedAt)}</p>
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
            <p className="text-xs text-muted">Failed {formatRelativeTime(job.completedAt)} ago</p>
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
