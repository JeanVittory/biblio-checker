# Step 06 — Cross-Reference Pattern Detection (Deterministic)

## Scope

- Define deterministic checks that analyze the full set of classified references as a corpus
- Specify the data structure for pattern flags
- Define how detected patterns are stored in graph state for consumption by the LLM analysis node (Step 07) and adjudication node (Step 05)

**Out of scope:** LLM analysis of patterns (Step 07). Adjudication logic (Step 05). Graph wiring (Step 08).

**Important:** Steps 06 and 07 both describe behavior that lives inside the **single** `analyze_cross_patterns` node function, registered at module path `langgraph.nodes.cross_patterns` (see Step 08). Step 06 covers the deterministic checks that run first. Step 07 covers the optional LLM analysis that runs second within the same node. They are NOT separate nodes.

## Context

When examining references one at a time, certain fabrication patterns are invisible. A single `not_found` reference might be a legitimately obscure paper. But five `not_found` references that all cite the same journal — a journal that doesn't appear in any database — is a strong indicator of systematic fabrication.

These patterns are detectable with deterministic checks (no LLM needed). The results feed into the LLM analysis in Step 07 and provide context for the adjudication in Step 05.

## Requirements

### 1. Node Entry Point

```
analyze_cross_patterns(state: GraphState) -> dict
```

Reads `classified_references` from state. Returns `{"cross_reference_analysis": {...}}`.

### 2. Pattern Checks

The node must perform the following checks, in order:

#### 2.1 Suspicious Venue Cluster

**Condition:** Three or more references classified as `not_found` share the same normalized venue name.

**Normalization:** Venue names are compared after:
- Converting to lowercase
- Removing leading/trailing whitespace
- Removing punctuation (periods, commas)
- Collapsing multiple spaces to one

**Output flag:**
```
{
    "type": "suspicious_venue_cluster",
    "venue": "{normalized_venue_name}",
    "reference_ids": ["{id_1}", "{id_2}", "{id_3}", ...],
    "count": {N},
    "message": "{N} referencias no encontradas citan la misma revista: '{venue}'."
}
```

#### 2.2 Unregistered DOI Prefix Cluster

**Condition:** Two or more references classified as `not_found` or `suspicious` share the same DOI prefix (the `10.XXXX` portion before the first `/`), AND none of the `verified` or `likely_verified` references in the document use that same prefix.

**Rationale:** If a DOI prefix appears only in unverified references and never in verified ones, it may be a fabricated prefix.

**Output flag:**
```
{
    "type": "unregistered_doi_prefix",
    "doi_prefix": "{prefix}",
    "reference_ids": ["{id_1}", "{id_2}", ...],
    "count": {N},
    "message": "El prefijo DOI '{prefix}' aparece en {N} referencias no verificadas y en ninguna verificada."
}
```

#### 2.3 Self-Citation Anomaly

**Condition:** A single normalized last name appears in more than 40% of all references in the document.

**Author normalization:** Compare last names only (the last word in each author string), lowercased.

**Output flag:**
```
{
    "type": "self_citation_anomaly",
    "dominant_author": "{last_name}",
    "percentage": {N},
    "reference_ids": ["{id_1}", "{id_2}", ...],
    "message": "El autor '{last_name}' aparece en {N}% de las referencias, lo que puede indicar autocitas excesivas."
}
```

**Note:** Self-citation is not inherently suspicious — it is flagged as an observation, not as evidence of fabrication. The LLM analysis in Step 07 determines whether the pattern is concerning in context.

#### 2.4 Temporal Impossibility

**Condition:** A reference cites a year in the future (relative to the current date) OR a reference cites a year that predates its venue's known founding (this second check is optional and only applies if venue founding data is available from API candidates).

**Future year check:** Compare `normalized.year` against the current year. If `year > current_year`, flag it.

**Testability:** The `current_year` value must be injectable (e.g., as a parameter with a default of `datetime.now().year`) so tests can assert deterministic behavior without depending on real system time.

**Output flag:**
```
{
    "type": "temporal_impossibility",
    "reference_id": "{id}",
    "year": {year},
    "reason": "future_year" | "venue_predates",
    "message": "La referencia cita el año {year}, que es posterior al año actual."
}
```

### 3. Output Structure

The `cross_reference_analysis` dict has this shape:

```
{
    "flags": [
        { "type": "...", ... },
        { "type": "...", ... }
    ],
    "total_flags": {N},
    "analyzed_references": {total_count}
}
```

If no patterns are detected, the output is:

```
{
    "flags": [],
    "total_flags": 0,
    "analyzed_references": {total_count}
}
```

### 4. Performance Considerations

- All checks are O(N) or O(N^2) at worst (venue cluster is N references × string normalization)
- With a maximum of 150 references, this is negligible
- No API calls or LLM calls — purely in-memory computation

### 5. Handling Empty or Small Reference Lists

| References count | Behavior |
|-----------------|----------|
| 0 references | Return empty flags, `analyzed_references: 0` |
| 1 reference | Skip venue cluster check (need >= 3). Skip DOI prefix check (need >= 2). Self-citation not meaningful. Only temporal check applies |
| 2 references | Skip venue cluster check. DOI prefix and temporal checks apply |
| 3+ references | All checks apply |

## Acceptance Criteria

1. Venue cluster detection correctly normalizes venue names and requires 3+ matches among `not_found` references
2. DOI prefix cluster correctly extracts the `10.XXXX` portion and only flags prefixes absent from verified references
3. Self-citation check uses last-name normalization and the 40% threshold
4. Temporal impossibility detects future years
5. Output structure matches the specified format with `flags`, `total_flags`, `analyzed_references`
6. Empty reference list produces empty flags without errors
7. Patterns are additive — a reference can appear in multiple flags (e.g., a not_found reference with a future year AND a suspicious venue)

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| 3 `not_found` refs cite "Rev. Lit. Hispánica", "Revista de Literatura Hispánica", "Rev Lit Hisp" | After normalization, these may or may not match — the normalization (lowercase, strip punctuation) produces "rev lit hispánica", "revista de literatura hispánica", "rev lit hisp". These are different strings → NOT flagged as a cluster. Only exact normalized matches count. |
| 5 `not_found` refs share prefix 10.9999, but 1 `verified` ref also uses 10.9999 | NOT flagged — the prefix appears in a verified reference, so it is considered legitimate |
| Author "García" appears in 50 of 100 references | Flagged: 50% exceeds 40% threshold |
| Reference cites year 2027 (current year is 2026) | Flagged as `temporal_impossibility` with reason `future_year` |
| Reference has null year | Skipped for temporal check — no year to validate |
| Reference has null venue | Skipped for venue cluster check |
| All references are `verified` | No venue clusters possible (requires `not_found`), no DOI prefix flags (requires unverified refs). Self-citation and temporal checks still run. |
