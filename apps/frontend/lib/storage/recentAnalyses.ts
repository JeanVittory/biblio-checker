import type { ResultsV1 } from "@/types/results";

/**
 * Persistent storage layer for recent analysis jobs.
 *
 * Data is stored in localStorage under STORAGE_KEY as a JSON blob conforming
 * to LocalStorageData (schema version 1). All read operations are safe — they
 * return an empty list on missing or corrupt data. Write operations may throw
 * only when the storage quota is exceeded; callers are responsible for
 * surfacing that error to the user.
 */

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "expired";

export interface StoredJob {
  jobId: string;
  jobToken: string;
  fileName: string;
  /** ISO 8601 */
  submittedAt: string;
  status: JobStatus;
  stage: string | null;
  result: ResultsV1 | null;
  error: string | null;
  /** ISO 8601 or null */
  completedAt: string | null;
}

interface LocalStorageData {
  /** Schema version — currently 1. Treat any other value as invalid. */
  version: number;
  jobs: StoredJob[];
  /** ISO 8601 */
  lastUpdated: string;
}

const STORAGE_KEY = "biblio-checker:recent-analyses";
const SCHEMA_VERSION = 1;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Attempts to parse the raw localStorage string into LocalStorageData.
 * Returns null when the value is absent, unparseable, or uses a schema
 * version other than 1.
 */
function parseStorageData(raw: string | null): LocalStorageData | null {
  if (raw === null) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }

  if (
    typeof parsed !== "object" ||
    parsed === null ||
    (parsed as Record<string, unknown>).version !== SCHEMA_VERSION ||
    !Array.isArray((parsed as Record<string, unknown>).jobs)
  ) {
    return null;
  }

  return parsed as LocalStorageData;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Reads and returns the current list of stored jobs.
 *
 * - If the localStorage entry is absent, returns [].
 * - If the entry is present but corrupted or has an unknown schema version,
 *   logs a warning and returns [].
 */
export function readJobs(): StoredJob[] {
  if (typeof window === "undefined") return [];

  const raw = localStorage.getItem(STORAGE_KEY);

  if (raw === null) return [];

  const data = parseStorageData(raw);
  if (data === null) {
    console.warn(
      "[recentAnalyses] localStorage data is corrupted or has an unsupported schema version. Returning empty list."
    );
    return [];
  }

  return data.jobs;
}

/**
 * Serialises the provided jobs array to localStorage.
 *
 * Throws a `DOMException` (QuotaExceededError) if the storage quota is
 * exceeded — callers must handle this and surface it to the user.
 */
export function writeJobs(jobs: StoredJob[]): void {
  if (typeof window === "undefined") return;

  const data: LocalStorageData = {
    version: SCHEMA_VERSION,
    jobs,
    lastUpdated: new Date().toISOString(),
  };

  // May throw QuotaExceededError — intentionally not caught here.
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

/**
 * Creates a new job with status "queued", prepends it to the stored list,
 * persists the list, and returns the newly created job.
 */
export function addJob(jobId: string, jobToken: string, fileName: string): StoredJob {
  const newJob: StoredJob = {
    jobId,
    jobToken,
    fileName,
    submittedAt: new Date().toISOString(),
    status: "queued",
    stage: null,
    result: null,
    error: null,
    completedAt: null,
  };

  const existing = readJobs();
  writeJobs([newJob, ...existing]);

  return newJob;
}

/**
 * Merges `updates` into the stored job identified by `jobId`.
 *
 * The fields `jobId`, `jobToken`, `fileName`, and `submittedAt` are
 * immutable and will NOT be overwritten even if present in `updates`.
 */
export function updateJob(jobId: string, updates: Partial<StoredJob>): void {
  const jobs = readJobs();

  const index = jobs.findIndex((j) => j.jobId === jobId);
  if (index === -1) return;

  const current = jobs[index];

  // Protect immutable identity fields.
  const { jobId: immutableJobId, jobToken, fileName, submittedAt, ...safeUpdates } = updates;
  void immutableJobId;
  void jobToken;
  void fileName;
  void submittedAt;

  jobs[index] = { ...current, ...safeUpdates };

  writeJobs(jobs);
}

/**
 * Removes the job identified by `jobId` from the stored list and persists
 * the result. No-ops silently when the job is not found.
 */
export function removeJob(jobId: string): void {
  const jobs = readJobs();
  writeJobs(jobs.filter((j) => j.jobId !== jobId));
}

/**
 * Returns the stored job identified by `jobId`, or `undefined` if not found.
 * Does not mutate any stored state.
 */
export function getJob(jobId: string): StoredJob | undefined {
  return readJobs().find((j) => j.jobId === jobId);
}
