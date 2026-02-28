# Frontend Guidelines

> Part of the [biblio-checker monorepo](../../AGENTS.md).

## Project Structure & Module Organization

- `app/`: Next.js App Router routes, layouts, and API endpoints (`app/api/**/route.ts`).
- `components/`: Client UI components (generally `"use client"`).
- `services/`: Client-side API service calls (signedUpload, uploadFile, startAnalysis, cleanupUpload).
- `lib/`: Shared utilities and server helpers.
  - `lib/constants.ts`: App-wide constants, enums, error messages.
  - `lib/schemas/`: Zod schemas + inferred TypeScript types (requests, env, results contract).
  - `lib/supabase/`: Supabase admin client (server-only).
  - `lib/file.ts`: File validation/sanitization helpers for uploads.
  - `lib/localStorage/`: localStorage persistence for recent jobs.
  - `lib/time.ts`: Time formatting helpers (relative/elapsed).
  - `lib/server/`: Server-only helpers (e.g., storage cleanup).
- `public/`: Static assets served at `/`.

## Key Flows

- **Signed uploads**: `app/api/signed-upload/route.ts` creates a Supabase Storage signed upload URL and returns `{ signedUrl, filePath }` to the client.
- **Start analysis**: `app/api/analysis-start-gateway/route.ts` downloads the file from Supabase, computes SHA256, and forwards the request to the backend FastAPI service.
- **Cleanup uploads**: `app/api/cleanup-upload/route.ts` deletes uploaded files from Supabase Storage.

## Results Contract v1 (`result` payload)

The analysis success payload returned as `result` is governed by **Results Contract v1**.

- Source of truth (as implemented):
  - Backend model: `apps/backend/app/schemas/results.py`
  - Frontend schema + parser (types derived): `apps/frontend/lib/schemas/resultsV1.ts`
- Coherence rule (normative): any change to the `result` contract MUST update both `apps/backend/app/schemas/results.py` and `apps/frontend/lib/schemas/resultsV1.ts` in the same change set.
- Runtime validation is REQUIRED before treating network data as `ResultsV1`:
  - Zod schema + parser: `apps/frontend/lib/schemas/resultsV1.ts`
  - Polling integration (parses `data.result`): `apps/frontend/hooks/useRecentAnalysesPolling.ts`
- Rendering MUST degrade gracefully:
  - If `result` is present but invalid/unsupported, the UI must show an “unsupported/invalid results format” message and a best-effort raw JSON view.

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
