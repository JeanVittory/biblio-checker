# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Biblio Checker is an academic bibliographic reference validator that detects fabricated/hallucinated citations by checking them against OpenAlex, SciELO, and arXiv. It's a pnpm monorepo with three apps: a Next.js frontend, a FastAPI backend, and a Python worker.

## Commands

All commands run from repo root. Python apps use **uv** (never raw `python`).

| Task | Command |
|---|---|
| Install JS deps | `pnpm install` |
| Frontend dev | `pnpm dev:frontend` |
| Frontend build | `pnpm build:frontend` |
| Frontend lint | `pnpm lint:frontend` |
| Frontend typecheck | `pnpm --filter frontend exec tsc --noEmit` |
| Frontend tests | `pnpm --filter frontend exec vitest run` |
| Single frontend test | `pnpm --filter frontend exec vitest run path/to/test` |
| Backend dev | `pnpm dev:backend` |
| Backend tests | `pnpm test:backend` |
| Backend lint | `pnpm lint:backend` |
| Backend format | `pnpm format:backend` |
| Worker dev | `pnpm dev:worker` |
| Worker tests | `pnpm test:worker` |
| Worker lint | `pnpm lint:worker` |
| Worker format | `pnpm format:worker` |
| Setup Python env | `cd apps/<backend\|worker> && uv venv --python /usr/bin/python3.12 && uv sync` |

Run a single Python test: `cd apps/backend && uv run pytest tests/path_to_test.py -k test_name`

## Architecture

```
Browser → upload PDF/DOCX to Supabase Storage (signed URL)
       → POST /api/analysis-start-gateway (Next.js API route)
           → downloads file, computes SHA256, forwards to backend
           → POST /api/analysis/start (FastAPI) → creates analysis_jobs row
       → UI polls GET /api/jobs/status (Next.js proxy → FastAPI)

Worker (Python, polls every 5s):
  → atomically claims queued jobs via Postgres RPC (claim_analysis_job)
  → 3-stage pipeline: extract → langgraph (currently stubbed) → persist
  → marks job succeeded/failed
```

### Key Directories

- `apps/frontend/` — Next.js 16, React 19, TypeScript, Tailwind CSS 4, Zod 4. App Router. `@/` path alias.
- `apps/backend/` — FastAPI, Python 3.12, Pydantic. Text extraction via pdfminer.six (PDF) and python-docx (DOCX).
- `apps/worker/` — Python 3.12, LangGraph (stubbed), Supabase client. Polling loop in `polling/runner.py`, pipeline stages in `pipeline/`.
- `supabase/migrations/` — Postgres DDL migrations.
- `docs/` — PRODUCT_VISION.md (why), spec/SYSTEM_SPEC.md (what).
- `spec/` — SDD feature suites (functional requirements).

### Results Contract v1

Two canonical schema definitions that must stay in sync:
- Frontend: `apps/frontend/lib/schemas/resultsV1.ts` (Zod)
- Backend: `apps/backend/app/schemas/results.py` (Pydantic)

Runtime Zod validation is required before treating any result payload as ResultsV1. Invalid results must degrade gracefully (return `result=null`, never crash).

## Document Hierarchy

When making decisions, follow this read order:
1. `docs/PRODUCT_VISION.md` → Strategic direction
2. `docs/spec/SYSTEM_SPEC.md` → System behavior and contracts
3. `spec/` → SDD feature suites
4. `apps/*/AGENTS.md` → Per-app implementation rules
5. Source code

## Conventions

- **Commits**: Conventional Commits — `feat:`, `fix:`, `refactor:`, `docs:`
- **Frontend style**: 2-space indent, double quotes, semicolons, `@/` imports
- **Python style**: Ruff (line-length 88, target py312, select E/F/I/UP). Always use `uv run`.
- **Env vars**: Keep secrets in `.env`; update `.env.example` when adding new vars. `SUPABASE_SERVICE_ROLE_KEY` is server-only.

## Repo Hygiene

Never read, search, or index: `**/node_modules/**`, `**/.next/**`, `**/.venv/**`, `**/__pycache__/**`

## Database

Supabase (PostgreSQL + Storage). Migrations live in `supabase/migrations/`.

Key tables:
- `analysis_jobs` — job lifecycle with separate `poll_status_token` (for client polling) and `worker_lease_token` (for worker claims).
- `job_events` — append-only event log tracking job lifecycle transitions (created, claimed, stage changes, succeeded, failed, requeued).
- `reference_audit_log` — per-reference verification outcomes linked to a job.

Key RPCs:
- `claim_analysis_job` — atomic job claiming for worker exclusivity.
- `cleanup_expired_data(p_retention_days)` — deletes expired rows from `analysis_jobs`, `job_events`, and `reference_audit_log`.
