# Share Link Feature — Specification Suite

This directory contains a complete Spec-Driven Development (SDD) specification for the "Share Link" feature of Biblio Checker.

## Quick Start

1. **Start here:** Read `INDEX.md` for an overview and navigation guide
2. **Full specs:** Open any numbered folder (01-09) to read the detailed functional specification
3. **For implementation:** Begin with steps in the order recommended in `INDEX.md`

## What's Included

9 numbered specification directories, each containing a single `spec.md`:

- `01-overview` — Feature overview, scope, and value proposition
- `02-database-schema` — New columns on `analysis_jobs` for share tokens
- `03-share-token-generation` — Backend endpoint to generate share tokens on demand
- `04-public-read-endpoint` — Backend endpoint to read results by share token (no auth)
- `05-frontend-proxy` — Next.js API route proxying to the public read endpoint
- `06-share-page` — Frontend `/r/[shareToken]` page rendering shared results
- `07-share-button` — UI button in ExpandedDetail to generate and copy share links
- `08-i18n-catalog` — i18n keys for all three features across ES/PT/EN
- `09-acceptance-and-validation` — End-to-end acceptance criteria and testing

## Key Features Specified

- **On-demand share token generation** — User clicks "Share" to create a public URL; not auto-generated
- **Public read-only access** — Anyone with the URL can view results; no login or jobToken needed
- **Copy to clipboard** — One-click URL copy with visual feedback
- **Standalone share page** — `/r/<token>` renders a full results view with Biblio Checker branding
- **Privacy by default** — Jobs are private until explicitly shared; share can be revoked

## Important Notes

**These specs contain:**
- Functional requirements (what the system does)
- Database schema changes
- API contracts (request/response format)
- User flows and interactions
- Acceptance criteria (how to verify it works)
- Edge cases and error states

**These specs do NOT contain:**
- Code (Python, TypeScript, SQL, etc.)
- Implementation details or architecture
- Technology choices beyond what's already in the stack
- Styling details (exact colors, fonts, spacing)

## Using These Specs

### For Backend Engineers
- Priority: Steps 02, 03, 04
- Focus on migration, token generation endpoint, public read endpoint

### For Frontend Engineers
- Priority: Steps 05, 06, 07
- Focus on proxy route, share page, share button

### For QA/Testing
- Reference Step 09 for end-to-end acceptance criteria
- Each spec's "Acceptance Criteria" section is a testable checklist

## Dependency Flow

```
01 (Overview)
├── 02 (Database Schema) [Foundation]
│   ├── 03 (Share Token Generation)
│   └── 04 (Public Read Endpoint)
│       └── 05 (Frontend Proxy)
│           └── 06 (Share Page)
├── 03 ──> 07 (Share Button)
│          └── 05
└── 08 (i18n Catalog) [Cross-cutting]
    └── 06, 07
09 (Acceptance) [Depends on all]
```

## Implementation Phases

| Phase | Steps | Deliverable | Team |
|-------|-------|-------------|------|
| 1 | 02, 08 | Migration + i18n keys | Backend + Frontend |
| 2 | 03, 04 | Backend endpoints | Backend |
| 3 | 05, 06, 07 | Frontend proxy, page, button | Frontend |
| 4 | 09 | End-to-end validation | QA |

Phases 1 backend and frontend can run in parallel.

## Cross-Suite Dependencies

- **results-contract-v1** — The share page renders `ResultsV1` data
- **recent-analyses** — The share button integrates into `ExpandedDetail`
- **momento-wow** — The share page reuses `AuthenticityScore` and classification display
- **i18n-multilingual-support** — Extends existing message catalogs

---

**Status:** Complete and Ready for Implementation
**Last Updated:** April 16, 2026
**For:** Biblio Checker — Share Link Feature
