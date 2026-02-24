# Step 09 — Frontend Proxy Route

## Scope

This step specifies a Next.js server-side proxy route that forwards status requests from the frontend to the backend API. It covers:
- Route path and HTTP method
- Request parameter handling and validation
- Response forwarding (including status codes)
- Error handling and status code preservation
- Security considerations

This step does NOT cover:
- Next.js routing syntax or framework-specific implementation
- Backend API authentication or secrets management (assumed handled separately)
- Rate limiting or throttling (can be added later)
- Request logging, metrics, or observability details
- Frontend request construction (see Step 08 — Frontend Polling)
- Frontend response parsing (see Step 10 — Frontend UI)

## Context

The backend is kept intentionally hidden from the frontend JavaScript code (only the proxy URL is known). This prevents the backend URL from being exposed in client-side JavaScript (which could be harvested from network traffic or minified code). The proxy route acts as a thin forwarding layer that:
1. Accepts requests from the frontend (via JavaScript fetch)
2. Validates inputs
3. Forwards the request to the backend
4. Preserves HTTP status codes and response body
5. Returns the response to the frontend

## Requirements

1. The proxy route must be a Next.js API route (or app router equivalent) accessible at a fixed path (e.g., `/api/jobs/status`).

2. The route must accept HTTP GET or POST requests (backend team determines; recommend GET for idempotency).

3. The route must accept two parameters:
   - `jobId`: The unique job identifier
   - `jobToken`: The secret token for authorization

   These can be passed as query parameters (GET) or in the request body (POST); frontend and backend must agree on the convention.

4. The route must validate inputs before forwarding:
   - Both `jobId` and `jobToken` must be present (non-empty strings)
   - If either is missing or invalid, return HTTP 400 Bad Request with a clear error message

5. The route must forward the validated request to the backend API (URL stored in environment variable, never hardcoded).

6. The route must preserve the HTTP status code from the backend response:
   - If backend returns 200, proxy returns 200
   - If backend returns 401, proxy returns 401
   - If backend returns 404, proxy returns 404
   - If backend returns 502, proxy returns 502
   - Status codes are preserved to allow frontend to distinguish error types (Step 06 — Error Definitions)

7. The route must return the response body from the backend as-is (typically JSON).

8. If the backend request times out (e.g., after 30 seconds), the proxy must return HTTP 504 Gateway Timeout or 502 Bad Gateway.

9. If the backend request fails to establish a connection (e.g., service unavailable), the proxy must return HTTP 502 Bad Gateway.

10. The proxy must not add, remove, or modify the response body from the backend (transparent forwarding).

11. The proxy must not expose the backend URL or any internal infrastructure details in error responses.

12. The proxy should add appropriate security headers (e.g., `Content-Security-Policy`, `X-Content-Type-Options`) to responses, following Next.js best practices.

13. The proxy should log request/response metadata for debugging (excluding sensitive data like tokens) — logging strategy is a backend concern, but tokens must never appear in logs.

14. The proxy route should be type-safe (TypeScript) with proper type definitions for request/response.

## Route Specification

**Path:** `/api/jobs/status` (or similar convention)

**Method:** GET or POST (to be determined with backend team)

**Request Format (GET with Query Parameters):**
```
GET /api/jobs/status?jobId=abc123&jobToken=xyz789
```

**Request Format (POST with JSON Body):**
```
POST /api/jobs/status
Content-Type: application/json

{
  "jobId": "abc123",
  "jobToken": "xyz789"
}
```

**Success Response (HTTP 200):**
Backend response body is returned as-is. Example:
```
{
  "jobId": "abc123",
  "status": "running",
  "stage": "validation",
  "result": null,
  "error": null,
  "submittedAt": "2025-02-22T14:30:00Z",
  "completedAt": null
}
```

**Error Response (HTTP 400 — Validation Failure):**
```
{
  "error": "Missing or invalid parameters: jobId and jobToken are required"
}
```

**Error Response (HTTP 401/404 — Backend Authorization Failure):**
Backend response body is returned as-is, preserving the status code.

**Error Response (HTTP 502 — Backend Unavailable):**
```
{
  "error": "Unable to reach analysis service"
}
```

## Input Validation Rules

| Parameter | Required | Type | Validation |
|-----------|----------|------|------------|
| `jobId` | Yes | String | Non-empty, < 256 characters (reasonable limit) |
| `jobToken` | Yes | String | Non-empty, < 256 characters (reasonable limit) |

If validation fails, return HTTP 400 with a clear message.

## Error Handling in the Proxy

| Backend Status | Proxy Action | Proxy Status | Message |
|----------------|--------------|--------------|---------|
| 200 | Forward response | 200 | (Backend response body) |
| 401 | Forward response | 401 | (Backend response body) |
| 404 | Forward response | 404 | (Backend response body) |
| 500, 502, 503 | Forward response | Same | (Backend response body) |
| Timeout (e.g., 30s+) | Timeout error | 504 or 502 | "Request timed out" or "Service unavailable" |
| Connection refused | Connection error | 502 | "Unable to reach analysis service" |
| Invalid response body | Forward status | Same | (Backend response body, even if invalid JSON) |

## Security Considerations

- **No token logging:** Request parameters and response bodies containing tokens must not be logged
- **No URL exposure:** Backend API URL must not appear in error messages or responses
- **Rate limiting:** Optional for now; can be added by proxy if needed (not specified here)
- **CORS:** If frontend and proxy are on different origins (unlikely in same Next.js app), CORS headers should be set appropriately
- **Timeout protection:** Long-running requests should timeout to prevent resource exhaustion
- **Content validation:** Proxy should validate Content-Type (expect JSON from backend)

## Acceptance Criteria

- Valid request with correct jobId and jobToken returns HTTP 200 with backend response
- Request missing jobId returns HTTP 400 with a clear error message
- Request missing jobToken returns HTTP 400 with a clear error message
- Backend 401 response is forwarded as HTTP 401 (status code preserved)
- Backend 404 response is forwarded as HTTP 404 (status code preserved)
- Backend 502 response is forwarded as HTTP 502 (status code preserved)
- Timeout after 30 seconds returns HTTP 504 or 502
- Connection error returns HTTP 502 with a user-friendly message
- Response body from backend is returned unchanged (transparent forwarding)
- Backend URL is never exposed in error messages
- Request/response is type-safe (TypeScript validation)
- Multiple concurrent requests to the proxy are handled correctly

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Very long jobId or jobToken (e.g., 10,000 chars) | Validation fails; HTTP 400 is returned |
| jobId is an empty string | Validation fails; HTTP 400 is returned |
| jobToken is an empty string | Validation fails; HTTP 400 is returned |
| Backend returns non-JSON response | Proxy forwards it as-is; frontend handles parsing error (Step 06, 10) |
| Backend response is missing expected fields | Proxy forwards it as-is; frontend handles parsing error |
| Backend returns HTTP 200 but with error message in body | Proxy forwards it; frontend treats status as authoritative |
| Multiple requests to the proxy simultaneously | All are processed independently; no queueing |
| Backend response body is very large (MB-scale) | Proxy forwards it; potential performance impact on frontend |

## Performance Notes

- Proxy introduces minimal latency (typically < 50ms)
- With < 13 concurrent requests per second (Step 08 — Frontend Polling), proxy load is negligible
- Backend connection pooling can optimize repeated calls to the same backend
- Caching of successful responses can be considered in future iterations (not in scope here)

## Deployment Considerations

- Proxy route must be deployed with the frontend application
- Backend API URL must be available as an environment variable at deployment time
- Rate limiting or request throttling can be added later if needed
- Monitoring/logging should track error rates and response times

## Dependencies

- Depends on Step 05 (Job Status Endpoint) for backend response format
- Depends on Step 04 (Job Creation Endpoint) to provide jobId and jobToken that are forwarded
- Called by Step 08 (Frontend Polling) for status queries
- Informs Step 10 (Frontend UI) about HTTP status codes available for error handling
