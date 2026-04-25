# Step 02 — Enriched Decision Reasons (Phase A — Quick Win)

## Scope

- Enrich `decisionReason` template strings in the classification engine with match-specific data
- Incorporate candidate metadata (DOI, title snippet, source, year) into human-readable explanations
- No LLM calls added, no schema changes

**Out of scope:** AI adjudication (Steps 03–05). Cross-reference patterns (Steps 06–07). Changing classification logic or thresholds.

## Context

The classification engine in `classification.py` returns `decisionReason` as a template string for each rule. These strings are generic — they describe the rule that fired but include almost no data about the specific reference or match. For example:

- Rule 1: `"El DOI coincide exactamente con un registro canónico en {source}."`
- Rule 5: `"Se encontró una coincidencia fuerte por título y autores en {source}, aunque sin identificador canónico."`
- Rule 8: `"No se encontraron coincidencias en ninguna fuente consultada (OpenAlex, SciELO, arXiv, Open Library)."`

These messages are functional but miss the opportunity to provide the user with specific, actionable information about what was found.

## Requirements

### 1. Enrichment Rules per Classification

Each rule's `decisionReason` must incorporate data from the best-matching candidate (when one exists). The `classify_reference` function already receives `candidates: list[MatchCandidate]` and `normalized: dict`, so all necessary data is available.

#### 1.1 Rule 1 — Exact DOI Match (`verified`)

**Current:** `"El DOI coincide exactamente con un registro canónico en {source}."`

**Enriched:** Must include:
- The DOI value
- The matched title (truncated to 80 characters if longer, with ellipsis)
- The matched year (if available)
- The source name

**Format:** `"El DOI {doi} coincide con '{title_snippet}' ({year}) en {source}."`

If year is null, omit the year parenthetical. If title is null, omit the title snippet.

#### 1.2 Rule 2 — Exact Identifier Match (`verified`)

**Current:** `"El identificador arXiv coincide exactamente con un registro en arXiv."`

**Enriched:** Must include:
- The arXiv ID value
- The matched title (truncated to 80 characters)
- The matched year (if available)

**Format:** `"El identificador arXiv {arxiv_id} coincide con '{title_snippet}' ({year}) en arXiv."`

#### 1.3 Rule 3 — DOI Conflict (`suspicious`)

**Current:** `"El DOI citado apunta a un trabajo incompatible con el título o año reportados."`

**Enriched:** Must include:
- The DOI value
- The title found in the registry vs the title in the reference
- The year found vs the year cited (if both available)
- The source

**Format:** `"El DOI {doi} apunta a '{matched_title_snippet}' ({matched_year}) en {source}, pero la referencia cita '{ref_title_snippet}' ({ref_year}). La discrepancia sugiere una referencia fabricada o un DOI incorrecto."`

When only year conflicts (not title), the message must reflect that the title matches but the year diverges, and vice versa.

#### 1.4 Rule 4 — Cross-Source Conflict (`suspicious`)

**Current:** `"Múltiples fuentes encontraron trabajos similares pero con metadatos contradictorios entre sí."`

**Enriched:** Must include:
- The source names involved in the conflict
- What specifically conflicts (year difference, DOI difference, or both)

**Format:** `"Se encontraron coincidencias en {source_a} y {source_b}, pero sus metadatos son contradictorios: {conflict_detail}."`

Where `{conflict_detail}` is one of:
- `"los años difieren ({year_a} vs {year_b})"`
- `"los DOIs difieren"`
- `"los años y DOIs difieren"`

#### 1.5 Rule 5 — Strong Metadata Match (`likely_verified`)

**Current:** `"Se encontró una coincidencia fuerte por título y autores en {source}, aunque sin identificador canónico."`

**Enriched:** Must include:
- The similarity score (as percentage, e.g., "92%")
- The matched title (truncated)
- The source name

**Format:** `"Coincidencia del {score_pct}% con '{title_snippet}' en {source}. Sin DOI ni identificador canónico para confirmar."`

#### 1.6 Rule 5b — Single Moderate Match (`ambiguous`)

**Current:** `"Se encontró un candidato con coincidencia moderada, pero no suficiente para confirmar la referencia."`

**Enriched:** Must include:
- The similarity score (as percentage)
- The matched title (truncated)
- The source name

**Format:** `"Coincidencia del {score_pct}% con '{title_snippet}' en {source}. La similitud es insuficiente para confirmar."`

#### 1.7 Rule 6 — Multiple Plausible Candidates

Rule 6 in `classification.py` has TWO branches that must be handled differently:

**Branch A — Ambiguous (top two candidates within 0.15 of each other):**

**Current:** `"Se encontraron múltiples candidatos plausibles pero ninguno es lo suficientemente concluyente."`

**Enriched:** Must include:
- The number of candidates found
- The top two candidates: title snippet + source + score

**Format:** `"Se encontraron {count} candidatos. Los mejores: '{title_1}' ({score_1}%, {source_1}) y '{title_2}' ({score_2}%, {source_2}). Ninguno es concluyente."`

**Branch B — Dominant candidate (`likely_verified`, score >= 0.85):**

This sub-branch uses the same `reasonCode: "strong_metadata_match"` as Rule 5. It must use the **same format as Rule 5** (single candidate format):

**Format:** `"Coincidencia del {score_pct}% con '{title_snippet}' en {source}. Sin DOI ni identificador canónico para confirmar."`

#### 1.8 Rules 7, 8, 9 — Not Found variants

These rules have no candidate data to enrich. Their messages remain as-is:
- Rule 7 (insufficient metadata): Keep current message
- Rule 8 (no match): Keep current message
- Rule 9 (source timeout): Keep current message

### 2. Title Truncation

When including a title in `decisionReason`:
- If the title exceeds 80 characters, truncate to 77 characters and append `"..."`
- If the title is null, omit the title entirely from the message (adjust the format string)

### 3. Score Formatting

When including a score in `decisionReason`:
- Convert from float (0.0–1.0) to integer percentage (0–100)
- Format as `"{score}%"` (e.g., `0.92` becomes `"92%"`)

### 4. Backward Compatibility

- The `decisionReason` field is typed as `str` with `min_length=1` — enriched messages must still satisfy this constraint
- No new fields are added to `classify_reference` return dict
- No changes to `classify_reference` function signature
- The function already receives `candidates` and `normalized` — no new data sources needed

## Acceptance Criteria

1. Every `decisionReason` for Rules 1–6 includes specific match data when a candidate exists
2. Title truncation at 80 characters works correctly for long titles
3. Score is displayed as integer percentage
4. Rules 7, 8, 9 messages remain unchanged (no candidate data available)
5. All existing classification tests pass (message format changes require test updates)
6. The `classify_reference` function signature does not change
7. No new imports or dependencies added beyond what `classification.py` already uses

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| Candidate has null title | Omit title snippet from message; include other data (DOI, year, source) |
| Candidate has null year | Omit year parenthetical from message |
| Both title and year are null | Fall back to current generic message format |
| Title is exactly 80 characters | No truncation needed |
| Title is 81 characters | Truncated to 77 + "..." |
| Score is 1.0 | Displayed as "100%" |
| Score is 0.5 | Displayed as "50%" |
| Rule 4 conflict involves 3+ sources | Report the two sources with the strongest conflict |
