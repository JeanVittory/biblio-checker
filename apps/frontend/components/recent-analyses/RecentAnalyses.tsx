"use client";

import { useId } from "react";
import { JobRow } from "./JobRow";
import { StorageErrorBanner } from "./StorageErrorBanner";
import type { StoredJob } from "@/lib/localStorage/recentAnalyses";

export interface RecentAnalysesProps {
  jobs: StoredJob[];
  onRemoveJob: (jobId: string) => void;
  /** Set to true when a localStorage quota error has occurred. */
  storageFullError?: boolean;
  /** Set to true when localStorage data could not be parsed. */
  storageCorruptedError?: boolean;
}

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
      <h3 id={`${tableId}-heading`} className="text-sm font-semibold text-foreground">
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
