# Biblio Checker - Worker

> Part of the [biblio-checker monorepo](../../README.md).

Python worker that will consume Supabase rows and trigger a LangGraph analysis flow. In this first iteration it only provides the project structure and a runnable polling loop stub.

## Tech Stack

- **Python** 3.12.x
- **uv** (package manager)
- **Supabase** (`supabase` Python client)
- **LangGraph** (future flow orchestration)
- **Ruff** (linting & formatting)
- **Pytest** (testing)

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `ENVIRONMENT` | Environment name |
| `LOG_LEVEL` | Logging level |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side) |
| `SUPABASE_TABLE` | Table to poll (default: `analysis_jobs`) |
| `POLL_INTERVAL_SECONDS` | Poll interval seconds (default: `5`) |

## Setup

```bash
cd apps/worker
uv venv --python /usr/bin/python3.12
uv sync
```

## Run (dev)

From repo root:

```bash
pnpm dev:worker
```

Directly:

```bash
cd apps/worker
uv run python -m biblio_checker_worker
```

## Tests / Lint

```bash
pnpm test:worker      # run tests
pnpm lint:worker      # lint (ruff)
pnpm format:worker    # format (ruff)
```
