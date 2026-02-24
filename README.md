# Biblio Checker

Monorepo for the Biblio Checker application — a tool for verifying the authenticity of bibliographic references in academic documents.

## Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Zod 4
- **Backend**: FastAPI, Pydantic, Uvicorn, Ruff
- **Storage**: Supabase
- **Monorepo**: pnpm workspaces

## Structure

```
apps/
  frontend/   - Next.js web application
  backend/    - FastAPI service (Python)
  worker/     - Python worker 
```

## Documentation & Specs

Read order (source of truth):

1. `docs/PRODUCT_VISION.md` — product intent (why)
2. `docs/spec/SYSTEM_SPEC.md` — system behavior + contracts (what)
3. `spec/` — Spec-Driven Development (SDD) feature suites (functional requirements)
4. `apps/*/README.md` and `apps/*/AGENTS.md` — implementation guidance (how)

Entry points:

- `docs/README.md` — docs index
- `spec/README.md` — SDD/specs index
- `.claude/README.md` — Claude sub-agents for SDD workflow
- `spec/recent-analyses/README.md` — Recent Analyses (queued jobs + polling) spec suite

## Prerequisites

- Node 20+
- pnpm 9+
- Python 3.12+
- uv (Python package manager)

## Getting Started

```bash
pnpm install          # install all workspace dependencies
pnpm dev:frontend     # start the frontend dev server
```

### Backend (FastAPI)

```bash
cd apps/backend
uv venv --python /usr/bin/python3.12
uv sync
```

From repo root:

```bash
pnpm dev:backend
```

## Useful Commands

```bash
pnpm dev:frontend                  # start frontend dev server
pnpm build:frontend                # build frontend for production
pnpm lint:frontend                 # lint frontend
pnpm dev:backend                   # start backend dev server (FastAPI)
pnpm test:backend                  # run backend tests
pnpm lint:backend                  # lint backend (ruff)
pnpm format:backend                # format backend (ruff)
pnpm dev:worker                    # start worker (polling loop stub)
pnpm test:worker                   # run worker tests
pnpm lint:worker                   # lint worker (ruff)
pnpm format:worker                 # format worker (ruff)
pnpm --filter frontend <cmd>      # run any command in frontend workspace
```

## Applications

- **Frontend**: See [apps/frontend/README.md](./apps/frontend/README.md)
- **Backend**: See [apps/backend/README.md](./apps/backend/README.md)
- **Worker**: See [apps/worker/README.md](./apps/worker/README.md)
