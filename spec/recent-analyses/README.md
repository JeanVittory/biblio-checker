# Recent Analyses Feature — Specification Suite

This directory contains a complete Spec-Driven Development (SDD) specification for the "Recent Analyses" feature of Biblio Checker.

## Quick Start

1. **Start here:** Read `INDEX.md` for an overview and navigation guide
2. **Full specs:** Open any numbered folder (01-11) to read the detailed functional specification
3. **For implementation:** Begin with steps in the order recommended in `INDEX.md`

## What's Included

11 numbered specification directories, each containing a single `spec.md`:

- `01-product-overview` — Feature overview, scope, and value
- `02-job-access-model` — Token-based security model
- `03-database-schema` — Database schema requirements
- `04-job-creation-endpoint` — Backend job creation endpoint
- `05-job-status-endpoint` — Backend status query endpoint
- `06-error-definitions` — Complete error catalog
- `07-frontend-data-model` — Frontend data structures and storage
- `08-frontend-polling` — Real-time status polling mechanism
- `09-frontend-proxy-route` — Next.js proxy for backend communication
- `10-frontend-ui` — UI table component and interactions
- `11-upload-flow-integration` — Integration with upload form

## Key Features Specified

✓ **Persistent Job Tracking** — Jobs stored in localStorage across page refreshes
✓ **Real-time Status Updates** — Polling every 4 seconds for active jobs
✓ **Secure Access** — Token-based authorization; tokens expire after 1 hour
✓ **User-friendly UI** — Expandable rows, status badges, relative timestamps
✓ **Error Resilience** — Graceful handling of network failures, auth errors, storage limits
✓ **No User Auth** — Works without login; tokens act as receipts

## Important Notes

**These specs contain:**
- Functional requirements (what the system does)
- User flows and interactions
- Acceptance criteria (how to verify it works)
- Edge cases and error states
- Data model definitions
- API contracts (request/response format)

**These specs do NOT contain:**
- Code (Python, TypeScript, SQL, etc.)
- Implementation details or architecture
- Technology choices (framework, database, etc.)
- Styling or animation code
- Git workflows or deployment procedures

## Using These Specs

### For Project Managers
- Read Step 01 for scope and value
- Share all 11 specs with team for implementation planning
- Reference Steps 06, 10 for user-facing behavior and acceptance criteria

### For Backend Engineers
- Priority: Steps 02, 03, 04, 05, 06
- Focus on token model, endpoints, and error responses
- Steps 07-11 provide context on how frontend will use the API

### For Frontend Engineers
- Priority: Steps 07, 08, 09, 10, 11
- Understand data model and storage strategy first
- Steps 02-06 explain backend behavior and error responses

### For QA/Testing
- Reference Step 06 for error states to test
- Reference Step 10 for UI interactions to verify
- Each spec's "Acceptance Criteria" section is a testable checklist

### For Security Review
- Focus on Step 02 (token model and expiry)
- Review Steps 04, 05 for authorization validation
- Confirm HTTPS and secure header requirements

## Specification Statistics

| Metric | Value |
|--------|-------|
| Total Specifications | 11 |
| Total Lines | ~1,565 |
| Average Per Spec | ~142 lines |
| Format | Markdown |
| Estimated Read Time | 2-3 hours (full) or 30 min (focused) |

## Dependency Flow

```
Security Model (02)
├── Database Schema (03)
├── Job Creation Endpoint (04)
├── Job Status Endpoint (05)
└── Error Definitions (06)
    ├── Frontend Data Model (07)
    ├── Frontend Polling (08)
    ├── Frontend Proxy Route (09)
    ├── Frontend UI (10)
    └── Upload Flow Integration (11)
```

All steps are cohesive and non-redundant. Each step builds on prior steps but can be understood independently.

## Implementation Phases

Recommended phases for development:

| Phase | Steps | Duration | Deliverable |
|-------|-------|----------|-------------|
| 1 | 02-06 | Backend only | API with token model, endpoints, errors |
| 2 | 07-09 | Frontend infra | Data model, polling, proxy (no UI) |
| 3 | 10 | Frontend UI | Table component, interactions |
| 4 | 11 | Integration | Upload form → Recent Analyses |

Phases 1 and 2 can be worked in parallel by backend and frontend teams.

## Navigating the Specs

Each spec.md follows this structure:

```
# Step NN — Title
## Scope (what's in/out)
## Context (background)
## Requirements (numbered functional requirements)
## Acceptance Criteria (testable checklist)
## Edge Cases (corner cases and expected behavior)
## Integration Points (how it connects to other steps)
## Dependencies (which steps must be done first)
```

This consistent structure makes it easy to jump between specs and understand relationships.

## Questions or Clarifications?

Before implementation, resolve any unclear items listed in each spec's "Open Questions" or "Unclear Items" section. These typically include:

- Exact JSON response format (backend team confirms)
- Timestamp precision and timezone handling
- Query parameter vs. request body convention
- Result payload structure (backend analysis output)

## Maintenance

To keep specs up-to-date:

1. Update the affected step(s)
2. Check if dependencies change (update dependency graph)
3. Notify teams of changes
4. Update INDEX.md if the structure changes

---

**Status:** Complete and Ready for Implementation
**Last Updated:** February 22, 2026
**For:** Biblio Checker Recent Analyses Feature
