# Step 02 — Job Access Model and Security

## Scope

This step defines the security model for job access in the Recent Analyses feature. It covers:
- Token generation and format (at job creation)
- Token lifecycle and expiry rules (1 hour TTL)
- How tokens are validated (what the backend checks)
- Error behavior for invalid, expired, or missing tokens
- Security principles (preventing job ID enumeration, timing-safe validation)

This step does NOT cover:
- Implementation details of token generation (hashing, encoding, cryptography)
- Database indexing strategies
- Rate limiting or DoS protection (beyond token validation)
- Backend endpoint code or frameworks
- Frontend token storage mechanics (see Step 07 — Frontend Data Model)

## Context

Because Biblio Checker has no user authentication, there is no built-in access control. Anyone with a job ID could theoretically discover and monitor other users' jobs. Tokens solve this by requiring both a job ID and a secret token to query job status. Tokens are short-lived (1 hour) to limit the window of exposure if a URL or token is leaked.

## Requirements

1. Every job created by the backend must have a unique, cryptographically secure token assigned at creation time.
2. Each token must have an expiry timestamp; tokens expire exactly 1 hour after job creation.
3. The token must be returned to the frontend in the job creation response (see Step 04).
4. The backend must validate tokens on every status query (see Step 05).
5. Token validation must check two conditions:
   - The token value matches the stored token for the given job ID
   - The current time is before the token's expiry timestamp
6. If either condition fails, the backend must return a 401 (Unauthorized) response with no indication of whether the job exists.
7. If the job does not exist (regardless of token), the backend must also return 404 (Not Found) with no indication of whether the token was valid.
8. The 404 and 401 responses must be indistinguishable in error message and HTTP status to prevent job ID enumeration.
9. Tokens should be treated as secrets and never logged or exposed in debugging output.
10. Tokens must remain constant for the lifetime of the job (no refresh or rotation during a job's execution).

## Acceptance Criteria

- A valid token with a non-expired timestamp allows the frontend to query job status successfully
- An invalid token (wrong value, correct job ID) returns 404 or 401 with identical error messages
- An expired token (valid format, past expiry time) returns 401 with the same message as an invalid token
- A queried job that does not exist returns 404 with the same message as an invalid token
- The token is returned in the job creation response (payload and HTTP status verified in Step 04)
- A job cannot be accessed 61 minutes after creation, even with the correct token

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Querying a job 59 minutes after creation | Token is still valid; status returned successfully |
| Querying a job 61 minutes after creation | Token is expired; 401 response returned |
| Querying with job ID but no token | Invalid input; handled by frontend validation or 400 Bad Request |
| Querying with token but no job ID | Invalid input; handled by frontend validation or 400 Bad Request |
| Querying with valid token but wrong job ID | 404 response (same message as invalid token) |
| Token leaked in browser history or logs | Risk is mitigated by 1-hour expiry; no additional controls required at this scope |
| Multiple concurrent status queries with same token | All queries succeed if token is not expired |
| Token passed in URL vs. HTTP header | Determined by backend design; not specified here |

## Security Principles

- **No enumeration:** Identical error responses for "not found" and "unauthorized" prevent attackers from discovering valid job IDs by trial and error.
- **Time-limited access:** 1-hour TTL ensures leaked tokens have limited utility.
- **Simplicity:** Token validation is stateless (no session lookups); only requires checking the stored token and expiry time.
- **Transparency:** Frontend and backend teams agree on the token lifecycle upfront to avoid surprises during integration.

## Dependencies

- None. This step is foundational and has no dependencies on other steps.
- Step 03 (Database Schema) will be informed by the token and expiry timestamp storage requirements.
- Step 04 (Job Creation Endpoint) will implement token generation and return.
- Step 05 (Job Status Endpoint) will implement token validation.
