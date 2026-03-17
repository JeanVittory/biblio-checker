# Step 04 — Python structlog Configuration

## Scope

**In scope:**

- Install `structlog` in both Python apps
- Create a centralized `setup_logging()` function in each app
- Add `log_level` and `log_format` settings where missing
- Update `.env.example` files

**Out of scope:**

- Migrating existing logging calls (Steps 05-08)
- Adding new logging points (Steps 06, 08)
- FastAPI request logging middleware (Step 05)

## Context

Both Python apps need structlog configured to:
1. Process structlog-native loggers (used in application code)
2. Process stdlib `logging` loggers (used by third-party libraries like uvicorn, httpx, supabase-py)

structlog achieves this by configuring both its own processor pipeline and a `ProcessorFormatter` that intercepts stdlib log records. The `contextvars` integration allows binding context (like `request_id` or `job_id`) that automatically appears in all log output within that execution context.

### Existing Configuration

**Backend (`apps/backend/app/core/config.py`):** Has a `Settings` class with pydantic-settings. Currently no `log_level` or `log_format` fields.

**Worker (`apps/worker/biblio_checker_worker/core/config.py`):** Has `log_level: str = "INFO"` already. No `log_format` field. The current `_configure_logging()` in `main.py` uses `logging.basicConfig` with a text format.

## Requirements

### R1 — Package installation

Add `"structlog"` to `dependencies` in both:
- `apps/backend/pyproject.toml`
- `apps/worker/pyproject.toml`

Then run `uv sync` in each app directory.

### R2 — Backend settings

**File:** `apps/backend/app/core/config.py`

Add to the `Settings` class:

```python
log_level: str = "INFO"
log_format: str = "console"
```

These are read from `LOG_LEVEL` and `LOG_FORMAT` env vars respectively (pydantic-settings convention).

### R3 — Worker settings

**File:** `apps/worker/biblio_checker_worker/core/config.py`

Add to the existing `Settings` class (which already has `log_level`):

```python
log_format: str = "console"
```

Read from `LOG_FORMAT` env var.

### R4 — Backend logging module

**File:** `apps/backend/app/core/logging.py` (new file)

```python
import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structlog and stdlib logging for the backend."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    use_json = settings.log_format.lower() == "json" or (
        settings.log_format.lower() != "console"
        and getattr(settings, "environment", "") == "production"
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
```

**Design decisions:**

| Decision | Rationale |
|---|---|
| `merge_contextvars` first in chain | Ensures bound context (request_id, job_id) appears in every log line |
| `foreign_pre_chain` | Applies the same processors to stdlib loggers (uvicorn, httpx) |
| `root.handlers.clear()` | Prevents duplicate handlers if `setup_logging()` is called more than once |
| `sys.stderr` as output | Standard practice — stdout is for app output, stderr for logs |
| Quiet httpx/httpcore | These emit DEBUG/INFO for every HTTP call, flooding logs |

### R5 — Worker logging module

**File:** `apps/worker/biblio_checker_worker/core/logging.py` (new file)

Same pattern as R4, but importing from `biblio_checker_worker.core.config`:

```python
import logging
import sys

import structlog

from biblio_checker_worker.core.config import settings


def setup_logging() -> None:
    """Configure structlog and stdlib logging for the worker."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    use_json = settings.log_format.lower() == "json" or (
        settings.log_format.lower() != "console"
        and getattr(settings, "environment", "") == "production"
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if use_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
```

### R6 — Update `.env.example` files

**`apps/backend/.env.example`** — add:
```
LOG_LEVEL=INFO
LOG_FORMAT=console
```

**`apps/worker/.env.example`** — add:
```
LOG_FORMAT=console
```

(Worker already documents `LOG_LEVEL` if present; verify and add if missing.)

## Acceptance Criteria

- [ ] `structlog` is listed in `apps/backend/pyproject.toml` dependencies
- [ ] `structlog` is listed in `apps/worker/pyproject.toml` dependencies
- [ ] `uv sync` succeeds in both apps
- [ ] `apps/backend/app/core/config.py` has `log_level` and `log_format` settings
- [ ] `apps/worker/biblio_checker_worker/core/config.py` has `log_format` setting
- [ ] `apps/backend/app/core/logging.py` exists with `setup_logging()`
- [ ] `apps/worker/biblio_checker_worker/core/logging.py` exists with `setup_logging()`
- [ ] Both `setup_logging()` functions produce JSON when `log_format="json"`
- [ ] Both `setup_logging()` functions produce colored console output when `log_format="console"`
- [ ] `pnpm lint:backend` passes
- [ ] `pnpm lint:worker` passes
- [ ] `.env.example` files are updated

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `LOG_LEVEL=INVALID` | `getattr(logging, "INVALID", logging.INFO)` falls back to INFO |
| `LOG_FORMAT` not set | Defaults to `"console"` (dev-friendly) |
| `setup_logging()` called twice | Second call clears handlers and re-adds — no duplicate output |
| Third-party lib uses `logging.getLogger("some.lib")` | Intercepted by the root handler formatter — appears as structured output |
| Running in CI (no TTY) | `sys.stderr.isatty()` returns False — `ConsoleRenderer` disables colors |

## Dependencies

- **Step 01** defines the log format and level strategy
- **No dependency on** frontend steps (02-03)
