# Worker Framework — Reading Order and Dependencies

## Dependency Graph

```
01 (State Machine) ──> 02 (Atomic Claiming) ──> 03 (Domain Layer) ──> 04 (Repository)
                                                                           │
                                                       ┌───────────────────┘
                                                       v
                                                 05 (Pipeline Framework)
                                                       │
                                          ┌────────────┼────────────┐
                                          v            v            v
                                    06 (Extract)  07 (LangGraph) 08 (Persist)
                                          │            │            │
                                          └────────────┼────────────┘
                                                       v
                                                 09 (Polling Integration)
                                                       │
                                                       v
                                                 10 (Retry & Recovery)
```

## Navigation

| Step | Title | Depends on | Key deliverable |
|------|-------|------------|-----------------|
| 01 | State Machine Definition | — | Status/stage enums, valid transition table |
| 02 | Atomic Job Claiming | 01 | Postgres RPC `claim_analysis_job`, lease model |
| 03 | Job Domain Layer | 01 | Python enums, error types, AnalysisJob model |
| 04 | Job Repository | 02, 03 | `repo.py` with claim, update_stage, mark_succeeded, mark_failed |
| 05 | Pipeline Framework | 03 | Stage contract, JobContext, pipeline runner |
| 06 | Extract Stage | 04, 05 | Storage download + SHA-256 verification |
| 07 | LangGraph Stage | 04, 05 | LangGraph wrapper (stub) |
| 08 | Persist Stage | 04, 05 | Result validation + DB write |
| 09 | Polling Integration | 04, 05, 06, 07, 08 | Modified `poll_once()` wiring everything together |
| 10 | Retry and Recovery | All above | Error classification, retry strategy, crash recovery |

## Implementation Phases

**Phase 1 — Database** (Step 02): Apply the migration. No Python changes.

**Phase 2 — Domain + Repository** (Steps 03, 04): Pure Python modules with no pipeline dependency. Testable in isolation.

**Phase 3 — Pipeline + Integration** (Steps 05–09): Build the pipeline framework, implement stages, wire into polling loop.

**Phase 4 — Hardening** (Step 10): Verify retry and crash recovery behavior end-to-end.
