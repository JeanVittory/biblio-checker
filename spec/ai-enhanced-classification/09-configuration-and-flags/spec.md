# Step 09 — Configuration and Feature Flags

## Scope

- Define new configuration fields in the worker Settings model
- Define corresponding environment variables
- Specify default values and validation rules
- Define feature flag behavior

**Out of scope:** Node behavior (Steps 05–07). Graph wiring (Step 08). Testing (Step 10).

## Context

The worker configuration lives in `core/config.py` as a Pydantic `Settings` model using `pydantic_settings`. Environment variables are loaded from `.env` files. The existing pattern uses typed fields with `Field()` validators and sensible defaults.

New features must be independently toggleable so they can be deployed incrementally and disabled in production if issues arise.

## Requirements

### 1. New Settings Fields

| Field | Type | Default | Validation | Env var | Description |
|-------|------|---------|------------|---------|-------------|
| `ai_adjudication_enabled` | `bool` | `True` | — | `AI_ADJUDICATION_ENABLED` | Master toggle for AI adjudication. When `False`, the `ai_adjudicate` node passes through without LLM calls |
| `ai_adjudication_max_references` | `int` | `20` | `ge=1, le=150` | `AI_ADJUDICATION_MAX_REFERENCES` | Maximum number of uncertain references to adjudicate per job. References are prioritized by lowest confidence score |
| `cross_pattern_analysis_enabled` | `bool` | `True` | — | `CROSS_PATTERN_ANALYSIS_ENABLED` | Toggle for cross-reference pattern detection AND LLM analysis. When `False`, the `analyze_cross_patterns` node passes through |
| `cross_pattern_llm_enabled` | `bool` | `True` | — | `CROSS_PATTERN_LLM_ENABLED` | Toggle for the LLM call within cross-pattern analysis. When `False`, deterministic checks still run but no LLM call is made. Only meaningful when `cross_pattern_analysis_enabled` is `True` |

### 2. Feature Flag Hierarchy

```
cross_pattern_analysis_enabled = False
  → entire cross-pattern node is pass-through (no checks, no LLM)

cross_pattern_analysis_enabled = True, cross_pattern_llm_enabled = False
  → deterministic checks run, flags produced, but no LLM analysis
  → adjudication node still receives deterministic flags as context

cross_pattern_analysis_enabled = True, cross_pattern_llm_enabled = True
  → full pipeline: deterministic checks + LLM pattern analysis

ai_adjudication_enabled = False
  → adjudication node is pass-through (no LLM calls for uncertain references)
  → cross-pattern analysis still runs if enabled (flags are produced but not consumed)

ai_adjudication_enabled = True
  → uncertain references are adjudicated with LLM
  → cross-pattern context is included in prompt if available
```

### 3. Validation Rules

1. `ai_adjudication_max_references` must be between 1 and 150 (the existing `max_references` pipeline cap)
2. No cross-field validation is needed — all flags are independent and degrade gracefully

### 4. Environment Variable File Updates

The `.env.example` file must be updated with:

```
# --- AI-Enhanced Classification ---
AI_ADJUDICATION_ENABLED=true
AI_ADJUDICATION_MAX_REFERENCES=20
CROSS_PATTERN_ANALYSIS_ENABLED=true
CROSS_PATTERN_LLM_ENABLED=true
```

Each variable must include a comment explaining its purpose.

### 5. Cost Impact Documentation

The configuration section in `.env.example` must include comments documenting the LLM cost impact:

- `ai_adjudication_enabled`: Adds 1 LLM call per job (batched, only for uncertain references)
- `cross_pattern_llm_enabled`: Adds 1 LLM call per job (only when patterns detected)
- Maximum additional LLM calls per job: 2 (one for adjudication, one for cross-pattern analysis)
- To minimize cost: disable both LLM features while keeping deterministic enrichments (Step 02)

## Acceptance Criteria

1. All four new fields are present in the `Settings` model
2. Default values match the specification
3. `ai_adjudication_max_references` has `ge=1, le=150` validation
4. Feature flags work independently — disabling one does not affect the other
5. `.env.example` is updated with all new variables and explanatory comments
6. The `Settings` model validates successfully with default values (no `.env` file needed for development)

## Edge Cases

| Scenario | Expected behavior |
|----------|-------------------|
| All features disabled | Pipeline behaves identically to pre-enhancement. No LLM calls beyond parse + normalize |
| Only adjudication enabled, cross-pattern disabled | Adjudication runs but without cross-pattern context. Still valuable — LLM reasons about individual references |
| Only cross-pattern enabled, adjudication disabled | Patterns detected and stored but not consumed. No visible effect on output (flags are internal). Useful for monitoring/logging only |
| `ai_adjudication_max_references` set to 1 | Only the single most uncertain reference is adjudicated |
| `ai_adjudication_max_references` set to 150 | All uncertain references are adjudicated (up to pipeline cap) |
