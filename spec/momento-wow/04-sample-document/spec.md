# Step 04 — Sample Document

## Scope

This step specifies the curated sample PDF that enables zero-friction first use of Biblio Checker. It covers:
- Document content and structure
- Reference selection criteria
- Expected classification outcomes
- File hosting and delivery

This step does NOT cover:
- The UI button that triggers the sample flow (see Step 05)
- The upload, analysis, or polling flow (unchanged from existing behavior)
- Creation of additional sample documents for different scenarios

## Context

The biggest barrier to first-use is that a visitor must have an academic PDF with references ready to upload. A curated sample document eliminates this friction entirely. When the user clicks "Try with example," this pre-built PDF is fed into the standard upload flow, and the user sees a realistic analysis with a mix of verified, fabricated, and ambiguous references.

The sample document MUST be carefully curated so that the current pipeline produces a representative spread of classifications, demonstrating the product's value.

## Requirements

### 1) File Format

The sample document MUST be a valid PDF file. PDF is chosen because:
- It is the most common academic document format
- It exercises the primary extraction path (pdfminer.six)
- It is universally viewable

### 2) File Location

The sample document MUST be served as a static asset from the frontend's public directory at the path:
```
/samples/sample-references.pdf
```

This path MUST be accessible via a simple HTTP GET request from the browser (no authentication, no API route).

### 3) File Size

The sample document SHOULD be under 100 KB. It contains only text (references), no images, charts, or heavy formatting. Small size ensures fast download and minimal storage upload time.

### 4) Document Content

The document MUST contain a title section and a list of bibliographic references. The title section SHOULD identify the document as a sample for Biblio Checker.

The document MUST NOT contain a full academic paper. It is ONLY a reference list, consistent with the platform's purpose (users upload documents containing bibliographic references).

### 5) Reference Count

The document MUST contain approximately 8 references (minimum 7, maximum 10). This count is:
- Large enough to demonstrate a meaningful score distribution
- Small enough to process quickly (< 30 seconds expected pipeline time)
- Sufficient to show all classification types

### 6) Reference Mix

The references MUST be curated to produce the following approximate classification spread when processed by the current pipeline:

| Target Classification | Count | Description |
|----------------------|-------|-------------|
| `verified` | 4 | Real publications with valid DOIs that resolve in OpenAlex |
| `likely_verified` | 1 | Real publication without DOI but with strong metadata match |
| `ambiguous` | 1 | Reference with a common/generic title that matches multiple candidates |
| `not_found` | 1 | Completely fabricated reference with plausible-sounding but fake title, authors, and journal |
| `suspicious` | 1 | Real title but with incorrect DOI or conflicting metadata |

This mix is designed to produce a score comfortably inside the medium band. Applying the formula from Step 02: `eligible = 4 + 1 + 1 + 1 + 1 = 8`; `weightedSum = 4×1.0 + 1×0.75 + 1×0.25 = 5.0`; `score = round(5.0/8 × 100) = 63`. A score of 63 provides tolerance for pipeline variance — if one `verified` reference shifts to `likely_verified`, the score drops to ~59 (still medium). If one shifts to `not_found`, it drops to ~50 (still medium).

### 7) Reference Quality Criteria

**Verified references** MUST:
- Use real, currently resolvable DOIs
- Have correct author names, year, and venue
- Be from well-indexed sources (OpenAlex preferred)

**Fabricated references** MUST:
- Use plausible but non-existent author names
- Use plausible but non-existent journal names
- Use realistic years (2015-2024)
- NOT use real DOIs
- Be convincing enough to demonstrate the "deep fake" problem

**Suspicious reference** MUST:
- Use a real, verifiable title
- Attach an incorrect DOI (belonging to a different paper) or conflicting metadata (wrong year, wrong author)
- Demonstrate how the system detects metadata inconsistencies

### 8) Language

The references MUST be in English. English references have the widest coverage across OpenAlex, arXiv, and other indexed sources, ensuring consistent classification results.

### 9) Stability

The sample document's references MUST be chosen for classification stability. This means:
- Verified references use DOIs from long-established publications (not recent preprints that may be re-indexed)
- Fabricated references use sufficiently unique fake names to avoid accidental matches
- The expected classification outcomes SHOULD remain stable across pipeline updates

If the pipeline changes significantly (new search strategies, different scoring), the sample document MAY need to be updated.

## Acceptance Criteria

- The file exists at `/samples/sample-references.pdf` in the frontend public directory
- The file is a valid PDF readable by standard PDF viewers
- The file is under 100 KB
- The file contains 7-10 bibliographic references (target: 8)
- When processed by the current pipeline, the results include at least 4 distinct classification types
- The resulting Authenticity Score falls in the `medium` band (50-79), target ~63
- All "verified" references (4) have DOIs that currently resolve in OpenAlex
- All "fabricated" references do not match any indexed publication

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| OpenAlex changes indexing of a verified reference | Reference may shift to `likely_verified`; score changes slightly but stays in medium band |
| Pipeline adds new search strategies | Some `not_found` references might become `ambiguous`; sample may need updating |
| User re-analyzes the sample multiple times | Results SHOULD be identical (deterministic pipeline) |
| Sample PDF is corrupted during deployment | Frontend fetch returns non-PDF; error handling in Step 05 catches this |

## Integration Points

- Step 05 (Sample Document Integration) references this file to wire up the "Try with example" button
- The file is consumed by the standard upload flow (signed URL → Supabase Storage → backend → worker)

## Dependencies

- None (foundational step)
- The reference selection depends on the current state of OpenAlex, arXiv, and SciELO indices
