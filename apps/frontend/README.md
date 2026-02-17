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
    verify-authenticity-gateway/route.ts # Gateway to backend verification API
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
pnpm dev
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
