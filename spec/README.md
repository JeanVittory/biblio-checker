# Specs (Spec-Driven Development / SDD)

The `spec/` directory contains **feature-level specifications** written in a Spec-Driven Development (SDD) style.

## Structure

Each feature lives in `spec/<feature>/` and typically includes:

- `README.md` — suite overview and how to read it
- `INDEX.md` — navigation + reading order
- `NN-*/spec.md` — one spec per numbered step (functional requirements + acceptance criteria)

## Suites

- `spec/recent-analyses/` — “Recent Analyses” (job tracking + localStorage persistence + status polling).
- `spec/results-contract-v1/` — “Results Contract v1” (normative `results` / `result` JSON schema + enums + validation requirements).
- `spec/worker-framework/` — “Worker Framework” (state machine, atomic job claiming, pipeline framework, retry and recovery).
- `spec/audit-logging/` — “Audit Logging” (job event tracking, reference audit log, data retention cleanup).
- `spec/structured-logging/` — “Structured Logging” (Pino for frontend, structlog for backend/worker, request correlation, JSON output).
- `spec/langgraph-reference-analysis/` — “LangGraph Reference Analysis” (LangGraph graph for bibliographic reference verification: text extraction, LLM parsing/normalization, API verification, classification, report assembly).
