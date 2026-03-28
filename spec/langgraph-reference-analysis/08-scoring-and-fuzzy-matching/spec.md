# Step 08 — Scoring and Fuzzy Matching

## Scope

- Implement fuzzy title matching utility
- Implement author name matching utility
- Define a composite scoring function that combines title and author similarity
- Populate `raw_score` on `MatchCandidate` objects from API clients

**Out of scope:** Classification decisions (Step 09). API client implementation (Step 07). Evidence assembly (Step 10).

## Context

API clients (Step 07) return `MatchCandidate` objects from title-based searches with `raw_score=0.0` (because APIs don't always provide relevance scores). The scoring module computes similarity between the reference's normalized metadata and each candidate's metadata to produce a meaningful `raw_score` (0.0–1.0).

This score is used by the classification engine (Step 09) to determine whether a match is strong enough to classify as `likely_verified`, `ambiguous`, etc.

## Requirements

### 1. Scoring Module — `langgraph/scoring.py`

**File:** `apps/worker/biblio_checker_worker/langgraph/scoring.py`

### 2. Title Similarity

```python
def title_similarity(title_a: str | None, title_b: str | None) -> float:
    """Compute similarity between two titles. Returns 0.0-1.0."""
```

**Algorithm:**
1. If either title is `None` or empty, return `0.0`
2. Normalize both titles:
   - Lowercase
   - Remove leading/trailing whitespace
   - Collapse multiple whitespace to single space
   - Remove common punctuation (`.`, `,`, `:`, `;`, `"`, `'`, `(`, `)`, `[`, `]`)
3. Compute similarity using `SequenceMatcher` from `difflib`:
   ```python
   from difflib import SequenceMatcher
   return SequenceMatcher(None, norm_a, norm_b).ratio()
   ```

**Note:** `SequenceMatcher` is in the Python standard library — no additional dependency needed.

### 3. Author Similarity

```python
def author_similarity(authors_a: list[str], authors_b: list[str]) -> float:
    """Compute similarity between two author lists. Returns 0.0-1.0."""
```

**Algorithm:**
1. If either list is empty, return `0.0`
2. Normalize each author name:
   - Lowercase
   - Remove punctuation (`.`, `,`)
   - Collapse whitespace
3. Compare the **first author** of each list using `SequenceMatcher`:
   - First-author match is the strongest signal (academic convention)
4. If there are multiple authors, compute a bonus:
   - Count how many authors from list A have a fuzzy match (ratio >= 0.8) in list B
   - Bonus = `matched_count / max(len(a), len(b)) * 0.3`
5. Final score = `first_author_similarity * 0.7 + bonus` (capped at 1.0)

### 4. Composite Score

```python
def compute_match_score(
    *,
    ref_title: str | None,
    ref_authors: list[str],
    ref_year: int | None,
    candidate_title: str | None,
    candidate_authors: list[str],
    candidate_year: int | None,
) -> float:
    """Compute overall similarity score between a reference and a candidate. Returns 0.0-1.0."""
```

**Algorithm:**

Weighted combination:

| Component | Weight | Computation |
|-----------|--------|-------------|
| Title | 0.55 | `title_similarity(ref_title, candidate_title)` |
| Authors | 0.30 | `author_similarity(ref_authors, candidate_authors)` |
| Year | 0.15 | `1.0` if years match exactly, `0.5` if off by 1, `0.0` otherwise. `0.0` if either year is `None`. |

```python
score = (title_weight * title_sim) + (author_weight * author_sim) + (year_weight * year_sim)
return round(min(score, 1.0), 4)
```

### 5. Score Application

The `verify_single_reference` node (Step 10) will call `compute_match_score()` to populate `raw_score` on each `MatchCandidate` that came from a title/metadata search (not DOI/identifier exact matches, which keep `raw_score=1.0`).

### 6. Score Thresholds (used by classification in Step 09)

These thresholds are defined here for reference but enforced by the classification engine:

| Threshold | Value | Meaning |
|-----------|-------|---------|
| Strong match | >= 0.85 | High confidence metadata match → `likely_verified` |
| Moderate match | 0.50 - 0.84 | Plausible candidate → `ambiguous` if multiple |
| Weak match | < 0.50 | Too dissimilar to be considered a match |

## Acceptance Criteria

- [ ] `title_similarity()` returns `float` in `[0.0, 1.0]`
- [ ] `title_similarity()` is case-insensitive and punctuation-insensitive
- [ ] `title_similarity()` returns `0.0` for `None` or empty titles
- [ ] `title_similarity()` returns `1.0` for identical titles (after normalization)
- [ ] `author_similarity()` returns `float` in `[0.0, 1.0]`
- [ ] `author_similarity()` emphasizes first-author matching (70% weight)
- [ ] `author_similarity()` returns `0.0` for empty author lists
- [ ] `compute_match_score()` returns weighted combination of title, author, and year similarity
- [ ] Year match: exact=1.0, off-by-one=0.5, other=0.0, missing=0.0
- [ ] All functions use Python standard library only (no extra dependencies)
- [ ] Unit tests cover: identical metadata, similar metadata, completely different, missing fields, year edge cases

## Edge Cases

| Scenario | Expected Behavior |
|----------|-------------------|
| Titles differ only in capitalization | `title_similarity` returns `1.0` |
| One title has extra subtitle after colon | Moderate similarity (e.g., 0.7-0.8) |
| Authors in different order (first-author same) | High similarity (first-author dominates) |
| Authors in different formats ("Smith, J." vs "John Smith") | Moderate similarity via `SequenceMatcher` |
| Year is `None` for both reference and candidate | Year component contributes `0.0` |
| One of the two author lists is empty | `author_similarity` returns `0.0` |

## Dependencies

- **Depends on:** Step 01 (schemas: `MatchCandidate`), Step 07 (API clients produce candidates)
- **Informs:** Step 09 (classification uses score thresholds), Step 10 (verify node applies scores)
