# Biblio Checker - Backend

> Part of the [biblio-checker monorepo](../../README.md).

FastAPI service for verifying the authenticity of bibliographic references.

## Tech Stack

- **FastAPI** (web framework)
- **Pydantic** (validation & settings)
- **Uvicorn** (ASGI server)
- **Ruff** (linting & formatting)
- **Pytest** (testing)
- **Python** 3.12.x
- **uv** (package manager)

## Project Structure

```
app/
  main.py                                  # App factory, CORS middleware, router registration
  core/
    config.py                              # Settings loaded from .env
  api/
    router.py                              # Main API router (prefix: /api)
    routes/references/
      router.py                            # References sub-router (prefix: /references)
      verify_authenticity.py               # POST /api/references/verify-authenticity
  schemas/
    references.py                          # Request/response models & validation
    errors.py                              # Error response model
tests/
  test_verify_authenticity_validation.py   # Endpoint validation tests
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/references/verify-authenticity` | Verify document authenticity |

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description | Example |
|---|---|---|
| `APP_NAME` | Application name | `Biblio Checker API` |
| `ENVIRONMENT` | Environment type | `development` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000` |
| `ALLOWED_BUCKETS` | Comma-separated allowed storage buckets | `uploads` |
| `SUPABASE_URL` | Supabase project URL | `https://YOUR_PROJECT_REF.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server-side) | `YOUR_SUPABASE_SERVICE_ROLE_KEY` |

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

## Tests / Lint

```bash
pnpm test:backend      # run tests
pnpm lint:backend      # lint (ruff)
pnpm format:backend    # format (ruff)
```
