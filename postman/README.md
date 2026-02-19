# Postman: Supabase upload → verify → cleanup

This repo’s “real” flow is:

1) Next.js creates a Supabase Storage signed upload URL
2) Client uploads the file bytes to Supabase using that signed URL
3) Next.js downloads the file from Supabase, computes SHA256, and forwards the request to the FastAPI backend
4) (optional) Cleanup deletes the uploaded object

The Postman collection in this folder emulates the same flow **without putting Supabase secrets in Postman**.

## Prerequisites (local)

1) Configure env files:
   - `apps/frontend/.env.local` (see `apps/frontend/.env.local.example`)
   - `apps/backend/.env` (see `apps/backend/.env.example`)

2) Start servers:
   - Frontend: `pnpm dev:frontend` (Next.js at `http://localhost:3000`)
   - Backend: `pnpm dev:backend` (FastAPI at `http://127.0.0.1:8000`)

## Import into Postman

1) Import collection: `postman/biblio-checker.postman_collection.json`
2) Import environment: `postman/biblio-checker.local.postman_environment.json`
3) Select the environment **biblio-checker (local)**

## Run the flow (manual in Postman UI)

1) Run **1) Create signed upload URL (Next.js)**
2) Open **2) Upload file to Supabase (PUT signedUrl)**
   - Set **Body** to file/binary and pick your local PDF
   - Ensure headers include `content-type: application/pdf` and `x-upsert: false`
3) Run **3) Verify authenticity (Next.js gateway → FastAPI)**
4) Run **4) Cleanup uploaded file (Next.js)** (recommended)

## Optional: run via Newman (automation)

If you want to run this flow from CLI (CI-like), install Newman and provide a file path:

```bash
npx newman run postman/biblio-checker.postman_collection.json \
  -e postman/biblio-checker.local.postman_environment.json \
  --env-var upload_file_path=/absolute/path/to/sample.pdf \
  --env-var test_file_name=sample.pdf
```

Notes:
- `upload_file_path` must point to the real file on disk.
- `test_file_name` should match the filename portion of the storage path (it’s validated downstream).
