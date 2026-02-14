# Backend (FastAPI)

FastAPI service for the Biblio Checker monorepo.

## Requirements

- Python **3.12.x** 
- `uv`

## Setup

```bash
cd apps/backend
uv venv --python /usr/bin/python3.12
uv sync
```

## Run (dev)

From repo root:

```bash
pnpm dev:backend
```

Directly:

```bash
cd apps/backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Tests / lint

```bash
pnpm test:backend
pnpm lint:backend
pnpm format:backend
```

