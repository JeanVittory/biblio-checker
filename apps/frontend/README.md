# Biblio Checker - Frontend

> Part of the [biblio-checker monorepo](../../README.md).

Next.js web application for the Biblio Checker project.

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

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only)
- `SUPABASE_STORAGE_BUCKET`
- `BIBLIO_BACKEND_CHECK_URL`

## Useful Commands

```bash
pnpm lint       # run ESLint
pnpm build      # production build
pnpm start      # serve production build
```

## Deploy

Ready for deployment on [Vercel](https://vercel.com). Set the root directory to `apps/frontend`.
