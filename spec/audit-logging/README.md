# Audit Logging — Spec Suite

## Purpose

Define the infrastructure for complete traceability of job lifecycle events and per-reference verification outcomes in the Biblio Checker system.

## Problem Statement

The system currently stores only the final state of each job (`analysis_jobs.error_code`, `error_detail`). There is no history of state transitions, no record of retries, and no way to audit individual reference verification outcomes independently of the full results blob. The 7-day retention policy documented in SYSTEM_SPEC is not enforced.

## Audience

| Persona | Start here | Focus on |
|---|---|---|
| Product / QA | Step 01 | Scope, acceptance criteria, integration points |
| Backend dev | Steps 02-05 | Job events schema, retention, backend repo |
| Worker dev | Steps 02-03, 06 | Job events schema, reference audit, worker repo |
| DBA / Infra | Steps 02-04 | Table schemas, indexes, retention function |

## Suite Statistics

| Metric | Value |
|---|---|
| Steps | 7 |
| New DB tables | 2 (`job_events`, `reference_audit_log`) |
| New DB functions | 1 (`cleanup_expired_data`) |
| New Python modules | 4 (2 enums + 2 repos) |
| Existing files modified | 0 |
