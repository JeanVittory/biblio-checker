# Step 05 — Backend Logging Infrastructure

## Scope

**In scope:**

- Wire `setup_logging()` into the FastAPI app startup
- Create request logging middleware with `request_id` correlation
- Migrate the single existing `logging` call in `audit_repo.py` to structlog

**Out of scope:**

- Adding logging to files that currently have none (Step 06)
- Worker changes (Steps 07-08)

## Context

The backend currently has:
- **No logging setup** in `app/main.py`
- **One file** using stdlib logging: `app/services/audit_repo.py` with `logging.getLogger(__name__)`
- **No request correlation** — when multiple concurrent requests hit the API, their logs are interleaved with no way to group them

The FastAPI app is created in `app/main.py` via a `create_app()` function. CORS middleware is already registered there. The request logging middleware will be added alongside it.

### Existing Patterns

The backend uses `anyio.to_thread.run_sync` for async wrapping of synchronous Supabase calls. The middleware should be a standard Starlette `BaseHTTPMiddleware` or pure ASGI middleware.

## Requirements

### R1 — Wire `setup_logging()` in `app/main.py`

Call `setup_logging()` at the very beginning of `create_app()`, before any other initialization:

```python
from app.core.logging import setup_logging

def create_app() -> FastAPI:
    setup_logging()
    # ... existing code ...
```

Add a startup log after the app is configured:

```python
import structlog

logger = structlog.stdlib.get_logger("biblio_checker_backend")

def create_app() -> FastAPI:
    setup_logging()
    # ... existing app setup ...
    logger.info("app_started", environment=settings.environment)
    return application
```

### R2 — Request logging middleware

**File:** `apps/backend/app/middleware/request_logging.py` (new file)

```python
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.stdlib.get_logger("biblio_checker_backend.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            http_method=request.method,
            http_path=request.url.path,
        )

        logger.info("request_started")
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed")
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            structlog.contextvars.bind_contextvars(duration_ms=duration_ms)

        log_level = "warning" if response.status_code >= 500 else "info"
        getattr(logger, log_level)(
            "request_finished", status_code=response.status_code
        )

        response.headers["X-Request-ID"] = request_id
        return response
```

**Behavior:**

1. Generate a UUID4 `request_id` for every incoming request
2. Clear contextvars to prevent leaking context from previous requests
3. Bind `request_id`, `http_method`, `http_path` to contextvars — these automatically appear in ALL log calls made during this request (including in service/repo layers)
4. Log `request_started` at INFO
5. Time the request using `time.perf_counter()`
6. On exception: log with `logger.exception` (includes traceback), re-raise
7. Log `request_finished` with `status_code` and `duration_ms` — WARNING for 5xx, INFO otherwise
8. Add `X-Request-ID` response header for client-side correlation

### R3 — Register middleware in `app/main.py`

Register the middleware **after** the CORS middleware. In Starlette, middleware is applied in reverse registration order — the last registered middleware becomes the outermost wrapper. By registering `RequestLoggingMiddleware` after CORS, it wraps the full request lifecycle including CORS handling:

```python
from app.middleware.request_logging import RequestLoggingMiddleware

# existing: application.add_middleware(CORSMiddleware, ...)
application.add_middleware(RequestLoggingMiddleware)
```

If the middleware directory doesn't exist, create `apps/backend/app/middleware/__init__.py` (empty).

### R4 — Migrate `app/services/audit_repo.py`

**Current:**
```python
import logging

logger = logging.getLogger(__name__)

# ... inside insert_job_event:
logger.warning(
    "Failed to insert job event [event_type=%s, job_id=%s]: %s",
    event_type, job_id, exc,
)
```

**New:**
```python
import structlog

logger = structlog.stdlib.get_logger(__name__)

# ... inside insert_job_event:
logger.warning(
    "job_event_insert_failed",
    event_type=event_type,
    job_id=job_id,
    error=str(exc),
)
```

**Changes:**
- Replace `import logging` with `import structlog`
- Replace `logging.getLogger` with `structlog.stdlib.get_logger`
- Replace format-string style with event name + keyword args
- Event name changes from descriptive sentence to snake_case identifier

## Acceptance Criteria

- [ ] `setup_logging()` is called at the start of `create_app()` in `app/main.py`
- [ ] `app_started` log event is emitted on startup
- [ ] `apps/backend/app/middleware/request_logging.py` exists with `RequestLoggingMiddleware`
- [ ] Every request produces `request_started` and `request_finished` log events
- [ ] `request_id` is bound to contextvars and appears in all logs during that request
- [ ] `X-Request-ID` header is present in responses
- [ ] 5xx responses log `request_finished` at WARNING level
- [ ] Unhandled exceptions log `request_failed` with traceback
- [ ] `app/services/audit_repo.py` uses `structlog.stdlib.get_logger` instead of `logging.getLogger`
- [ ] `pnpm lint:backend` passes
- [ ] `pnpm test:backend` passes
- [ ] Existing error handling behavior is unchanged

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Request to health check or non-existent path | Still logged (middleware wraps all requests) |
| Middleware exception in `call_next` | Logged as `request_failed` with traceback, exception re-raised |
| Concurrent async requests | Each has its own contextvars scope (Python contextvars are task-local in asyncio) |
| `audit_repo.py` `insert_job_event` called during a request | `request_id` automatically appears in the audit warning log (via contextvars) |

## Dependencies

- **Step 04** must be implemented first (`setup_logging()` must exist)
- **No dependency on** frontend steps or worker steps
