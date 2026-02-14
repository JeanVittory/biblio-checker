# Repository Guidelines

## Monorepo Structure

- `apps/frontend/`: Next.js web application (see [apps/frontend/AGENTS.md](./apps/frontend/AGENTS.md))
- `apps/backend/`: (planned) Backend service
- `packages/`: (future) Shared libraries

## Build Commands (from root)

- `pnpm install`: Install all workspace dependencies
- `pnpm dev`: Start frontend dev server
- `pnpm build`: Build all apps
- `pnpm lint`: Lint all apps

## Workspace Commands

- `pnpm --filter frontend <cmd>`: Run command in the frontend workspace
- `pnpm --filter backend <cmd>`: Run command in the backend workspace (future)

## Commit & Pull Request Guidelines

- Commit style: short, imperative messages using Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`)
- PRs should include: summary, rationale, steps to test, and UI screenshots when applicable
