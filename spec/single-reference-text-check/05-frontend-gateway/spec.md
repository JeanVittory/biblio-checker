# Step 05 — Frontend Gateway

## Scope

This step specifies the Next.js API route that proxies text-mode requests from the browser to the FastAPI backend. It covers:
- Route contract (method, path, request, response)
- Validation
- Locale propagation from cookie
- Error mapping

This step does NOT cover:
- The UI component that calls this route (Step 06)
- The backend endpoint receiving the forwarded request (Step 03)

## Context

The existing route `/api/analysis-start-gateway` (`apps/frontend/app/api/analysis-start-gateway/route.ts`) does heavy work for the file flow: validates the payload, downloads the just-uploaded file from Supabase, computes SHA-256, validates the augmented payload, and forwards to the backend. None of this is needed for text input. The text gateway is a thin proxy: validate body shape, override locale from cookie, forward to backend, return the backend response shape unchanged.

The reason for proxying through Next.js (rather than calling the FastAPI backend directly from the client) is the same as for the existing gateway:
- Keeps the backend URL server-only (`BIBLIO_BACKEND_CHECK_URL`)
- Centralizes locale override (cookie is httpOnly server-side)
- Allows future server-side rate limiting without changing the client

## Requirements

### 1) Route

- **Method:** `POST`
- **Path:** `/api/analysis-text-gateway`
- **File location:** `apps/frontend/app/api/analysis-text-gateway/route.ts`

### 2) Request Body

```
{
  "requestId": string (required, UUID),
  "reference": {
    "rawText": string (required, 20–2000 chars after trim)
  }
}
```

The body shape MUST be defined as a Zod schema in `apps/frontend/lib/schemas/bibliographyCheck.ts`:

```ts
export const textReferenceCheckSchema = z
  .object({
    requestId: z.string().uuid(),
    reference: z.object({
      rawText: z
        .string()
        .trim()
        .min(20)
        .max(2000)
        .regex(/^[^\x00]*$/, "null bytes not allowed"),
    }),
  })
  .strict();

export type TextReferenceCheckPayload = z.infer<typeof textReferenceCheckSchema>;
```

The schema uses `.strict()` so any extraneous client-supplied field (notably an attempted `locale` override) is REJECTED with a 400, never silently dropped. This closes the only locale-tampering vector.

Note: `locale` is NOT part of the client payload. It is added server-side from the cookie.

### 3) Validation

The route MUST:
1. Parse the JSON body
2. Validate against `textReferenceCheckSchema` (Zod `.safeParse`)
3. Return 400 with `{ok: false, success: false, message: "<validation error>"}` on validation failure (no leak of raw error messages)

### 4) Locale Override (Server-Side Source of Truth)

The route MUST read the locale from the cookie used by `next-intl` and run it through the existing `normalizeLocale` helper from `@/i18n/config` — the same helper used by the file gateway. The implementer MUST NOT re-implement locale validation inline (region suffixes like `'es-MX'`, uppercase variants like `'ES'`, and embedded newlines are already handled there). If the cookie is missing or normalizes to an unsupported value, default to `'es'`.

The route MUST NOT trust any locale field present in the client payload (the strict Zod schema rejects extra fields, including any attempted `locale`).

### 5) Forwarding

Build the backend payload by merging:

```
{
  requestId: <from body>,
  reference: { rawText: <trimmed body.reference.rawText> },
  locale: <from cookie or default>
}
```

Inside the gateway route handler, fetch the backend URL directly using `fetch`:

- URL: `${process.env.BIBLIO_BACKEND_CHECK_URL}/api/analysis/start-text`
- Headers:
  - `Content-Type: application/json`
  - `Accept-Language: <locale>` (consistent with file gateway)
- Body: stringified merged payload

### 6) Response Shape

On success (HTTP 200 from backend), the route MUST return:

```
{
  "ok": true,
  "success": true,
  "message": "Analysis started successfully.",
  "requestId": <echoed>,
  "backend": {
    "message": <from backend>,
    "success": <from backend>,
    "jobId": <from backend>,
    "status": <from backend, e.g. "queued">,
    "jobToken": <from backend>
  }
}
```

This shape mirrors `/api/analysis-start-gateway` exactly except for the missing `storage` block (since there is no storage involved). The frontend's tracking code (Step 06) reads `backend.jobId` and `backend.jobToken` and is mode-agnostic.

### 7) Error Mapping

| Backend response | Gateway response | Status |
|------------------|------------------|--------|
| 200 | `{ok: true, success: true, ...}` | 200 |
| 422 (validation) | `{ok: false, success: false, message: "<safe summary>"}` | 400 |
| 500 (DB or other) | `{ok: false, success: false, message: "Internal error"}` | 502 |
| Network failure / timeout (30s) | `{ok: false, success: false, message: "Backend unreachable"}` | 502 |
| 4xx other | `{ok: false, success: false, message: "<from backend>"}` | 400 |

The gateway MUST set a fetch timeout of 30 seconds (consistent with `/api/jobs/status` proxy).

Error response bodies MUST NOT echo `requestId` (or any other client-supplied identifier). Only `{ok, success, message}` is returned on the error path. The success path may continue to return `requestId` (it is needed for client tracking).

### 8) Logging

Use the existing Pino logger pattern (see `/api/analysis-start-gateway/route.ts`). Log:

| Event | Fields |
|-------|--------|
| `text_gateway_request_received` | `requestId`, `text_length` |
| `text_gateway_validation_failed` | `requestId` (if available), `errors` (Zod safe-parse error path summary) |
| `text_gateway_forwarded` | `requestId` |
| `text_gateway_backend_error` | `requestId`, `status`, `code` |

The logger MUST NOT emit `rawText` content.

### 9) No File Cleanup

Unlike the file gateway, this route does NOT need to call `cleanupUploadService` on failure. There is no Supabase Storage object to clean up.

### 10) CSRF / Same-Origin

The route inherits the same CSRF posture as the file gateway. No additional CSRF token is required (Next.js App Router, same-origin POST). If the file gateway adds custom origin checks in the future, this route MUST mirror them.

## Acceptance Criteria

- `POST /api/analysis-text-gateway` with valid body returns 200 and the response shape described in § 6
- The forwarded backend payload contains `locale` derived from the cookie (NOT the client body)
- A request with `rawText` of 19 chars returns 400
- A request with `rawText` of 2001 chars returns 400
- A request without `requestId` returns 400
- A request with extraneous fields (e.g., `locale` in body) is REJECTED with HTTP 400 by the strict Zod schema (`.strict()`); extra fields are NEVER silently dropped
- Backend 422 maps to gateway 400 with a safe message (no leak of internal error details)
- Backend timeout (>30s) maps to gateway 502
- Logs do not contain `rawText` content

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| `NEXT_LOCALE` cookie is `'fr'` (unsupported) | Default to `'es'`; do not error |
| `NEXT_LOCALE` cookie missing | Default to `'es'` |
| `NEXT_LOCALE` cookie is `'es-MX'` | Default to `'es'` (no region suffix support) |
| Client sends `locale` in body | Either Zod rejects (`.strict()`) OR field is ignored; never forwarded |
| Backend URL env var is missing | Return 500; log; do not crash the route |
| Same `requestId` reused twice | Forward both; backend creates two distinct jobs (no dedup) |

## Integration Points

- Step 03 (Backend Text Endpoint) — recipient of forwarded requests
- Step 06 (Input Component) — caller of this gateway from the browser via the `startTextAnalysisGateway` service
- `apps/frontend/lib/schemas/bibliographyCheck.ts` — extend with `textReferenceCheckSchema`
- `apps/frontend/services/startTextAnalysisGateway.ts` — new client-side service (parallel to `startAnalysisGateway.ts`)
- Existing `/api/analysis-start-gateway/route.ts` — sibling; same logger and locale-cookie helper

## Dependencies

- Step 03 (Backend Text Endpoint)
