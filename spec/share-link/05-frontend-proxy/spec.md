# Step 05 — Frontend Proxy

## Scope

This step specifies the Next.js API route that proxies requests from the frontend share page to the backend public read endpoint. It covers:
- Route path and method
- Request forwarding
- Error handling

This step does NOT cover:
- The backend endpoint (see Step 04)
- The share page UI (see Step 06)

## Context

The frontend communicates with the backend through Next.js API routes (server-side), not directly from the browser. This pattern is already established for the status endpoint at `apps/frontend/app/api/jobs/status/route.ts`. The share proxy follows the same pattern.

## Requirements

### 1) Route Path

- **File:** `apps/frontend/app/api/shared/[shareToken]/route.ts`
- **HTTP Method:** `GET`
- **URL Pattern:** `/api/shared/<shareToken>`

### 2) Request Forwarding

The route MUST:
1. Extract `shareToken` from the URL path parameter
2. Validate that `shareToken` is a non-empty string
3. Forward the request to the backend at `GET /api/analysis/shared/{shareToken}`
4. Return the backend response (status code + body) as-is

### 3) Backend URL

The backend URL MUST be read from the `BIBLIO_BACKEND_CHECK_URL` environment variable (same as the existing status proxy at `apps/frontend/app/api/jobs/status/route.ts`). If the variable is not set, use `http://localhost:8000` as the default.

### 4) Timeout

The request to the backend MUST have a timeout of 30 seconds (same as the status proxy).

### 5) Error Handling

- If `shareToken` is empty or missing, return 400 with `{ "error": "missing_share_token" }`
- If `shareToken` exceeds 64 characters, return 400 with `{ "error": "invalid_share_token" }` (never forward to backend — prevents DB amplification)
- If the backend is unreachable, return 502 with `{ "error": "backend_unavailable" }`
- If the backend returns an error (4xx/5xx), forward the status code and body

### 6) Share Token Validation

The proxy MUST validate `shareToken` using Zod: `z.string().min(1).max(64)`. Requests with tokens exceeding 64 characters MUST be rejected locally (400) without forwarding to the backend. `secrets.token_urlsafe(24)` produces exactly 32 characters; 64 provides ample headroom.

### 6) Caching

The proxy response MUST include `Cache-Control: no-store` to prevent caching of share results. Results may change if the share token expires or the job is deleted.

### 7) POST Proxy for Token Generation

In addition to the GET proxy, a POST proxy route MUST be created for share token generation:

- **File:** `apps/frontend/app/api/analysis/share/route.ts`
- **HTTP Method:** `POST`
- **URL Pattern:** `/api/analysis/share`
- **Behavior:** Forward the JSON body (`jobId`, `jobToken`) to the backend at `POST /api/analysis/share`
- **Backend URL:** Read from `BIBLIO_BACKEND_CHECK_URL` (same as other proxies)
- **Timeout:** 30 seconds
- **Error handling:** Same pattern as the GET proxy

This proxy is required because the existing frontend architecture routes ALL backend calls through Next.js API routes (never direct browser-to-backend). The share button (Step 07) calls this proxy, not the backend directly.

## Acceptance Criteria

- `GET /api/shared/<token>` forwards to backend and returns the response
- `shareToken` exceeding 64 chars returns 400 (never forwarded)
- Empty share token returns 400
- Backend timeout returns 502
- Backend 404 is forwarded as 404
- Response includes `Cache-Control: no-store`
- `POST /api/analysis/share` forwards JSON body to backend and returns response

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Backend is down | 502 after 30s timeout |
| shareToken contains special characters | URL-encoded by fetch; backend handles validation |
| Very long shareToken (> 1000 chars) | Forwarded to backend; backend returns 404 |

## Integration Points

- Step 04 (Public Read Endpoint) — proxies to this backend endpoint
- Step 06 (Share Page) — the share page calls this proxy route

## Dependencies

- Step 04 (Public Read Endpoint) — backend endpoint must exist
