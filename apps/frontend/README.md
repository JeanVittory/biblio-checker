# Biblio Checker - Frontend

> Part of the [biblio-checker monorepo](../../README.md).

Next.js web application for verifying the authenticity of bibliographic references.

## Tech Stack

- **Next.js** 16 (App Router)
- **React** 19
- **TypeScript** 5
- **Tailwind CSS** 4
- **Zod** 4 (schema validation)
- **Supabase** (storage)

## Project Structure

```
app/
  page.tsx                              # Main page (single-page app)
  layout.tsx                            # Root layout
  api/
    signed-upload/route.ts              # Create signed upload URL
    analysis-start-gateway/route.ts # Gateway to backend analysis API
    cleanup-upload/route.ts             # Delete uploaded files
components/                             # React UI components
services/                               # Client-side API service calls
lib/
  constants.ts                          # App-wide constants and enums
  supabaseAdmin.ts                      # Supabase admin client (server-only)
  utils.ts                              # Utility functions
  validation/                           # Zod validation schemas
  server/                               # Server-only helpers
types/                                  # TypeScript type definitions
```

## Development

From the repo root:

```bash
pnpm install
pnpm dev:frontend
```

Or from this directory:

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Environment Variables

Copy `.env.local.example` to `.env.local` and fill in:

| Variable                    | Description                  | Example                            |
| --------------------------- | ---------------------------- | ---------------------------------- |
| `SUPABASE_URL`              | Supabase project URL         | `https://your-project.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side service role key |
| `SUPABASE_STORAGE_BUCKET`   | Storage bucket name          | `uploads`                          |
| `BIBLIO_BACKEND_CHECK_URL`  | Backend base URL             | `http://localhost:8000`            |

## Useful Commands

```bash
pnpm lint       # run ESLint
pnpm build      # production build
pnpm start      # serve production build
```

## Recent Analyses (Queued Jobs + Polling)

The frontend tracks recently submitted analysis jobs in browser localStorage and polls the backend for status updates.

**Polling details (concrete):**

- **Proxy endpoint:** `GET /api/jobs/status?jobId=<id>&jobToken=<token>`
- **Upstream target:** backend `GET /api/analysis/status`
- **Interval:** every **4 seconds**
- **Active polling statuses:** `queued`, `running`
- **Terminal statuses:** `succeeded`, `failed` (polling stops automatically)
- **Token invalid/expired:** proxy returns **401/404** → UI marks job as `expired` (frontend-only) and stops polling
- **Transient failures (network/502):** retried on the next interval

**Key files:**

- `apps/frontend/hooks/useRecentAnalysesPolling.ts` — polling lifecycle + localStorage sync
- `apps/frontend/app/api/jobs/status/route.ts` — server-side proxy (with upstream timeout)
- `apps/frontend/components/RecentAnalyses.tsx` — table UI
- `apps/frontend/lib/storage/recentAnalyses.ts` — localStorage schema + helpers
