<INSTRUCTIONS>
# Backend Guidelines (FastAPI)

## Stack

- Python: 3.12.x (use `/usr/bin/python3.12`)
- Environment/deps: `uv` with a local venv at `apps/backend/.venv`
- Web framework: FastAPI + Uvicorn
- Validation: Pydantic + pydantic-settings
- Lint/format: Ruff
- Tests: Pytest

## Commands

Run from repo root:

- `pnpm dev:backend` — start dev server (reload) on `127.0.0.1:8000`
- `pnpm test:backend` — run tests
- `pnpm lint:backend` — lint
- `pnpm format:backend` — format

Run from `apps/backend/`:

- `uv venv --python /usr/bin/python3.12`
- `uv sync`
- `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`

## Project Layout

- `app/main.py` — FastAPI app factory + CORS middleware + router registration
- `app/core/config.py` — settings loaded from `.env` (see `.env.example`)
- `app/api/router.py` — main API router (prefix: `/api`)
- `app/api/routes/analysis/router.py` — analysis sub-router (prefix: `/analysis`)
- `app/api/controllers/analysis/start.py` — `POST /api/analysis/start`
- `app/schemas/analysis.py` — request/response Pydantic models (VerifyAuthenticityRequest, VerifyAuthenticityResponse, DocumentPayload, StoragePayload, IntegrityPayload)
- `app/schemas/errors.py` — error response model
- `tests/` — pytest tests

## Endpoint Details

### POST /api/analysis/start

Request validates:
- sourceType ↔ mimeType consistency
- Storage path contains requestId
- Filename matches path filename
- Bucket is in `ALLOWED_BUCKETS` list
- File extension matches sourceType
- Path security: no traversal (`..`), no absolute paths, no backslashes, no null bytes
- Integrity: SHA256 hash (64 hex characters)

## Conventions

- Always run code via `uv run ...` to ensure the venv interpreter is used (avoid relying on `python`/pyenv shims).
- Keep settings in env vars; update `.env.example` when adding new required variables.
- Environment variables: `APP_NAME`, `ENVIRONMENT`, `ALLOWED_ORIGINS`, `ALLOWED_BUCKETS`.
</INSTRUCTIONS>
