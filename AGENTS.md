# Repository Guidelines

## Repo Hygiene (Do Not Read Generated Artifacts)

Agents MUST NOT read, search, or index generated dependency/build directories:

- `**/node_modules/**`
- `**/.next/**`

When searching the repo (e.g., with ripgrep), exclude them (unless your tool already ignores them), for example:

- `rg <pattern> --glob '!**/node_modules/**' --glob '!**/.next/**'`

## Document Hierarchy (Read Order)

Agents MUST follow this order of reference when making decisions:

1. docs/PRODUCT_VISION.md → Strategic direction (why the product exists)
2. docs/spec/SYSTEM_SPEC.md → System behavior and contracts (how it must behave)
3. spec/ → Spec-Driven Development (SDD) feature suites (functional requirements)
4. apps/*/AGENTS.md → Implementation rules (how to build it)
5. Source code → Current implementation details

## Current Project State (as of 2026-03-02)

- Monorepo for Biblio Checker: Next.js frontend, FastAPI backend, and a Python worker.
- System flow (intended): UI → signed upload to storage → gateway forwards start request → backend validates + creates job row → UI polls job status → worker processes job.
- Current behavior: the worker exists as a polling-loop stub and may not advance jobs beyond creation (jobs are created as `status="queued"` and `stage="created"`).

## Monorepo Structure

- `apps/frontend/`: Next.js web application (see [apps/frontend/AGENTS.md](./apps/frontend/AGENTS.md))
- `apps/backend/`: FastAPI service for bibliography verification (see [apps/backend/AGENTS.md](./apps/backend/AGENTS.md))
- `apps/worker/`: Python worker (polling-loop stub; future job processing) (see [apps/worker/AGENTS.md](./apps/worker/AGENTS.md))
- `spec/`: Spec-Driven Development feature suites (functional requirements)
- `packages/`: (future) Shared libraries

## Build Commands (from root)

- `pnpm install`: Install all workspace dependencies
- `pnpm dev:frontend`: Start frontend dev server
- `pnpm build:frontend`: Build frontend for production
- `pnpm lint:frontend`: Lint frontend (ESLint)
- `pnpm dev:backend`: Start backend dev server (FastAPI)
- `pnpm test:backend`: Run backend tests (pytest)
- `pnpm lint:backend`: Lint backend (ruff)
- `pnpm format:backend`: Format backend (ruff)
- `pnpm dev:worker`: Start worker (polling loop)
- `pnpm test:worker`: Run worker tests (pytest)
- `pnpm lint:worker`: Lint worker (ruff)
- `pnpm format:worker`: Format worker (ruff)

## Workspace Commands

- `pnpm --filter frontend <cmd>`: Run command in the frontend workspace
- `pnpm --filter backend <cmd>`: Run command in the backend workspace
- `pnpm --filter worker <cmd>`: Run command in the worker workspace

## Commit & Pull Request Guidelines

- Commit style: short, imperative messages using Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`)
- PRs should include: summary, rationale, steps to test, and UI screenshots when applicable
