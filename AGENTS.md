# Repository Guidelines

## Document Hierarchy (Read Order)

Agents MUST follow this order of reference when making decisions:

1. PRODUCT_VISION.md → Strategic direction (why the product exists)
2. SYSTEM_SPEC.md → System behavior and contracts (how it must behave)
3. apps/*/AGENTS.md → Implementation rules (how to build it)
4. Source code → Current implementation details

## Monorepo Structure

- `apps/frontend/`: Next.js web application (see [apps/frontend/AGENTS.md](./apps/frontend/AGENTS.md))
- `apps/backend/`: FastAPI service for bibliography verification (see [apps/backend/AGENTS.md](./apps/backend/AGENTS.md))
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

## Workspace Commands

- `pnpm --filter frontend <cmd>`: Run command in the frontend workspace
- `pnpm --filter backend <cmd>`: Run command in the backend workspace

## Commit & Pull Request Guidelines

- Commit style: short, imperative messages using Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`)
- PRs should include: summary, rationale, steps to test, and UI screenshots when applicable
