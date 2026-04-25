# AI-Enhanced Classification — Reading Order and Dependencies

## Dependency Graph

```
01 (Overview) ──> 02 (Enriched Decision Reasons)
                       │
                  03 (Adjudication Data Model)
                       │
                  04 (Prompt Design)
                       │
                  05 (Adjudication Node)
                       │
          ┌────────────┼────────────┐
          v            │            v
   06 (Cross-Pattern   │   07 (Cross-Pattern
       Deterministic)  │       LLM Analysis)
          │            │            │
          └────────────┼────────────┘
                       v
               08 (Graph Topology)
                       │
                       v
               09 (Configuration)
                       │
                       v
               10 (Testing Strategy)
```

## Navigation

| Step | Title | Depends on | Key deliverable |
|------|-------|------------|-----------------|
| 01 | Product Overview and Gap Analysis | — | Gap matrix showing where AI adds value vs where rules suffice |
| 02 | Enriched Decision Reasons | 01 | Updated `decisionReason` templates incorporating match-specific data |
| 03 | Adjudication Data Model | 01 | Pydantic structured output schema for LLM adjudication |
| 04 | Adjudication Prompt Design | 03 | System/user prompts with safety guardrails |
| 05 | AI Adjudication Node | 03, 04 | Node behavior: filtering, batching, applying LLM suggestions |
| 06 | Cross-Pattern Detection (Deterministic) | 05 | Cluster detection, DOI prefix analysis, self-citation anomaly, temporal checks |
| 07 | Cross-Pattern LLM Analysis | 05, 06 | Document-level LLM call for systematic fabrication detection |
| 08 | Graph Topology Update | 05, 06, 07 | New edges wiring `classify_results -> cross_patterns -> ai_adjudicate -> assemble_report` |
| 09 | Configuration and Feature Flags | 08 | Settings fields, env vars, feature toggles |
| 10 | Testing Strategy | All | Unit tests, integration tests, E2E validation plan |

## Implementation Phases

**Phase A — Quick Win** (Step 02): No LLM cost. Enriches existing decision reasons with candidate-specific data.

**Phase B — AI Adjudication** (Steps 03–05, 08–09): Core AI feature. One batched LLM call per job for uncertain references.

**Phase C — Cross-Reference Patterns** (Steps 06–07): One additional LLM call per document for document-level analysis.

## Acceptance Criteria by Feature

### Enriched Decision Reasons (Step 02)
- `decisionReason` for verified/likely_verified references includes specific match data (DOI, title snippet, source name)
- No LLM calls added
- All existing tests continue to pass

### AI Adjudication (Steps 03–05)
- References with `manualReviewRequired == True` receive LLM-generated analysis
- LLM can reclassify within the compatibility matrix constraints
- `decisionReason` is replaced with contextual AI reasoning for adjudicated references
- `reasonCode` is preserved from the deterministic rule (traceability)
- Feature can be disabled via configuration flag

### Cross-Reference Patterns (Steps 06–07)
- Deterministic checks flag suspicious clusters, unregistered DOI prefixes, self-citation anomalies, temporal impossibilities
- LLM receives flagged patterns and produces document-level analysis
- Pattern flags are passed as context to the adjudication node

### ResultsV1 Contract
- Zero schema changes across all phases
- Compatibility matrix validator in `schemas.py` continues to enforce valid classification/band combinations
- All existing Pydantic invariants pass
