# Step 03 — Job Domain Layer

## Scope

- Define Python enum types mirroring the DB CHECK constraints (`JobStatus`, `JobStage`)
- Define typed error classes following the project's frozen-dataclass convention
- Define the `AnalysisJob` data model as a typed representation of a DB row
- Define new settings fields in the worker configuration

**Out of scope:** Repository functions that perform DB operations (see Step 04). Pipeline logic (see Step 05).

## Context

The worker currently has no typed representation of analysis jobs. The existing backend uses `StrEnum` for status/stage values and frozen dataclass exceptions for error handling (see `apps/backend/app/services/analysis_jobs_repo.py`). The worker must define its own local copies of these types (no cross-app imports between `apps/backend` and `apps/worker`).

### Existing patterns to follow

The backend's error pattern at `apps/backend/app/services/analysis_jobs_repo.py`:

```
@dataclass(frozen=True)
class AnalysisJobsRepoError(Exception):
    code: str
    detail: str | None = None
```

The worker's existing error at `apps/worker/biblio_checker_worker/supabase/client.py`:

```
@dataclass(frozen=True)
class SupabaseClientError(Exception):
    code: str
    detail: str | None = None
```

Both follow the same frozen-dataclass-with-code-and-detail pattern. All new error types MUST follow this convention.

## Requirements

### 1. Enums — `jobs/enums.py`

**File:** `apps/worker/biblio_checker_worker/jobs/enums.py`

Two `StrEnum` classes mirroring the database CHECK constraints exactly:

**JobStatus** — four members:

| Member | Value | Description |
|--------|-------|-------------|
| `QUEUED` | `"queued"` | Waiting to be claimed |
| `RUNNING` | `"running"` | Being processed by a worker |
| `SUCCEEDED` | `"succeeded"` | Completed successfully |
| `FAILED` | `"failed"` | Permanently failed |

**JobStage** — six members:

| Member | Value | Description |
|--------|-------|-------------|
| `CREATED` | `"created"` | Initial state after claim |
| `EXTRACT_DONE` | `"extract_done"` | File downloaded and verified |
| `LANGGRAPH_RUNNING` | `"langgraph_running"` | Graph orchestration active |
| `VERIFYING_REFERENCES` | `"verifying_references"` | API calls in progress |
| `PERSISTING_RESULT` | `"persisting_result"` | Writing result to DB |
| `DONE` | `"done"` | Processing complete |

Both enums use `enum.StrEnum` from the standard library (Python 3.12).

### 2. Error Types — `jobs/errors.py`

**File:** `apps/worker/biblio_checker_worker/jobs/errors.py`

Three frozen dataclass exception types:

**JobRepoError** — raised by repository functions (Step 04) when a DB operation fails:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | (required) | Stable error code (e.g., `"claim_failed"`, `"stage_update_failed"`) |
| `detail` | `str or None` | `None` | Human-readable detail message |

**StageError** — raised by pipeline stages (Steps 06–08) when a processing step fails:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | (required) | Stable error code (e.g., `"storage_download_failed"`, `"langgraph_flow_failed"`) |
| `detail` | `str or None` | `None` | Human-readable detail message |
| `transient` | `bool` | `True` | If `True`, the error is retryable. If `False`, the job should fail permanently. |

**TerminalJobError** — raised when a job must fail permanently regardless of remaining attempts:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `code` | `str` | (required) | Stable error code (e.g., `"integrity_sha_mismatch"`) |
| `detail` | `str or None` | `None` | Human-readable detail message |

All three MUST be frozen dataclasses that inherit from `Exception`. The `@dataclass(frozen=True)` decorator is required.

### 3. Job Model — `jobs/models.py`

**File:** `apps/worker/biblio_checker_worker/jobs/models.py`

A frozen dataclass `AnalysisJob` that provides a typed view of a row from the `analysis_jobs` table:

| Field | Type | Maps to column |
|-------|------|----------------|
| `id` | `str` | `id` (UUID as string) |
| `status` | `str` | `status` |
| `stage` | `str` | `stage` |
| `bucket` | `str` | `bucket` |
| `path` | `str` | `path` |
| `sha256` | `str` | `sha256` |
| `source_type` | `str` | `source_type` |
| `attempts` | `int` | `attempts` |
| `max_attempts` | `int` | `max_attempts` |
| `job_token` | `str or None` | `job_token` |
| `token_expires_at` | `str or None` | `token_expires_at` (ISO 8601 string as returned by Supabase) |
| `created_at` | `str or None` | `created_at` |
| `updated_at` | `str or None` | `updated_at` |

The model MUST include a `from_row(row: dict) -> AnalysisJob` classmethod that:
1. Accepts a raw dict as returned by the Supabase client (`resp.data[0]`)
2. Maps dict keys to dataclass fields
3. Preserves timestamp values as ISO 8601 strings (no datetime parsing needed for v1)

The model is frozen (immutable). Pipeline code reads fields but never modifies the job model directly; DB updates go through the repository layer.

### 4. Configuration — `core/config.py`

**File:** `apps/worker/biblio_checker_worker/core/config.py` (modify existing)

Two new settings fields added to the existing `Settings` class:

| Field | Type | Default | Env var | Description |
|-------|------|---------|---------|-------------|
| `job_lease_seconds` | `int` | `300` | `JOB_LEASE_SECONDS` | How long (in seconds) a worker holds the lease on a claimed job |
| `job_token_bytes` | `int` | `32` | `JOB_TOKEN_BYTES` | Number of random bytes for token generation via `secrets.token_urlsafe()` |

These are appended to the existing settings. No existing fields are modified.

### 5. Package Init — `jobs/__init__.py`

**File:** `apps/worker/biblio_checker_worker/jobs/__init__.py`

Empty `__init__.py` file to make `jobs` a Python package. No re-exports needed.

## Acceptance Criteria

- `JobStatus` has exactly 4 members with values matching the DB CHECK constraint
- `JobStage` has exactly 6 members with values matching the DB CHECK constraint
- All three error types are frozen dataclasses inheriting from `Exception`
- `StageError` has a `transient` field defaulting to `True`
- `TerminalJobError` has no `transient` field (it is always terminal)
- `AnalysisJob.from_row()` correctly maps a Supabase response dict to a typed dataclass
- `AnalysisJob` is frozen (immutable)
- `settings.job_lease_seconds` defaults to 300
- `settings.job_token_bytes` defaults to 32
- All new modules import cleanly (`python -c "from biblio_checker_worker.jobs.enums import JobStatus"`)
- The existing `SupabaseClientError` in `supabase/client.py` is not modified

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `from_row()` receives a dict missing the `job_token` key | Field defaults to `None` (nullable field) |
| `from_row()` receives a dict with extra keys not in the model | Extra keys are ignored |
| `from_row()` receives a dict missing a required key (e.g., `id`) | Raises `KeyError` or `TypeError` — the caller (repo layer) handles this |
| Enum comparison with raw string: `JobStatus.QUEUED == "queued"` | Returns `True` (StrEnum supports string comparison) |

## Integration Points

- **Step 01:** Enum values match the state machine definition exactly
- **Step 04:** Repository functions use `AnalysisJob.from_row()` and raise `JobRepoError`
- **Step 05:** Pipeline runner catches `StageError` and `TerminalJobError`
- **Steps 06–08:** Stages raise `StageError` or `TerminalJobError`
- **Step 09:** Polling loop reads `settings.job_lease_seconds` and `settings.job_token_bytes`

## Dependencies

- **Depends on:** Step 01 (enum values must match the state machine)
- **Informs:** Step 04 (repo uses these types), Step 05 (pipeline catches these errors), Steps 06–08 (stages raise these errors)
