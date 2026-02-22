<INSTRUCTIONS>
# Worker Guidelines (Python)

## Stack

- Python: 3.12.x (use `/usr/bin/python3.12`)
- Environment/deps: `uv` with a local venv at `apps/worker/.venv`
- Supabase: `supabase` Python client (no manual HTTP / no fetch)
- Orchestration (future): LangGraph
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

## Project Layout

- `biblio_checker_worker/main.py` — entrypoint (logging + boot)
- `biblio_checker_worker/core/config.py` — settings loaded from `.env` (see `.env.example`)
- `biblio_checker_worker/supabase/client.py` — Supabase admin client factory
- `biblio_checker_worker/polling/runner.py` — polling loop (stub)
- `tests/` — pytest tests
</INSTRUCTIONS>
