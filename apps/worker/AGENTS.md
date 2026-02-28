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

## Results Contract v1 (persistence contract)

When the worker (future) marks a job as `succeeded` and persists `analysis_jobs.results`, it MUST write a payload that validates as **Results Contract v1**.

- Source of truth (as implemented):
  - Backend validation model: `apps/backend/app/schemas/results.py`
  - Frontend schema + parser (types derived): `apps/frontend/lib/schemas/resultsV1.ts`
- Coherence rule (normative): any change to the `result` contract MUST update backend + frontend sources of truth above in the same change set.
- Security: results MUST NOT include job tokens, signed URLs, or credentials.
</INSTRUCTIONS>
