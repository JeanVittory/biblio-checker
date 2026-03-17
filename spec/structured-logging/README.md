# Structured Logging — Spec Suite

## Purpose

Establish structured logging infrastructure across all three apps (frontend, backend, worker) to enable production monitoring, debugging, and request/job traceability.

## Problem Statement

The system has no structured logging. The frontend uses raw `console.*` calls (5 occurrences across 4 files). The backend has almost no logging — API errors are silently swallowed without any trace. The worker uses stdlib `logging` with a basic text format that is not machine-parseable. In production, there is no way to correlate requests, trace job lifecycle events, or aggregate error patterns.

## Technology Choices

| App | Library | Rationale |
|---|---|---|
| Frontend (Next.js) | **Pino** | De-facto standard for Node.js structured logging. Built-in browser support, JSON output, pino-pretty for dev. |
| Backend (FastAPI) | **structlog** | Most popular Python structured logging library. Wraps stdlib logging, JSON output, colored dev console, contextvars for request correlation. |
| Worker (Python) | **structlog** | Same as backend for consistency. Replaces existing `logging.basicConfig` setup. |

## Audience

| Persona | Start here | Focus on |
|---|---|---|
| Product / QA | Step 01 | Scope, goals, non-goals |
| Frontend dev | Steps 02-03 | Pino setup, console.* migration |
| Backend dev | Steps 04-06 | structlog config, middleware, coverage |
| Worker dev | Steps 04, 07-08 | structlog config, migration, coverage |

## Suite Statistics

| Metric | Value |
|---|---|
| Steps | 8 |
| New files created | 5 (1 TS, 2 Python config, 1 Python middleware, 1 Python config settings) |
| Existing files modified | ~20 |
| New dependencies | 3 (`pino`, `pino-pretty`, `structlog`) |
