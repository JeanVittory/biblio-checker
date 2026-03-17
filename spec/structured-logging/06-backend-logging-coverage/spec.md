# Step 06 — Backend Logging Coverage

## Scope

**In scope:**

- Add structlog logging to all backend files that currently have no logging
- Cover API controllers, service layers, and core utilities
- Use structured event names with keyword arguments

**Out of scope:**

- Modifying error handling logic or response codes
- Adding new error types or changing exception hierarchy
- Worker logging (Steps 07-08)

## Context

After Step 05, the backend has structlog infrastructure (config, middleware, audit_repo migration). But most files still have zero logging. API errors are silently swallowed — the `problem_response()` utility returns error responses without any server-side trace.

The `request_id` bound by the middleware (Step 05) will automatically appear in all log calls made during request processing, so service-layer logs inherit request correlation for free.

## Requirements

### R1 — `app/api/controllers/analysis/start.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Handler entry | `analysis_start_requested` | `info` | `bucket`, `path` |
| After job created | `analysis_job_created` | `info` | `job_id` |
| `SupabaseStorageError` catch | `analysis_start_storage_error` | `warning` | `error_code=exc.code`, `error_detail=exc.detail` |
| `AnalysisJobsRepoError` catch | `analysis_start_repo_error` | `warning` | `error_code=exc.code`, `error_detail=exc.detail` |
| `IntegrityShaMismatchError` catch | `analysis_start_sha_mismatch` | `warning` | `error_code=exc.code` |

### R2 — `app/api/controllers/analysis/status.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Handler entry | `job_status_requested` | `info` | `job_id` |
| `AnalysisJobsRepoError` catch | `job_status_repo_error` | `warning` | `job_id`, `error_code` |
| Token mismatch / expired | `job_status_token_invalid` | `warning` | `job_id` |
| Row not found | `job_status_not_found` | `warning` | `job_id` |
| Result validation `except Exception` | `job_status_result_validation_failed` | `warning` | `job_id` |

### R3 — `app/services/analysis_jobs_repo.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Before insert | `analysis_job_inserting` | `info` | — |
| After successful insert | `analysis_job_inserted` | `info` | `job_id` |
| Insert error | `analysis_job_insert_failed` | `error` | `error_code`, `error_detail` |
| Before fetch | `analysis_job_fetching` | `info` | `job_id` |
| After successful fetch | `analysis_job_fetched` | `info` | `job_id`, `status` |
| Fetch error | `analysis_job_fetch_failed` | `error` | `job_id`, `error_code`, `error_detail` |

### R4 — `app/services/supabase_storage.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

| Location | Event | Level | Fields |
|---|---|---|---|
| Signed URL creation start | `storage_signed_url_creating` | `info` | `bucket`, `path` |
| Signed URL created | `storage_signed_url_created` | `info` | — |
| Download start | `storage_download_starting` | `info` | `bucket`, `path` |
| Download complete | `storage_download_complete` | `info` | `size_bytes` |
| Any storage error | `storage_error` | `error` | `error_code`, `error_detail` |

### R5 — `app/services/text_extraction.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging at these points:

The function signature is `extract_text_from_bytes(*, source_type, content, max_chars)`. The async wrapper `extract_text_from_bytes_async` delegates to it. Add logging to the sync function:

| Location | Event | Level | Fields |
|---|---|---|---|
| Extraction start | `text_extraction_starting` | `info` | `source_type=source_type`, `content_bytes=len(content)` |
| Extraction complete | `text_extraction_complete` | `info` | `chars=len(text)` |
| Extraction error (in `except TextExtractionError`) | `text_extraction_failed` | `error` | `error_code=exc.code`, `error_detail=exc.detail` |

### R6 — `app/services/integrity.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging:

| Location | Event | Level | Fields |
|---|---|---|---|
| SHA mismatch detected | `sha_mismatch` | `warning` | `computed=computed_sha[:12]`, `provided=provided_sha[:12]` |

**Security note:** Only log the first 12 characters of SHA hashes to avoid exposing full content fingerprints in logs.

### R7 — `app/core/supabase_client.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging:

| Location | Event | Level | Fields |
|---|---|---|---|
| Client misconfigured | `supabase_client_misconfigured` | `error` | — |

### R8 — `app/core/problems.py`

Add at module level:
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)
```

Add logging:

| Location | Event | Level | Fields |
|---|---|---|---|
| Every `problem_response()` call | `problem_response_sent` | `warning` | `code`, `status` |

This ensures every error response is captured in server logs — critical for production debugging.

## Event Naming Convention

All events follow `snake_case` naming:
- `{domain}_{action}` for normal operations (e.g., `analysis_job_inserted`)
- `{domain}_{action}_{outcome}` for error branches (e.g., `analysis_start_storage_error`)

## Acceptance Criteria

- [ ] All 7 files listed above have `structlog.stdlib.get_logger(__name__)` at module level
- [ ] Every `except` block in API controllers logs the error before returning `problem_response()`
- [ ] Service layer operations log start and completion
- [ ] `problem_response()` logs every invocation
- [ ] SHA hashes are truncated to 12 chars in log output
- [ ] No log call includes sensitive data (passwords, tokens, full file contents)
- [ ] No error handling behavior is changed — only logging is added
- [ ] `pnpm lint:backend` passes
- [ ] `pnpm test:backend` passes

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `logger.info()` raises unexpectedly | Should not happen with structlog, but if it did, the exception would propagate — acceptable since this is infrastructure, not fire-and-forget |
| High request volume | Log volume scales linearly with requests; each request produces 2 middleware logs + N service logs. Consider adjusting log level in production if noisy. |
| `problem_response()` called outside a request context | `request_id` will not be in contextvars — log still works, just without correlation |

## Dependencies

- **Step 05** must be implemented first (structlog wired into app, middleware active)
- **No dependency on** frontend or worker steps
