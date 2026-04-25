"use client";

import { Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type { JobStatus } from "@/lib/localStorage/recentAnalyses";

export interface StatusBadgeProps {
  status: JobStatus;
}

const STATUS_TO_KEY: Record<JobStatus, string> = {
  queued: "status.queued",
  running: "status.running",
  succeeded: "status.succeeded",
  failed: "status.failed",
  expired: "status.expired",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const t = useTranslations();
  const label = t(STATUS_TO_KEY[status] as Parameters<typeof t>[0]);
  const base = "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium";

  switch (status) {
    case "queued":
      return (
        <span
          aria-label={label}
          className={cn(base, "bg-amber-500/15 text-amber-500 border border-amber-500/30")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          {label}
        </span>
      );
    case "running":
      return (
        <span
          aria-label={label}
          className={cn(base, "bg-blue-500/15 text-blue-400 border border-blue-500/30")}
        >
          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          {label}
        </span>
      );
    case "succeeded":
      return (
        <span
          aria-label={label}
          className={cn(base, "bg-green-500/15 text-green-400 border border-green-500/30")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          {label}
        </span>
      );
    case "failed":
      return (
        <span
          aria-label={label}
          className={cn(base, "bg-red-500/15 text-red-400 border border-red-500/30")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
          {label}
        </span>
      );
    case "expired":
      return (
        <span
          aria-label={label}
          className={cn(base, "bg-surface text-muted border border-border")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          {label}
        </span>
      );
  }
}
