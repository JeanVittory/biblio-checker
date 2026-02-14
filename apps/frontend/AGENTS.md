# Frontend Guidelines

> Part of the [biblio-checker monorepo](../../AGENTS.md).

## Project Structure & Module Organization

- `app/`: Next.js App Router routes, layouts, and API endpoints (`app/api/**/route.ts`).
- `components/`: Client UI components (generally `"use client"`).
- `lib/`: Shared utilities and server helpers (e.g., Supabase admin client, validation).
- `types/`: Shared TypeScript types for API payloads/responses.
- `public/`: Static assets served at `/`.

Notable flows:
- Signed uploads: `app/api/signed-upload/route.ts` creates a Supabase Storage signed upload URL and returns `{ signedUrl, filePath }` to the client.

## Build, Test, and Development Commands

Use `pnpm` from the repo root or this directory:

- `pnpm dev`: Run the app locally in development mode.
- `pnpm build`: Production build.
- `pnpm start`: Serve the production build.
- `pnpm lint`: Run ESLint checks.
- `pnpm exec tsc --noEmit`: Typecheck without emitting files.

## Coding Style & Naming Conventions

- Language: TypeScript + React (Next.js).
- Formatting: 2-space indentation, double quotes, semicolons (follow existing files).
- Imports: use the `@/` alias (e.g., `@/lib/utils`) instead of relative chains.
- API routes: `app/api/<name>/route.ts` with `export async function POST/GET(...)`.

## Testing Guidelines

- No automated test suite is configured yet.
- Minimum verification for changes: `pnpm lint` + `pnpm exec tsc --noEmit`, and a quick manual run via `pnpm dev`.

## Security & Configuration Tips

- Keep `SUPABASE_SERVICE_ROLE_KEY` server-only; never expose it to client components.
- Use `.env.local` (see `.env.local.example`) for local config; do not commit secrets.
