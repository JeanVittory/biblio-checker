"use client";

import { useState, useCallback, useId } from "react";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/time";
import { StatusBadge } from "./StatusBadge";
import { ExpandedDetail } from "./ExpandedDetail";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";

export interface JobRowProps {
  job: StoredJob;
  onRemove: (jobId: string) => void;
}

export function JobRow({ job, onRemove }: JobRowProps) {
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

  const handleRemoveKeyDown = useCallback((e: React.KeyboardEvent<HTMLButtonElement>) => {
    // Allow Space/Enter to activate without bubbling to the row.
    if (e.key === " " || e.key === "Enter") {
      e.stopPropagation();
    }
  }, []);

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
              aria-label={`Remove job for ${job.fileName}`}
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
