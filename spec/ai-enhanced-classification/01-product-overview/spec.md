# Step 01 — Product Overview: Where AI Adds Value

## Scope

- Catalog where the pipeline currently uses LLM vs deterministic logic
- Identify the classification gaps where AI reasoning would improve outcomes
- Define which deterministic rules must NOT be replaced
- Establish the value proposition for each proposed AI enhancement

**Out of scope:** Implementation details (Steps 02–09). Prompt engineering (Step 04). Graph wiring (Step 08).

## Context

The Biblio Checker pipeline uses a LangGraph graph with 6 nodes. Today the LLM is called in only two places:

1. **parse_references** — splits raw text into individual reference strings
2. **normalize_references** — extracts structured metadata (title, authors, year, DOI, etc.)

The remaining nodes — verification (API queries), scoring (SequenceMatcher), classification (9 priority rules), and report assembly — are entirely deterministic. The LLM acts as a text parser, not as an evaluator. A regex-plus-API pipeline would produce nearly identical results.

The classification engine assigns one of six categories: `verified`, `likely_verified`, `ambiguous`, `not_found`, `suspicious`, `processing_error`. Three of these (`ambiguous`, `not_found`, `suspicious`) require manual review but offer no AI reasoning about *why* the reference is uncertain or *how likely* it is to be fabricated.

## Requirements

### 1. Current Pipeline AI Usage Map

| Node | Uses LLM | Purpose |
|------|----------|---------|
| extract_text | No | PDF/DOCX library parsing |
| parse_references | Yes | Split text into reference strings |
| normalize_references | Yes | Extract structured metadata |
| verify_single_reference | Minimal — one optional LLM call for cross-language title detection (`_check_title_translation` in `verify.py`), triggered only when author similarity >= 0.8 but title similarity < 0.5. Output is binary YES/NO. | Query OpenAlex, SciELO, arXiv, Open Library |
| classify_results | No | Apply 9 deterministic rules |
| assemble_report | No | Build and validate ResultsV1 payload |

### 2. Classification Rules That Must Remain Deterministic

The following rules produce high-confidence, binary outcomes where AI reasoning adds no value:

| Rule | Condition | Classification | Why deterministic is optimal |
|------|-----------|----------------|------------------------------|
| Rule 1 | Exact DOI match with consistent metadata | `verified` | DOI match is a binary fact |
| Rule 2 | Exact arXiv ID match with consistent metadata | `verified` | Identifier match is a binary fact |
| Rule 7 | No title, no DOI, no arXiv ID | `not_found` | No data to reason about |
| Rule 9 | All sources timed out, no candidates | `not_found` | Infrastructure issue, not intelligence |

### 3. Classification Gaps Where AI Adds Value

| Gap | Current behavior | What AI can do |
|-----|-----------------|----------------|
| **Ambiguous single match** (Rule 5b) | Labels "moderate match found" with no context | Reason about whether the candidate is the same work with citation errors vs. a different work entirely |
| **Multiple plausible candidates** (Rule 6) | Labels "multiple candidates, none conclusive" | Evaluate which candidate is most likely correct and explain why |
| **No match found** (Rule 8) | Labels "no match in any source" | Distinguish genuinely obscure/new references from fabricated ones based on plausibility of title+author+venue combination |
| **DOI conflict** (Rule 3) | Labels "DOI points to incompatible work" | Explain the specific nature of the conflict and assess fabrication likelihood |
| **Cross-source conflict** (Rule 4) | Labels "contradictory metadata across sources" | Identify which source is authoritative and why metadata diverges |
| **Document-level patterns** | Not detected at all | Detect systematic fabrication: shared fake journals, unregistered DOI prefixes, implausible author-venue combinations across multiple references |
| **Decision explanations** | Template strings with no reference-specific data | Produce natural-language reasoning citing specific evidence from the API lookups |

### 4. Value Proposition per Enhancement

#### 4.1 Enriched Decision Reasons (Phase A)

- **Cost:** Zero additional LLM calls
- **Value:** Transform generic template strings into specific, data-rich explanations
- **Example:** "El DOI coincide exactamente con un registro canónico en openalex." becomes "El DOI 10.1038/nature12373 coincide con 'Whole-genome sequence analysis...' (2013) en OpenAlex."
- **Applies to:** All classifications (verified, likely_verified, ambiguous, not_found, suspicious)

#### 4.2 AI Adjudication (Phase B)

- **Cost:** One batched LLM call per job (only for uncertain references)
- **Value:** LLM reasons about evidence and can reclassify uncertain references with natural-language justification
- **Applies to:** Only references where `manualReviewRequired == True` (ambiguous, not_found, suspicious)
- **Safety:** LLM output is constrained to existing Classification enum; compatibility matrix enforces valid combinations

#### 4.3 Cross-Reference Pattern Analysis (Phase C)

- **Cost:** One LLM call per document + deterministic checks
- **Value:** Detects fabrication patterns invisible when examining references individually
- **Applies to:** The full set of classified references as a corpus

## Acceptance Criteria

1. This step produces no code changes — it is a reference document for subsequent steps
2. The gap analysis correctly reflects the current state of `classification.py` rules 1–9
3. The "must remain deterministic" list covers rules where LLM reasoning adds no value
4. Each proposed enhancement has a clear cost/value trade-off documented

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| Document where all references are `verified` | AI adjudication is skipped entirely (no uncertain refs) — zero additional LLM cost |
| Document where all references are `not_found` | All references go through AI adjudication — maximum LLM cost but also maximum value |
| Document with 150 references, 100 uncertain | Adjudication cap limits LLM processing to configurable maximum (e.g., 20) |
