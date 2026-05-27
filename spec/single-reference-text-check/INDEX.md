# Single Reference Text Check — Specification Index

This folder contains a complete Spec-Driven Development (SDD) breakdown of the **"Single Reference Text Check"** feature for Biblio Checker.

## Structure

The specifications are organized into 9 logical steps, numbered 01-09. Each step is a directory containing a single `spec.md` file.

### Reading Order

1. **01-overview** — Start here. Scope, value proposition, user journey.
2. **02-database-schema** — `input_kind`, `raw_reference_text`, nullable file fields, CHECK constraint.
3. **03-backend-text-endpoint** — `POST /api/analysis/start-text` contract.
4. **04-worker-text-mode** — Pipeline branch for `input_kind='text'` jobs.
5. **05-frontend-gateway** — `/api/analysis-text-gateway` Next.js proxy.
6. **06-input-component** — `SingleReferenceForm` (textarea, validation, submit).
7. **07-tabs-and-recent-analyses** — AppClient tabs + history badge.
8. **08-i18n-catalog** — Complete key catalog for EN/ES/PT.
9. **09-acceptance-and-validation** — End-to-end criteria and test matrix.

### Dependency Graph

```
01 (Overview)
 ├── 02 (Database Schema) [Foundation]
 │    ├── 03 (Backend Text Endpoint)
 │    │    └── 04 (Worker Text Mode)
 │    │         └── 05 (Frontend Gateway)
 │    │              ├── 06 (Input Component)
 │    │              │    └── 07 (Tabs & Recent Analyses)
 │    │              └── 07
 │    └── 04
 ├── 08 (i18n Catalog) [Cross-cutting]
 │    └── 06, 07
 └── 09 (Acceptance) [All previous steps]
```

### Quick Navigation

| Step | Title | Audience | Focus |
|------|-------|----------|-------|
| 01 | Overview | Everyone | Feature scope, user journey |
| 02 | Database Schema | Backend, DBA | Migration, new columns, CHECK constraint |
| 03 | Backend Text Endpoint | Backend | `POST /api/analysis/start-text` |
| 04 | Worker Text Mode | Backend | Pipeline branch, langgraph entrypoint |
| 05 | Frontend Gateway | Frontend | Next.js proxy route |
| 06 | Input Component | Frontend | Textarea form |
| 07 | Tabs & Recent Analyses | Frontend | AppClient refactor + badge |
| 08 | i18n Catalog | Frontend | EN/ES/PT keys |
| 09 | Acceptance | QA | E2E criteria, testing |

## Key Concepts

### Two Input Modes, One Job Lifecycle
A job's `input_kind` is either `file` (current behavior) or `text` (this feature). Both flow through the same `analysis_jobs` table, the same worker polling loop, and emit the same `ResultsV1`. The only differences are: which columns are populated at insert time, and which pipeline stages run.

### Single Canonical Reference (No Multi-Paste)
The text input accepts exactly **one bibliographic reference** per submission (20–2000 chars). Multi-line input is allowed (a single reference may wrap), but the system does NOT split into multiple references. This decision lets us bypass the `parse_references` LangGraph node entirely.

### No File Coupling for Text Jobs
Text-mode jobs have NULL `bucket`, `path`, `sha256`, and `source_type`. A CHECK constraint enforces consistency: `input_kind='file'` requires all four fields; `input_kind='text'` requires `raw_reference_text` and forbids them. This keeps existing file-mode logic untouched.

### Reuse Over Rebuild
- `verify_single_reference()` (worker, pure function) — used as-is
- `ResultsV1` (backend + frontend) — unchanged; references array of length 1
- Polling proxy `/api/jobs/status` and `useRecentAnalysesPolling` — unchanged
- `parseResultsV1`, `ExpandedDetail` — unchanged

### Public-Facing Display Name
Since there's no filename, the frontend stores the first 60 characters of the pasted text as the display name in `RecentAnalyses` (truncated with ellipsis). The reference's `rawText` is also part of the resulting `ReferenceResult`, so the user can always see the full original.

---

Generated: May 3, 2026
For: Biblio Checker — Single Reference Text Check Feature
