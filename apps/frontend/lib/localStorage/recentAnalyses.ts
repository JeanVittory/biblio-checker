import type { ResultsV1 } from "@/lib/schemas/resultsV1";
import logger from "@/lib/logger";
const log = logger.child({ module: "recentAnalyses" });

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
  /**
   * Display name shown in the Recent Analyses table.
   * For file-mode jobs this is the original file name.
   * For text-mode jobs this is the first 60 chars of the pasted text (+ ellipsis).
   * Kept as `fileName` in the persisted schema for backwards compatibility.
   */
  fileName: string;
  /** ISO 8601 */
  submittedAt: string;
  status: JobStatus;
  stage: string | null;
  result: ResultsV1 | null;
  error: string | null;
  /**
   * Machine-readable code propagated from the worker via the status endpoint.
   * Drives client-side mapping to generic i18n messages (e.g. "trial_limit_reached"
   * → t("errors.trial_limit_reached")). Null/absent for legacy entries and for
   * non-failed states; optional so older persisted rows remain valid.
   */
  errorCode?: string | null;
  /** ISO 8601 or null */
  completedAt: string | null;
  /**
   * Discriminates between the two job entry modes.
   * Defaults to "file" for legacy entries that pre-date this field.
   * Optional in the type so that old persisted rows (which lack this key) still
   * satisfy the interface; `readJobs` fills in "file" for any missing value.
   */
  inputKind?: "file" | "text";
  /**
   * Trimmed paste text capped at 500 chars. Present only for text-mode jobs.
   * Used as the hover tooltip in the Recent Analyses table.
   * User-supplied; React text-node escaping is the only XSS defense at every render site.
   */
  rawTextPreview?: string;
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
 *
 * Backwards compatibility: rows written before the `inputKind` / `rawTextPreview`
 * fields were added are patched defensively:
 *   - missing `inputKind` → defaults to "file"
 *   - missing `rawTextPreview` → stays undefined
 */
export function readJobs(): StoredJob[] {
  if (typeof window === "undefined") return [];

  const raw = localStorage.getItem(STORAGE_KEY);

  if (raw === null) return [];

  const data = parseStorageData(raw);
  if (data === null) {
    log.warn("localStorage data is corrupted or has an unsupported schema version; returning empty list");
    return [];
  }

  // Patch legacy rows that lack the new fields.
  return data.jobs.map((job) => ({
    ...job,
    inputKind: (job as StoredJob).inputKind ?? "file",
    rawTextPreview: (job as StoredJob).rawTextPreview,
  }));
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
 * Options for addJob — extends the signature without breaking existing callers.
 */
export interface AddJobOptions {
  /** Discriminates the job entry mode. Defaults to "file". */
  inputKind?: "file" | "text";
  /**
   * Trimmed paste preview capped at 500 chars.
   * Only relevant for text-mode jobs; omit for file-mode.
   */
  rawTextPreview?: string;
}

/**
 * Creates a new job with status "queued", prepends it to the stored list,
 * persists the list, and returns the newly created job.
 *
 * The `displayName` parameter is stored as `fileName` for backwards compatibility.
 * The `options.inputKind` and `options.rawTextPreview` fields are persisted into
 * the new columns introduced in the single-reference-text-check feature suite.
 */
export function addJob(
  jobId: string,
  jobToken: string,
  displayName: string,
  options: AddJobOptions = {}
): StoredJob {
  const { inputKind = "file", rawTextPreview } = options;

  const newJob: StoredJob = {
    jobId,
    jobToken,
    fileName: displayName,
    submittedAt: new Date().toISOString(),
    status: "queued",
    stage: null,
    result: null,
    error: null,
    completedAt: null,
    inputKind,
    ...(rawTextPreview !== undefined ? { rawTextPreview } : {}),
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
