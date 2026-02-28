"use client";

/**
 * useRecentAnalysesPolling
 *
 * Manages the lifecycle of recent-analysis jobs stored in localStorage.
 * For each job in the "queued" or "running" state it opens an independent
 * polling interval (every 4 s) against the /api/jobs/status proxy route.
 *
 * Transient failures (network errors, 502) are silently retried on the next
 * interval. Terminal statuses (succeeded, failed, expired) stop polling
 * automatically. On unmount every active interval is cleared.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
  readJobs,
  addJob,
  updateJob,
  removeJob,
  type StoredJob,
  type JobStatus,
} from "@/lib/localStorage/recentAnalyses";
import { API_ROUTES, HTTP_STATUS } from "@/lib/constants";
import { parseResultsV1 } from "@/lib/schemas/resultsV1";

const POLL_INTERVAL_MS = 4_000;

/** Statuses that indicate the job has reached a terminal state. */
const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set([
  "succeeded",
  "failed",
  "expired",
]);

/** Statuses for which polling should be active. */
const ACTIVE_STATUSES: ReadonlySet<JobStatus> = new Set(["queued", "running"]);

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseRecentAnalysesPollingResult {
  /** Live list of StoredJob, kept in sync with localStorage on each update. */
  jobs: StoredJob[];
  /** Adds a job to localStorage and immediately starts polling for it. */
  addTrackedJob: (jobId: string, jobToken: string, fileName: string) => void;
  /** Removes a job from localStorage and cancels its polling interval. */
  removeTrackedJob: (jobId: string) => void;
}

export function useRecentAnalysesPolling(): UseRecentAnalysesPollingResult {
  const [jobs, setJobs] = useState<StoredJob[]>(() => readJobs());

  /**
   * Maps jobId → setInterval return value for every currently active poll.
   * Using a ref avoids stale closure issues and prevents unnecessary
   * re-renders when the interval map changes.
   */
  const intervals = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  /**
   * Tracks which job IDs currently have a pending fetch in-flight.
   * Prevents concurrent requests for the same job when a poll takes longer
   * than the interval (spec 08-R11: no more than one request per job per
   * polling interval).
   */
  const inFlight = useRef<Set<string>>(new Set());

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  /**
   * Reads the latest snapshot from localStorage and pushes it into React
   * state so the UI reflects the most current data.
   */
  const syncJobsFromStorage = useCallback(() => {
    setJobs(readJobs());
  }, []);

  /**
   * Cancels the polling interval for `jobId` if one is active.
   */
  const stopPolling = useCallback((jobId: string) => {
    const id = intervals.current.get(jobId);
    if (id !== undefined) {
      clearInterval(id);
      intervals.current.delete(jobId);
    }
  }, []);

  /**
   * Performs a single poll for `jobId` / `jobToken`.
   *
   * - 200: merges the updated fields into localStorage.
   * - 401 / 404: marks the job as expired.
   * - Network error / 502: transient — does nothing (next interval retries).
   *
   * After each successful update the React state is re-synced from storage.
   */
  const pollOnce = useCallback(
    async (jobId: string, jobToken: string) => {
      // Guard: skip if a fetch for this job is already in-flight (08-R11).
      if (inFlight.current.has(jobId)) return;
      inFlight.current.add(jobId);

      try {
        const url =
          `${API_ROUTES.JOBS_STATUS}` +
          `?jobId=${encodeURIComponent(jobId)}` +
          `&jobToken=${encodeURIComponent(jobToken)}`;

        let response: Response;
        try {
          response = await fetch(url, { method: "GET" });
        } catch {
          // Network failure — transient, retry on next interval.
          return;
        }

        if (response.status === HTTP_STATUS.UNAUTHORIZED || response.status === HTTP_STATUS.NOT_FOUND) {
          updateJob(jobId, { status: "expired" });
          stopPolling(jobId);
          syncJobsFromStorage();
          return;
        }

        // 502 or other non-200 transient errors — retry on next interval.
        if (!response.ok) {
          return;
        }

        // 200 — parse and persist the new state.
        let body: unknown;
        try {
          body = await response.json();
        } catch {
          // Unexpected non-JSON body from proxy — transient.
          return;
        }

        if (typeof body !== "object" || body === null) return;

        const data = body as Record<string, unknown>;

        const status =
          typeof data.status === "string" && isValidJobStatus(data.status)
            ? (data.status as JobStatus)
            : undefined;

        const updates: Partial<StoredJob> = {};
        if (status !== undefined) updates.status = status;
        if (typeof data.stage === "string") updates.stage = data.stage;
        if (typeof data.stage === "object") updates.stage = null; // reset if backend clears it
        if ("result" in data) {
          updates.result = parseResultsV1(data.result);
        }
        if (typeof data.error === "string") updates.error = data.error;
        if (typeof data.completedAt === "string") updates.completedAt = data.completedAt;

        updateJob(jobId, updates);
        syncJobsFromStorage();

        // Stop polling once a terminal state is reached.
        if (status !== undefined && TERMINAL_STATUSES.has(status)) {
          stopPolling(jobId);
        }
      } finally {
        inFlight.current.delete(jobId);
      }
    },
    [stopPolling, syncJobsFromStorage]
  );

  /**
   * Starts a polling interval for the given job if one is not already active.
   */
  const startPolling = useCallback(
    (jobId: string, jobToken: string) => {
      if (intervals.current.has(jobId)) return;

      const id = setInterval(() => {
        pollOnce(jobId, jobToken);
      }, POLL_INTERVAL_MS);

      intervals.current.set(jobId, id);
    },
    [pollOnce]
  );

  // ---------------------------------------------------------------------------
  // On mount: resume polling for any queued / running jobs from localStorage.
  // ---------------------------------------------------------------------------

  useEffect(() => {
    const stored = readJobs();

    stored.forEach((job) => {
      if (ACTIVE_STATUSES.has(job.status)) {
        startPolling(job.jobId, job.jobToken);
      }
    });

    // Capture ref value for cleanup.
    const activeIntervals = intervals.current;

    return () => {
      activeIntervals.forEach((id) => clearInterval(id));
      activeIntervals.clear();
    };
  }, [startPolling]);

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  const addTrackedJob = useCallback(
    (jobId: string, jobToken: string, fileName: string) => {
      addJob(jobId, jobToken, fileName);
      syncJobsFromStorage();
      startPolling(jobId, jobToken);
    },
    [syncJobsFromStorage, startPolling]
  );

  const removeTrackedJob = useCallback(
    (jobId: string) => {
      stopPolling(jobId);
      removeJob(jobId);
      syncJobsFromStorage();
    },
    [stopPolling, syncJobsFromStorage]
  );

  return { jobs, addTrackedJob, removeTrackedJob };
}

// ---------------------------------------------------------------------------
// Type guard
// ---------------------------------------------------------------------------

const VALID_JOB_STATUSES: ReadonlySet<string> = new Set([
  "queued",
  "running",
  "succeeded",
  "failed",
  "expired",
]);

function isValidJobStatus(value: string): boolean {
  return VALID_JOB_STATUSES.has(value);
}
