# Frontend Guidelines

> Part of the [biblio-checker monorepo](../../AGENTS.md).

## Project Structure & Module Organization

- `app/`: Next.js App Router routes, layouts, and API endpoints (`app/api/**/route.ts`).
- `components/`: Client UI components (generally `"use client"`).
- `services/`: Client-side API service calls (signedUpload, uploadFile, verifyAuthenticity, cleanupUpload).
- `lib/`: Shared utilities and server helpers.
  - `lib/constants.ts`: App-wide constants, enums, error messages.
  - `lib/supabaseAdmin.ts`: Supabase admin client (server-only).
  - `lib/utils.ts`: File validation, sanitization, formatting helpers.
  - `lib/validation/`: Zod schemas for request validation (bibliographyCheck, signUploadURL, cleanupUpload, env).
  - `lib/server/`: Server-only helpers (e.g., storage cleanup).
- `types/`: Shared TypeScript types for API payloads/responses.
- `public/`: Static assets served at `/`.

## Key Flows

- **Signed uploads**: `app/api/signed-upload/route.ts` creates a Supabase Storage signed upload URL and returns `{ signedUrl, filePath }` to the client.
- **Verify authenticity**: `app/api/verify-authenticity-gateway/route.ts` downloads the file from Supabase, computes SHA256, and forwards the verification request to the backend FastAPI service.
- **Cleanup uploads**: `app/api/cleanup-upload/route.ts` deletes uploaded files from Supabase Storage.

## Build, Test, and Development Commands

Use `pnpm` from the repo root or this directory:

- From repo root:
  - `pnpm dev:frontend`: Run the app locally in development mode.
  - `pnpm build:frontend`: Production build.
  - `pnpm lint:frontend`: Run ESLint checks.
  - `pnpm --filter frontend exec tsc --noEmit`: Typecheck without emitting files.
- From `apps/frontend/`:
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
- Minimum verification for changes (from repo root): `pnpm lint:frontend` + `pnpm --filter frontend exec tsc --noEmit`, and a quick manual run via `pnpm dev:frontend`.

## Security & Configuration Tips

- Keep `SUPABASE_SERVICE_ROLE_KEY` server-only; never expose it to client components.
- `BIBLIO_BACKEND_CHECK_URL` is used server-side in the gateway route to reach the FastAPI backend.
- Use `.env.local` (see `.env.local.example`) for local config; do not commit secrets.
