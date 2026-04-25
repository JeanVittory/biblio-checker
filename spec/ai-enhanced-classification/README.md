# AI-Enhanced Classification — Spec Suite

## Overview

This suite specifies how to introduce meaningful AI reasoning into the bibliographic reference classification pipeline. Today the LLM is used only as a text parser (extract and normalize references); the actual verification intelligence — scoring, classification, decision — is 100% deterministic. These specs add LLM-powered adjudication for ambiguous cases, cross-reference pattern detection, and enriched human-readable explanations.

## What's Included

- **Step 01** — Product overview and gap analysis
- **Step 02** — Enriched decision reasons for deterministic rules (no LLM cost)
- **Step 03** — Adjudication data model (structured output schema)
- **Step 04** — Adjudication prompt design and safety
- **Step 05** — AI adjudication node behavior
- **Step 06** — Cross-reference pattern detection (deterministic checks)
- **Step 07** — Cross-reference LLM analysis
- **Step 08** — Graph topology update (wiring new nodes)
- **Step 09** — Configuration and feature flags
- **Step 10** — Testing strategy

## Important Notes

- **No changes to ResultsV1 schema.** All AI reasoning is expressed through existing fields (`decisionReason`, `classification`, `confidenceScore`, `confidenceBand`).
- **Deterministic rules are preserved.** Exact DOI/identifier matches remain rule-based. AI only acts on uncertain cases.
- **No code in specs.** These are functional requirements and acceptance criteria, not implementation guides.

## Using These Specs

| Audience | Start with | Focus on |
|----------|-----------|----------|
| PM | Step 01 | Product gaps and value proposition |
| Backend/Worker dev | Steps 02–09 | All implementation specs in order |
| QA | Step 10, then Steps 02–07 | Testing strategy, then acceptance criteria per step |
| Security | Steps 04, 07 | Prompt injection protection in LLM calls |

## Dependency Flow

```
01 (Overview) ──> 02 (Enriched Reasons)
                       │
                  03 (Adjudication Model)
                       │
                  04 (Prompt Design)
                       │
                  05 (Adjudication Node)
                       │
          ┌────────────┤
          v            v
   06 (Cross-Pattern   07 (Cross-Pattern
       Deterministic)      LLM Analysis)
          │            │
          └─────┬──────┘
                v
         08 (Graph Topology)
                │
                v
         09 (Configuration)
                │
                v
         10 (Testing Strategy)
```

## Implementation Phases

**Phase A — Quick Win** (Step 02): Enrich `decisionReason` templates with specific match data. Zero LLM cost. Can ship independently.

**Phase B — AI Adjudication** (Steps 03–05, 08–09): The core AI feature. Adds LLM-as-Judge for ambiguous/not_found/suspicious references.

**Phase C — Cross-Reference Patterns** (Steps 06–07): Document-level fabrication detection. Builds on Phase B.
