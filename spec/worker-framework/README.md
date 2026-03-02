# Worker Job Processing Framework

## Overview

This specification suite defines the framework that powers the biblio-checker worker: a polling-based job processor that claims analysis jobs from the `analysis_jobs` Supabase table, runs them through a multi-stage pipeline, and handles errors, retries, and crash recovery.

## Problem Statement

The worker at `apps/worker/` is currently a stub. It has a polling loop that calls `poll_once()` every 5 seconds but performs no work. The `analysis_jobs` table already has the schema to support full lifecycle management (status, stage, attempts, job_token, token_expires_at), but no code drives these transitions. This spec suite defines the complete processing framework so that jobs move from `queued` through analysis stages to `succeeded` or `failed`.

## Scope

**In scope:**
- State machine governing job status and stage transitions
- Atomic job claiming via Postgres RPC (concurrency-safe)
- Domain layer: enums, error types, typed job model
- Repository layer: DB operations for claiming, advancing stages, and marking outcomes
- Pipeline framework: stage contract, context, orchestration runner
- Three pipeline stages: extract, langgraph (stub), persist
- Polling loop integration
- Retry strategy and crash recovery

**Out of scope:**
- LangGraph graph implementation (reference verification logic)
- Text extraction from PDF/DOCX (will be implemented separately)
- Results Contract v1 schema definition (see `spec/results-contract-v1/`)
- Frontend polling and display
- 7-day retention / cleanup scheduling

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Retry mode | Restart from `stage=created` | Simpler for v1; design allows future migration to resume-from-stage |
| Concurrency control | Postgres RPC with `FOR UPDATE SKIP LOCKED` | PostgREST cannot expose row-level locking; RPC is the only atomic option |
| Lease mechanism | Token + TTL per job | Enables crash recovery without external coordination |
| LangGraph stage | Stub only | Framework must be testable before the analysis flow is built |
| Text extraction | Duplicated in worker | Avoids cross-app imports; keeps apps independent |

## Audience

| Reader | Start here |
|--------|------------|
| Implementing the worker framework | Step 01 (state machine), then follow INDEX.md order |
| Understanding concurrency guarantees | Step 02 (atomic job claiming) |
| Adding a new pipeline stage | Step 05 (pipeline framework) for the contract, then any stage spec |
| Understanding retry behavior | Step 10 (retry and recovery) |

## Statistics

| Metric | Value |
|--------|-------|
| Total steps | 10 |
| New Python modules | ~12 files |
| Modified Python modules | 2 files |
| Database migrations | 1 (Postgres RPC) |
| Estimated implementation phases | 3 (DB, domain+repo, pipeline+integration) |
