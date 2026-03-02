# Frontend Guidelines

> Part of the [biblio-checker monorepo](../../AGENTS.md).

## Repo Hygiene (Do Not Read Generated Artifacts)

Agents MUST NOT read, search, or index generated dependency/build directories within the frontend workspace:

- `apps/frontend/node_modules/**`
- `apps/frontend/.next/**`

When searching, exclude them (unless your tool already ignores them), for example:

- `rg <pattern> apps/frontend --glob '!apps/frontend/node_modules/**' --glob '!apps/frontend/.next/**'`

## Project Structure & Module Organization

- `app/`: Next.js App Router routes, layouts, and API endpoints (`app/api/**/route.ts`).
- `components/`: Client UI components (generally `"use client"`).
- `hooks/`: Client hooks (e.g., `hooks/useRecentAnalysesPolling.ts`).
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

- **Signed uploads**: `app/api/signed-upload/route.ts` creates a Supabase Storage signed upload URL and returns `signedUrl`, `bucket`, `path`, `requestId`, and client expiry hints.
- **Start analysis (gateway)**: `app/api/analysis-start-gateway/route.ts` downloads the file from Supabase, computes SHA256, validates the payload, and forwards the request to the backend analysis start endpoint.
- **Cleanup uploads**: `app/api/cleanup-upload/route.ts` deletes uploaded files from Supabase Storage.
- **Job status polling (proxy + hook)**:
  - Proxy route: `GET /api/jobs/status?jobId=<id>&jobToken=<token>` (`app/api/jobs/status/route.ts`) forwards to the backend status endpoint and preserves upstream status codes.
  - Hook: `hooks/useRecentAnalysesPolling.ts` polls every 4 seconds for jobs in `queued`/`running`, stops on `succeeded`/`failed`/`expired`, and marks jobs as `expired` on 401/404.

## Results Contract v1 (`result` payload)

The analysis success payload returned as `result` is governed by **Results Contract v1**.

- Frontend source of truth (as implemented): `apps/frontend/lib/schemas/resultsV1.ts` (Zod schema + `parseResultsV1` parser; types derived).
- Coherence rule (normative): any change to the `result` contract MUST update the frontend schema/parser above and ensure the upstream service returns payloads that validate against it.
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

- Vitest tests exist (e.g., `apps/frontend/lib/schemas/__tests__/resultsV1.test.ts`).
- Minimum verification for changes (from repo root):
  - `pnpm lint:frontend`
  - `pnpm --filter frontend exec tsc --noEmit`
  - `pnpm --filter frontend exec vitest run`
  - Quick manual run via `pnpm dev:frontend`

## Security & Configuration Tips

- Keep `SUPABASE_SERVICE_ROLE_KEY` server-only; never expose it to client components.
- `BIBLIO_BACKEND_CHECK_URL` is used server-side in the gateway route to reach the FastAPI backend.
- `app/api/jobs/status/route.ts` must not expose backend URLs or raw job tokens in logs/error responses.
- Use `.env.local` (see `.env.local.example`) for local config; do not commit secrets.
