# Recent Analyses Feature — Specification Index

This folder contains a complete Spec-Driven Development (SDD) breakdown of the "Recent Analyses" feature for Biblio Checker. Each specification file is a self-contained functional requirement document suitable for implementation.

## Structure

The specifications are organized into 11 logical steps, numbered 01-11. Each step is a directory containing a single `spec.md` file.

### Reading Order

**Recommended reading order for stakeholders and engineers:**

1. **01-product-overview** — Start here. High-level overview of the feature, scope, and value proposition.
2. **02-job-access-model** — Security model and token lifecycle (foundational for backend design).
3. **03-database-schema** — Schema changes needed to support tokens.
4. **04-job-creation-endpoint** — Backend endpoint for creating jobs with tokens.
5. **05-job-status-endpoint** — Backend endpoint for querying job status with token validation.
6. **06-error-definitions** — Complete error catalog and user-facing behavior.
7. **07-frontend-data-model** — Frontend data structures and localStorage helpers.
8. **08-frontend-polling** — Frontend polling mechanism for real-time status updates.
9. **09-frontend-proxy-route** — Frontend server-side proxy for backend communication.
10. **10-frontend-ui** — Frontend UI component and user interactions.
11. **11-upload-flow-integration** — Integration between upload form and Recent Analyses feature.

### Dependency Graph

```
01 (Product Overview)
 └─ 02 (Job Access Model) [Foundation]
     ├─ 03 (Database Schema)
     │   ├─ 04 (Job Creation Endpoint)
     │   └─ 05 (Job Status Endpoint)
     ├─ 06 (Error Definitions) [Cross-cutting]
     │   ├─ 07 (Frontend Data Model)
     │   ├─ 08 (Frontend Polling)
     │   ├─ 09 (Frontend Proxy Route)
     │   └─ 10 (Frontend UI)
     └─ 11 (Upload Flow Integration)
         ├─ 07 (Frontend Data Model)
         ├─ 08 (Frontend Polling)
         └─ 10 (Frontend UI)
```

### Quick Navigation

| Step | Title | Audience | Focus |
|------|-------|----------|-------|
| 01 | Product Overview | Everyone | Feature definition, scope, value |
| 02 | Job Access Model | Backend, Security | Token lifecycle, security principles |
| 03 | Database Schema | Backend, DBA | Table changes, columns, indexing |
| 04 | Job Creation Endpoint | Backend | Extended response format |
| 05 | Job Status Endpoint | Backend | New endpoint behavior, validation |
| 06 | Error Definitions | Everyone | Error types, recovery, user experience |
| 07 | Frontend Data Model | Frontend | Data structures, localStorage helpers |
| 08 | Frontend Polling | Frontend | Polling mechanism, lifecycle |
| 09 | Frontend Proxy Route | Frontend, Backend | Proxy implementation, forwarding |
| 10 | Frontend UI | Frontend, Design | Table component, interactions |
| 11 | Upload Flow Integration | Frontend | Form integration, job capture |

## Key Concepts

### Job Access Control (Steps 02, 03, 04, 05)

Jobs are accessed via a **token-based model** without requiring user authentication:
- Each job receives a unique, short-lived token (1 hour TTL) at creation
- Frontend stores both `jobId` and `jobToken` in localStorage
- Status queries require both values; missing or expired tokens return a generic 404/401
- Prevents job ID enumeration while keeping access simple

### Frontend Persistence (Steps 07, 08, 10)

Job data is persisted in browser **localStorage** for:
- Surviving page refreshes
- Per-browser, per-device (no cross-device sync)
- Automatic cleanup when browser data is wiped
- Efficient reads/writes for < 50 jobs per session

### Real-time Updates (Steps 08, 09, 10)

**Polling mechanism** (every 4 seconds) keeps status current:
- Independent intervals per job (no blocking)
- Automatic resume on page load
- Graceful error handling (transient failures retry; auth failures stop immediately)
- UI updates reflect status changes without manual refresh

### Error Resilience (Step 06)

Comprehensive error handling for:
- Network failures (transient; auto-retry)
- Authorization failures (permanent; stop polling)
- Storage quota exceeded (warn user; preserve existing data)
- Malformed responses (graceful degradation)

## Acceptance Criteria by Feature

### Feature: Track Job Status
- **What:** Real-time visibility into job progress without manual refresh
- **How:** Polling every 4 seconds, localStorage persistence
- **Acceptance:** User can watch job progress in the table; status updates automatically

### Feature: Persistent Job List
- **What:** Job history survives page refresh in the same browser session
- **How:** Browser localStorage
- **Acceptance:** Refreshing the page shows the same jobs; data is cleared when browser data is wiped

### Feature: Secure Access
- **What:** Only authorized users (with a valid token) can query job status
- **How:** Token-based validation; tokens expire after 1 hour
- **Acceptance:** Invalid tokens return generic error; valid tokens return job status

### Feature: User Transparency
- **What:** Clear feedback on job state, errors, and troubleshooting steps
- **How:** Status badges, expanded detail panels, error messages
- **Acceptance:** User always knows what state a job is in; error messages are actionable

## No Code Zone

All files in this specification are **functional requirements only**. They contain:
- User flows and interactions
- Data model specifications (not code)
- Acceptance criteria
- Edge cases and error conditions
- UI/UX requirements
- API contracts (requests/responses, not implementation)

They do **NOT** contain:
- Code snippets (Python, TypeScript, SQL, etc.)
- Database DDL or migration scripts
- API endpoint code or route handlers
- React component code or hooks
- CSS styling or animation code
- Architecture diagrams or technical design

## Implementation Phases

These specifications can be implemented in multiple phases:

**Phase 1 (Backend Foundation):**
- Steps 02-06: Token model, database schema, endpoints, error handling

**Phase 2 (Frontend Infrastructure):**
- Steps 07-09: Data model, localStorage, polling, proxy route

**Phase 3 (Frontend UI):**
- Step 10: Table component, interactions

**Phase 4 (Integration):**
- Step 11: Upload form integration

Teams can work on Phase 1 and Phase 2 in parallel if desired.

## Review Checklist

Before implementation begins:

- [ ] Product team has reviewed Step 01 (scope is agreed)
- [ ] Backend team has reviewed Steps 02-06 (API contracts are clear)
- [ ] Frontend team has reviewed Steps 07-11 (data flow and UI are understood)
- [ ] Security team has reviewed Step 02 (token model is acceptable)
- [ ] QA team has reviewed Steps 06, 10 (error states and acceptance criteria are testable)
- [ ] All teams have discussed the dependency graph and implementation order

## Open Questions (Flagged in Specifications)

The following sections of specifications include "Open Questions" or unclear details:

- **Step 04:** Exact response format (JSON structure) should be confirmed with backend team
- **Step 05:** Exact response format and timestamp precision should be confirmed
- **Step 09:** Query parameter vs. request body convention for jobId and jobToken
- **Step 10:** Result payload format depends on backend analysis output (agree on structure)

These should be resolved in kick-off discussions before implementation starts.

## Maintenance and Updates

If the feature requirements change:
1. Update the relevant step(s)
2. Check dependencies (does the change affect other steps?)
3. Update the dependency graph if needed
4. Notify all teams of the change

Example: If token TTL changes from 1 hour to 2 hours, update Step 02 and notify affected teams.

## Total Specification Size

- 11 specification files
- ~1,565 lines of functional requirements
- Estimated read-through time: 2-3 hours for full understanding; 30 minutes for focused review

---

Generated: February 22, 2026
For: Biblio Checker — Recent Analyses Feature
