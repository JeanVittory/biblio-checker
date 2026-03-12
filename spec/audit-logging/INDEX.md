# Audit Logging — Index

## Reading Order

Steps are designed to be read sequentially. Database schemas (02-03) must be understood before the repos that operate on them (05-06).

## Dependency Graph

```
01-product-overview
 ├── 02-job-events-schema
 │    ├── 05-backend-audit-repo
 │    └── 06-worker-audit-repo
 ├── 03-reference-audit-schema
 │    └── 06-worker-audit-repo
 └── 04-retention-policy
      (depends on 02, 03)

07-integration-points
 (depends on all previous steps)
```

## Quick Reference

| Step | Title | Layer | Depends On |
|---|---|---|---|
| 01 | Product Overview | Product | — |
| 02 | Job Events Schema | Database | 01 |
| 03 | Reference Audit Schema | Database | 01 |
| 04 | Retention Policy | Database | 02, 03 |
| 05 | Backend Audit Repo | Backend | 02 |
| 06 | Worker Audit Repo | Worker | 02, 03 |
| 07 | Integration Points | Cross-cutting | 01-06 |

## Implementation Phases

| Phase | Steps | Owner |
|---|---|---|
| 1 — Database migrations | 02, 03, 04 | DBA / Backend |
| 2 — Python infrastructure | 05, 06 | Backend + Worker |
| 3 — Flow integration (future) | 07 | Backend + Worker |
