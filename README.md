# Biblio Checker

Monorepo for the Biblio Checker application.

## Structure

```
apps/
  frontend/   - Next.js web application
  backend/    - (planned) Bibliography checking service
packages/     - (future) Shared libraries
```

## Prerequisites

- Node 20+
- pnpm 9+

## Getting Started

```bash
pnpm install          # install all workspace dependencies
pnpm dev              # start the frontend dev server
```

## Useful Commands

```bash
pnpm dev:frontend                  # start frontend dev server
pnpm build:frontend                # build frontend for production
pnpm lint:frontend                 # lint frontend
pnpm --filter frontend <cmd>      # run any command in frontend workspace
```

## Applications

- **Frontend**: See [apps/frontend/README.md](./apps/frontend/README.md)
