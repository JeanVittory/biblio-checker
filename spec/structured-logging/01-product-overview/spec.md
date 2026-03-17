# Step 01 — Product Overview

## Scope

**In scope:**

- Define the goals and non-goals of structured logging across the monorepo
- Establish library choices and rationale
- Define log output formats per environment (development vs production)
- Define log level strategy

**Out of scope:**

- Log aggregation/shipping (Datadog, Loki, CloudWatch, etc.) — infrastructure concern
- Alerting rules based on log patterns
- Admin dashboard for viewing logs
- Performance benchmarking of logging overhead

## Context

Biblio Checker is a monorepo with three apps: a Next.js frontend, a FastAPI backend, and a Python worker. Each app handles a different part of the document verification pipeline:

- **Frontend:** receives user uploads, proxies API calls, polls for job status
- **Backend:** validates uploads, creates analysis jobs, serves job status
- **Worker:** claims jobs, runs the 3-stage pipeline (extract → LangGraph → persist)

### Current State

| App | Current Logging | Problems |
|---|---|---|
| Frontend | 5 raw `console.*` calls with manual `[prefix]` strings | Not structured, not configurable, no log levels in prod |
| Backend | 1 file uses `logging.getLogger(__name__)` | API errors are silently swallowed — no trace at all |
| Worker | 5 files use stdlib `logging` with `basicConfig` | Text format not machine-parseable, no request/job correlation |

### Key Files (Current State)

**Frontend — console.* locations:**
- `apps/frontend/lib/schemas/resultsV1.ts` (line 187) — `console.error`
- `apps/frontend/lib/localStorage/recentAnalyses.ts` (line 91) — `console.warn`
- `apps/frontend/app/page.tsx` (lines 255, 267) — `console.warn`
- `apps/frontend/app/api/jobs/status/route.ts` (line 51) — `console.error`

**Backend — only logging:**
- `apps/backend/app/services/audit_repo.py` — `logging.getLogger(__name__)`

**Worker — logging config:**
- `apps/worker/biblio_checker_worker/main.py` — `_configure_logging()` with `logging.basicConfig`

**Worker — logging usage:**
- `apps/worker/biblio_checker_worker/polling/runner.py` (5 calls)
- `apps/worker/biblio_checker_worker/pipeline/runner.py` (7 calls)
- `apps/worker/biblio_checker_worker/langgraph/flow.py` (1 call)
- `apps/worker/biblio_checker_worker/jobs/audit_repo.py` (2 calls)

## Requirements

### R1 — Structured JSON output in production

All three apps must produce **JSON-formatted logs** to stdout/stderr in production. Each log line must include at minimum: `level`, `timestamp`, `msg`, and any contextual fields (e.g., `module`, `request_id`, `job_id`).

### R2 — Human-readable output in development

In development, all three apps must produce **colored, human-readable** log output. This enables developers to read logs without external tooling.

### R3 — Log level configuration

Each app must support configurable log levels via environment variables:
- Frontend: `debug` in development, `info` in production (inferred from `NODE_ENV`)
- Backend/Worker: configurable via `LOG_LEVEL` env var (default: `INFO`)

### R4 — Output format configuration (Python apps)

Backend and worker must support a `LOG_FORMAT` env var:
- `"console"` — colored dev output (default)
- `"json"` — structured JSON for production

If `LOG_FORMAT` is not set, auto-detect: use `"json"` when `ENVIRONMENT=production`, `"console"` otherwise.

### R5 — Contextual correlation

- **Frontend (server-side):** logs should include a `module` field identifying the source
- **Backend:** logs should include `request_id` (auto-generated per request) and `module` for correlation
- **Worker:** logs should include `job_id` (bound per job processing cycle) for correlation

### R6 — Third-party log quieting

Backend and worker must suppress noisy third-party loggers (httpx, httpcore, supabase) to WARNING level to avoid flooding logs with HTTP client internals.

### R7 — Zero impact on error handling

Logging infrastructure must not change existing error handling behavior. If a log call fails, it must not propagate exceptions to the caller.

## Acceptance Criteria

- [ ] Frontend produces JSON logs on server-side in production, colored output in dev
- [ ] Frontend browser logs delegate to native `console.*` methods
- [ ] Backend produces JSON logs when `LOG_FORMAT=json`, colored console otherwise
- [ ] Worker produces JSON logs when `LOG_FORMAT=json`, colored console otherwise
- [ ] Log level is configurable in all three apps
- [ ] All existing `console.*` calls in frontend are replaced with Pino logger
- [ ] All existing `logging.*` calls in worker are replaced with structlog
- [ ] Backend has logging at all critical points (requests, errors, DB operations)
- [ ] Worker has logging at all pipeline stages
- [ ] No existing tests break
- [ ] All apps pass lint

## Edge Cases

| Scenario | Expected Behavior |
|---|---|
| `LOG_LEVEL` set to invalid value | Fall back to `INFO` |
| `LOG_FORMAT` not set, `ENVIRONMENT` not set | Default to `"console"` (dev-friendly) |
| Pino fails to initialize (e.g., pino-pretty not installed in prod) | Falls back to JSON mode (pino-pretty is devDependency) |
| Browser environment with no `console` object | Pino handles gracefully (no-op) |
| structlog `setup_logging()` called multiple times | Idempotent — clears and re-adds handlers |
