<INSTRUCTIONS>
# Backend Guidelines (FastAPI)

## Stack

- Python: 3.12.x (use `/usr/bin/python3.12`)
- Environment/deps: `uv` with a local venv at `apps/backend/.venv`
- Web framework: FastAPI + Uvicorn
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

- `app/main.py` — FastAPI app factory + middleware + router registration
- `app/core/config.py` — settings loaded from `.env` (see `.env.example`)
- `app/api/routes/health.py` — `GET /health`
- `tests/` — pytest tests

## Conventions

- Always run code via `uv run ...` to ensure the venv interpreter is used (avoid relying on `python`/pyenv shims).
- Keep settings in env vars; update `.env.example` when adding new required variables.
</INSTRUCTIONS>

