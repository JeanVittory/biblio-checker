# Share Link Feature — Specification Index

This folder contains a complete Spec-Driven Development (SDD) breakdown of the "Share Link" feature for Biblio Checker.

## Structure

The specifications are organized into 9 logical steps, numbered 01-09. Each step is a directory containing a single `spec.md` file.

### Reading Order

1. **01-overview** — Start here. Scope, value proposition, user journey.
2. **02-database-schema** — New columns on `analysis_jobs` for share tokens.
3. **03-share-token-generation** — Backend endpoint to create share tokens.
4. **04-public-read-endpoint** — Backend endpoint to read shared results publicly.
5. **05-frontend-proxy** — Next.js API route forwarding to backend.
6. **06-share-page** — Frontend `/r/[shareToken]` page.
7. **07-share-button** — UI button in the result panel.
8. **08-i18n-catalog** — Complete key catalog for EN/ES/PT.
9. **09-acceptance-and-validation** — End-to-end criteria and test matrix.

### Dependency Graph

```
01 (Overview)
 ├── 02 (Database Schema) [Foundation]
 │    ├── 03 (Share Token Generation)
 │    │    └── 07 (Share Button)
 │    └── 04 (Public Read Endpoint)
 │         └── 05 (Frontend Proxy)
 │              └── 06 (Share Page)
 ├── 08 (i18n Catalog) [Cross-cutting]
 │    └── 06, 07
 └── 09 (Acceptance) [All previous steps]
```

### Quick Navigation

| Step | Title | Audience | Focus |
|------|-------|----------|-------|
| 01 | Overview | Everyone | Feature scope, user journey |
| 02 | Database Schema | Backend, DBA | Migration, new columns |
| 03 | Share Token Generation | Backend | POST endpoint, auth |
| 04 | Public Read Endpoint | Backend | GET endpoint, no auth |
| 05 | Frontend Proxy | Frontend | Next.js API route |
| 06 | Share Page | Frontend | `/r/[shareToken]` page |
| 07 | Share Button | Frontend | UI component, clipboard |
| 08 | i18n Catalog | Frontend | EN/ES/PT keys |
| 09 | Acceptance | QA | E2E criteria, testing |

## Key Concepts

### Privacy Model
Jobs are **private by default**. Sharing is opt-in: the user must explicitly click "Share" to generate a public token. The share token is independent of the `poll_status_token` (which expires after 1 hour). Share tokens have a configurable TTL (default: 7 days).

### Token Design
- `share_token`: 32-character URL-safe token (`secrets.token_urlsafe(24)`)
- Stored on `analysis_jobs` table alongside existing tokens
- Generated on demand via authenticated endpoint
- Used as the sole identifier in the public URL (`/r/<token>`)

### Public Access
The public read endpoint returns the same `ResultsV1` data as the authenticated status endpoint but requires only the share token (no `jobId` or `jobToken`). It returns 404 for non-shared, expired, or non-existent tokens (enumeration-resistant).

---

Generated: April 16, 2026
For: Biblio Checker — Share Link Feature
