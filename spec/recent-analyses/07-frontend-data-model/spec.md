# Step 07 — Frontend Data Model and localStorage

## Scope

This step defines the data structures used by the frontend to represent jobs and their state. It covers:
- TypeScript types and interfaces for stored jobs
- Structure of data persisted in localStorage
- localStorage key names and naming conventions
- Data transformation between backend responses and frontend state
- localStorage helper functions (read, write, add, update, remove operations)

This step does NOT cover:
- React component state management or hooks (see Step 08 — Frontend Polling)
- UI rendering logic (see Step 10 — Frontend UI)
- Network request details (see Step 09 — Frontend Proxy Route)
- Browser API internals or polyfills
- Data migration strategies for schema changes

## Context

The Recent Analyses feature relies on browser localStorage to persist job data across page refreshes. The frontend must manage this data reliably: reading it on page load, updating it when status queries return, and writing it back after each change.

The data model bridges the backend response format (Step 05) and the frontend UI needs (Step 10). It must be robust, versioned, and handle edge cases like corrupted data or missing fields.

## Requirements

1. A **StoredJob** type must be defined representing a single job in localStorage with:
   - `jobId`: The unique job identifier (required, non-empty string)
   - `jobToken`: The secret token for status queries (required, non-empty string)
   - `fileName`: The original uploaded file name (required, non-empty string)
   - `submittedAt`: ISO 8601 timestamp of submission (required)
   - `status`: Current job status (required, one of: `queued`, `running`, `succeeded`, `failed`, `expired`)
   - `stage`: Current processing stage or null (optional, string or null)
   - `result`: Job result data or null (optional, depends on backend structure)
   - `error`: Error message or null (optional, string or null)
   - `completedAt`: ISO 8601 timestamp of completion or null (optional)

2. A **LocalStorageData** type must represent the entire stored state:
   - `version`: Schema version number (e.g., 1) for forward compatibility
   - `jobs`: An array of StoredJob objects
   - `lastUpdated`: Timestamp of last write to localStorage

3. localStorage must use a single key (e.g., "recentAnalyses" or "biblio-checker:recent-analyses") to store all Recent Analyses data as a JSON string.

4. On application load (page refresh), the frontend must:
   - Attempt to read and parse the localStorage entry
   - Validate the schema version matches the current version
   - If data is missing or corrupted, initialize an empty job list and log a warning
   - Return the list of jobs (or empty array on failure)

5. When adding a new job to the list:
   - Accept jobId, jobToken, and fileName (from upload response)
   - Create a new StoredJob with initial status `queued` and current timestamp
   - Prepend the job to the array (newest first)
   - Write the updated list back to localStorage
   - Handle localStorage quota errors gracefully (Step 06 — Error Definitions)

6. When updating an existing job (from status query response):
   - Match the job by jobId
   - Update `status`, `stage`, `result`, `error`, and `completedAt` as provided
   - Keep `jobId`, `jobToken`, `fileName`, and `submittedAt` unchanged
   - Write the updated list back to localStorage
   - If job is not found, do nothing (no error thrown)

7. When removing a job (user deletes a row):
   - Match the job by jobId
   - Remove it from the array
   - Write the updated list back to localStorage
   - If job is not found, do nothing (no error thrown)

8. localStorage operations must be synchronous and complete before returning to the caller (no async/await needed unless using an async storage wrapper).

9. All timestamps in the data model must be ISO 8601 strings (RFC 3339 format) for consistency and portability.

10. Sensitive data (job token) must not be exposed in logs, error messages, or debugging output. The token is stored in localStorage but never sent to analytics or external services.

## Data Model Details

### StoredJob Type

```
StoredJob {
  jobId: string                    // Non-empty, unique per session
  jobToken: string                 // Secret token, never exposed
  fileName: string                 // Original file name (for display)
  submittedAt: string             // ISO 8601 timestamp
  status: JobStatus               // See enum below
  stage: string | null            // e.g., "parsing", "validation", or null
  result: unknown | null          // Backend-specific result payload or null
  error: string | null            // Error message or null
  completedAt: string | null      // ISO 8601 timestamp or null
}

enum JobStatus {
  Queued = "queued"
  Running = "running"
  Succeeded = "succeeded"
  Failed = "failed"
  Expired = "expired"
}
```

### LocalStorageData Type

```
LocalStorageData {
  version: number                 // Currently 1; increment on schema changes
  jobs: StoredJob[]              // Array of jobs, newest first
  lastUpdated: string            // ISO 8601 timestamp of last write
}
```

### localStorage Key

- **Key Name:** `biblio-checker:recent-analyses` (or similar with namespace)
- **Format:** JSON string
- **Example:**
  ```
  {
    "version": 1,
    "jobs": [
      {
        "jobId": "job-abc123",
        "jobToken": "token-xyz789",
        "fileName": "thesis.pdf",
        "submittedAt": "2025-02-22T14:30:00Z",
        "status": "running",
        "stage": "validation",
        "result": null,
        "error": null,
        "completedAt": null
      }
    ],
    "lastUpdated": "2025-02-22T14:30:05Z"
  }
  ```

## localStorage Helper Functions

The frontend must provide helper functions for safe, consistent data access:

### Function: `readJobs(): StoredJob[]`
- Reads localStorage and parses the JSON
- Returns an array of jobs (empty array if data missing or invalid)
- Logs a warning if data is corrupted
- Does not throw; fails gracefully

### Function: `writeJobs(jobs: StoredJob[]): void`
- Serializes jobs to JSON and writes to localStorage
- Updates the `lastUpdated` timestamp
- Throws an error if localStorage quota is exceeded (Step 06)
- Logs warnings if serialization fails (should not happen with valid data)

### Function: `addJob(jobId: string, jobToken: string, fileName: string): StoredJob`
- Creates a new StoredJob with the provided values
- Sets status to `queued`, submittedAt to current time
- Prepends to the job list
- Calls `writeJobs` to persist
- Returns the created StoredJob for use by caller
- Throws if localStorage quota is exceeded

### Function: `updateJob(jobId: string, updates: Partial<StoredJob>): void`
- Finds the job by jobId
- Merges the provided updates into the job
- Calls `writeJobs` to persist
- Does nothing if job is not found (no error)
- Protects against overwriting jobId, jobToken, fileName, submittedAt

### Function: `removeJob(jobId: string): void`
- Finds and removes the job by jobId
- Calls `writeJobs` to persist
- Does nothing if job is not found (no error)

### Function: `getJob(jobId: string): StoredJob | undefined`
- Returns the job with the given jobId, or undefined if not found
- Does not modify state

## Acceptance Criteria

- localStorage is read successfully on page load and an empty array is returned if data is missing
- A new job can be added with `addJob()` and is immediately visible in localStorage
- An existing job can be updated with `updateJob()` without losing unrelated fields
- A job can be removed with `removeJob()` and is no longer present in localStorage
- localStorage quota errors are caught and reported (Step 06 — Error Definitions)
- Corrupted localStorage data does not crash the application; a warning is logged
- All timestamps are in ISO 8601 format
- Job status values match the enum (queued, running, succeeded, failed, expired)
- Jobs are stored in newest-first order (most recent submission at top)
- The schema version field allows future migrations without breaking the app

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| localStorage is empty on first load | Empty job array is returned; no error thrown |
| localStorage contains data with old schema version | Data is treated as invalid; user starts with empty list |
| A job object is missing required fields | Field is treated as null or undefined; UI handles gracefully |
| Job token is accidentally logged | Should be avoided; code review process can check for this |
| User clears browser data (including localStorage) | Recent Analyses table becomes empty on next page load |
| Job result payload is very large (MB-scale) | Stored and updated normally; potential performance impact (see Step 08) |
| Two jobs have the same jobId (impossible in practice) | updateJob() updates the first match; uniqueness by jobId is assumed |
| Timestamps have timezone information | Stored as-is in ISO 8601 format; consistent handling across frontend |

## Performance Considerations

- Assume < 50 jobs per session (no pagination needed)
- localStorage is synchronous; each write blocks the UI thread
- For performance, consider batching updates if multiple jobs are modified at once
- Large result payloads (MB-scale) should be handled carefully to avoid UI lag

## Dependencies

- Depends on Step 05 (Job Status Endpoint) for the response format that gets stored
- Depends on Step 04 (Job Creation Endpoint) for the response format that initializes a StoredJob
- Informs Step 08 (Frontend Polling) about how jobs are fetched and updated
- Informs Step 10 (Frontend UI) about the data available for rendering
