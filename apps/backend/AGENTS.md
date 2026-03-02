<INSTRUCTIONS>
# Backend Guidelines (FastAPI)

## Repo Hygiene (Do Not Read Generated Artifacts)

Agents MUST NOT read, search, or index generated dependency/build directories within the backend workspace:

- `apps/backend/.venv/**`
- `apps/backend/**/__pycache__/**`
- `apps/backend/.pytest_cache/**`
- `apps/backend/.ruff_cache/**`

When searching, exclude them (unless your tool already ignores them), for example:

- `rg <pattern> apps/backend --glob '!apps/backend/.venv/**' --glob '!apps/backend/**/__pycache__/**' --glob '!apps/backend/.pytest_cache/**' --glob '!apps/backend/.ruff_cache/**'`

## Stack

- Python: 3.12.x (use `/usr/bin/python3.12`)
- Environment/deps: `uv` with a local venv at `apps/backend/.venv`
- Web framework: FastAPI + Uvicorn
- Validation: Pydantic + pydantic-settings
- HTTP client: httpx
- Storage: Supabase Python client (admin/service role)
- Text extraction: pdfminer.six (PDF) + python-docx (DOCX)
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
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`

## Project Layout

- `app/main.py` — FastAPI app factory + CORS middleware + router registration
- `app/core/config.py` — settings loaded from `.env` (see `.env.example`)
- `app/core/problems.py` — Problem+JSON catalog + helpers (`application/problem+json`)
- `app/core/supabase_client.py` — Supabase admin client factory (service role)
- `app/api/router.py` — main API router (prefix: `/api`)
- `app/api/routes/analysis/router.py` — analysis sub-router (prefix: `/analysis`)
- `app/api/controllers/analysis/start.py` — `POST /api/analysis/start`
- `app/api/controllers/analysis/status.py` — `GET /api/analysis/status`
- `app/schemas/analysis.py` — request/response Pydantic models (VerifyAuthenticityRequest, VerifyAuthenticityResponse, DocumentPayload, StoragePayload, IntegrityPayload)
- `app/schemas/analysis_jobs.py` — `AnalysisJobStatus` / `AnalysisJobStage` enums
- `app/schemas/results.py` — Results Contract v1 validation model (`ResultsV1`)
- `app/schemas/errors.py` — error response model
- `app/services/supabase_storage.py` — signed download + streamed bytes download + size limits
- `app/services/integrity.py` — SHA256 computation + verification
- `app/services/analysis_jobs_repo.py` — `analysis_jobs` persistence (create + status lookup)
- `app/services/text_extraction.py` — extract text from PDF/DOCX bytes (sync + async)
- `app/utils/datetime_coercion.py` — normalize DB timestamps to UTC datetimes
- `tests/` — pytest tests

## Endpoint Details

### POST /api/analysis/start

Request validation (enforced by `VerifyAuthenticityRequest` and services):
- sourceType ↔ mimeType consistency
- Storage path contains requestId
- Filename matches path filename
- Bucket is in `ALLOWED_BUCKETS` list
- File extension matches sourceType
- Path security: no traversal (`..`), no absolute paths, no backslashes, no null bytes
- Integrity: SHA256 hash (64 hex characters)
- Storage download and size limits enforced server-side (max bytes).
- Response includes `jobId`, `status="queued"`, and a short-lived `jobToken` (currently 1-hour TTL).

### GET /api/analysis/status

Token-protected job status lookup.

- Query params: `jobId` and `jobToken` are required.
- Enumeration-resistant behavior:
  - Job not found AND invalid/expired token both return the same generic message.
- On success, returns `result` only when `status="succeeded"`.
- Backward compatibility: if stored `results` is missing/legacy/invalid, the endpoint returns `result=null` (and MUST NOT crash or change job status).
- Security: the response MUST NOT include `poll_status_token` or its expiry fields.

## Results Contract v1 (`results` / `result`)

The analysis success payload is governed by **Results Contract v1**.

- Backend source of truth (as implemented): `apps/backend/app/schemas/results.py` (`ResultsV1`).
- API contract: `GET /api/analysis/status` returns `result` only when `status="succeeded"`.
- Backward compatibility: if a stored payload is missing/legacy/invalid, the backend MUST return `result=null` (and MUST NOT crash or change the job status).

## Conventions

- Always run code via `uv run ...` to ensure the venv interpreter is used (avoid relying on `python`/pyenv shims).
- Keep settings in env vars; update `.env.example` when adding new required variables.
- Environment variables (see `app/core/config.py`): `APP_NAME`, `ENVIRONMENT`, `ALLOWED_ORIGINS`, `ALLOWED_BUCKETS`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SIGNED_URL_TTL_SECONDS`, `MAX_FILE_SIZE_BYTES`, `MAX_EXTRACTED_TEXT_CHARS`.
</INSTRUCTIONS>
