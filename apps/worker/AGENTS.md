<INSTRUCTIONS>
# Worker Guidelines (Python)

## Repo Hygiene (Do Not Read Generated Artifacts)

Agents MUST NOT read, search, or index generated dependency/build directories within the worker workspace:

- `apps/worker/.venv/**`
- `apps/worker/**/__pycache__/**`
- `apps/worker/.pytest_cache/**`
- `apps/worker/.ruff_cache/**`

When searching, exclude them (unless your tool already ignores them), for example:

- `rg <pattern> apps/worker --glob '!apps/worker/.venv/**' --glob '!apps/worker/**/__pycache__/**' --glob '!apps/worker/.pytest_cache/**' --glob '!apps/worker/.ruff_cache/**'`

## Stack

- Python: 3.12.x (use `/usr/bin/python3.12`)
- Environment/deps: `uv` with a local venv at `apps/worker/.venv`
- Supabase: `supabase` Python client (no manual HTTP / no fetch)
- Orchestration: LangGraph (currently a stubbed flow implementation)
- Lint/format: Ruff
- Tests: Pytest

## Commands

Run from repo root:

- `pnpm dev:worker` — start worker (polling loop)
- `pnpm test:worker` — run tests
- `pnpm lint:worker` — lint
- `pnpm format:worker` — format

Run from `apps/worker/`:

- `uv venv --python /usr/bin/python3.12`
- `uv sync`
- `uv run python -m biblio_checker_worker`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`

## Project Layout

- `biblio_checker_worker/main.py` — entrypoint (logging + boot)
- `biblio_checker_worker/core/config.py` — settings loaded from `.env` (see `.env.example`)
- `biblio_checker_worker/supabase/client.py` — Supabase admin client factory
- `biblio_checker_worker/polling/runner.py` — polling loop (claims one job per poll)
- `biblio_checker_worker/jobs/` — job models, enums, repo (DB access), error types, and audit logging (`audit_events.py`, `audit_repo.py`)
- `biblio_checker_worker/pipeline/` — pipeline runner + shared context + stages
- `biblio_checker_worker/pipeline/stages/extract.py` — download + SHA256 verification
- `biblio_checker_worker/pipeline/stages/run_langgraph.py` — stage wrapper around LangGraph flow
- `biblio_checker_worker/langgraph/flow.py` — LangGraph flow (currently stubbed)
- `biblio_checker_worker/pipeline/stages/persist.py` — persist `result_json` and mark succeeded
- `tests/` — pytest tests

## Key Flows (Worker Runtime)

The worker runs a server-side polling loop and processes one claimed job at a time.

- **Polling loop**: `biblio_checker_worker/polling/runner.py`:
  - Creates a Supabase admin client.
  - Every `poll_interval_seconds`, generates a lease token and calls `repo.claim_one_job(...)` (RPC `claim_analysis_job`) to atomically claim one job.
  - Dispatches claimed jobs into the pipeline via `pipeline/runner.py`.
- **Pipeline stages**: `biblio_checker_worker/pipeline/runner.py` runs:
  1) `extract_stage` — downloads bytes from Supabase Storage and enforces SHA-256 integrity.
  2) `run_langgraph_stage` — invokes the LangGraph flow (`langgraph/flow.py`, currently stubbed) and stores the returned dict on `ctx.result_json`.
  3) `persist_stage` — advances stage then calls `repo.mark_succeeded(..., result_json=ctx.result_json)`.
- **Error handling** (centralized in `pipeline/runner.py`):
  - `TerminalJobError` → mark failed permanently (no requeue).
  - `StageError(transient=True)` → requeue only if attempts remain.
  - Unexpected exceptions → write a generic error detail to DB; requeue if attempts remain.

## Result Persistence (Worker-Owned)

The worker persists the pipeline output dict as `result_json` via `repo.mark_succeeded(...)`.

- Current behavior: the LangGraph flow implementation is stubbed and returns `{}`.
- Security requirements:
  - Results MUST NOT include job tokens, signed URLs, credentials, or secrets.
  - Do not log raw job tokens (tokens are redacted in `AnalysisJob.__repr__`).
  - `error_detail` written to the DB is truncated in `jobs/repo.py` to limit information disclosure.

## Configuration (Environment Variables)

Settings are defined in `biblio_checker_worker/core/config.py` and loaded from `.env`:

- `ENVIRONMENT` (default: `development`)
- `LOG_LEVEL` (default: `INFO`)
- `SUPABASE_URL` (required)
- `SUPABASE_SERVICE_ROLE_KEY` (required; server-side only)
- `SUPABASE_TABLE` (default: `analysis_jobs`)
- `POLL_INTERVAL_SECONDS` (default: `5`)
- `JOB_LEASE_SECONDS` (default: `300`, range: `1..3600`)
- `JOB_TOKEN_BYTES` (default: `32`)

## Testing Guidelines

- Test coverage includes `tests/test_imports.py` (smoke test), `tests/test_audit_repo.py` (audit event insertion), and shared fixtures in `tests/conftest.py`.
- Minimum verification:
  - `pnpm test:worker` (or `uv run pytest`)
  - `pnpm lint:worker` / `pnpm format:worker`
</INSTRUCTIONS>
