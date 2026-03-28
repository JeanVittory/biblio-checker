# Step 01 — Overview and Dependencies

## Scope

- Define the new directory structure under `langgraph/`
- Define all new dependencies to add to `pyproject.toml`
- Define all new configuration settings in `core/config.py`
- Define new environment variables and `.env.example` updates
- Define the `schemas.py` file with ResultsV1 Pydantic models (copied from backend) and internal graph models

**Out of scope:** Individual node implementations (Steps 03–11). Graph wiring (Step 13). LLM prompts (Steps 05–06).

## Context

The current `langgraph/` directory contains only `__init__.py` and `flow.py` (a stub). This step establishes the full directory structure and all foundational artifacts needed before any node can be implemented.

The ResultsV1 Pydantic models in `apps/backend/app/schemas/results.py` must be duplicated into the worker to validate graph output without cross-app imports.

## Requirements

### 1. Directory Structure

Create the following structure under `apps/worker/biblio_checker_worker/langgraph/`:

```
langgraph/
├── __init__.py              # existing — update exports
├── flow.py                  # existing — will be modified in Step 14
├── state.py                 # Step 02
├── graph.py                 # Step 13
├── schemas.py               # this step (ResultsV1 copy + MatchCandidate)
├── classification.py        # Step 09
├── scoring.py               # Step 08
├── nodes/
│   ├── __init__.py
│   ├── extract_text.py      # Step 03
│   ├── parse_references.py  # Step 05
│   ├── normalize.py         # Step 06
│   ├── verify.py            # Step 10
│   ├── classify.py          # Step 09
│   └── assemble.py          # Step 11
├── clients/
│   ├── __init__.py
│   ├── openalex.py          # Step 07
│   ├── scielo.py            # Step 07
│   ├── arxiv.py             # Step 07
│   └── llm.py               # Step 04
└── prompts/
    ├── __init__.py
    ├── parse_references.py  # Step 05
    └── normalize.py         # Step 06
```

All `__init__.py` files start empty unless a step specifies exports.

### 2. New Dependencies — `pyproject.toml`

Add to `[project.dependencies]`:

| Package | Purpose | Version constraint |
|---------|---------|-------------------|
| `langchain-anthropic` | Claude LLM integration | `>=0.3` |
| `langchain-openai` | OpenAI LLM integration | `>=0.3` |
| `langchain-core` | Base abstractions (prompts, output parsers) | `>=0.3` |
| `httpx` | Async/sync HTTP client for external APIs | `>=0.27` |
| `pdfminer.six` | PDF text extraction | `>=20221105` |
| `python-docx` | DOCX text extraction | `>=1.1` |

Already present and sufficient: `langgraph`, `structlog`, `supabase`, `pydantic-settings`.

### 3. Configuration — `core/config.py`

Add the following fields to the existing `Settings` class in `apps/worker/biblio_checker_worker/core/config.py`:

```python
from pydantic import SecretStr

# --- LLM Provider ---
llm_provider: str = "anthropic"
# Valid values: "anthropic", "openai"
# Determines which LangChain chat model class is instantiated.

anthropic_api_key: SecretStr = SecretStr("")
# Required when llm_provider="anthropic". The Anthropic API key.
# Use .get_secret_value() when passing to LLM client constructors.

openai_api_key: SecretStr = SecretStr("")
# Required when llm_provider="openai". The OpenAI API key.
# Use .get_secret_value() when passing to LLM client constructors.

llm_model: str = "claude-sonnet-4-20250514"
# The model identifier passed to the LLM provider.
# Default is Claude Sonnet; change to e.g. "gpt-4o" when using OpenAI.

llm_temperature: float = 0.0
# Temperature for LLM calls. 0.0 for deterministic output.

# --- External APIs ---
openalex_email: str = ""
# Optional. If set, included in OpenAlex requests for polite pool (higher rate limits).

api_timeout_seconds: int = 30
# Timeout for each individual HTTP request to external APIs.

# --- Text Extraction ---
max_text_chars: int = 500_000
# Maximum characters extracted from a document. Documents exceeding this raise an error.

max_references: int = 150
# Maximum number of references to process per document.
# Documents exceeding this limit will process only the first N references.

# --- Pipeline Metadata ---
pipeline_name: str = "biblio-checker"
pipeline_version: str = "0.1.0"
# Included in the ResultsV1 `pipeline` field.
```

**Note:** All field names follow snake_case convention to match existing Settings fields. pydantic-settings resolves env vars case-insensitively.

**API base URLs** are non-configurable constants defined in each client file (not in Settings):

```python
# In clients/openalex.py
OPENALEX_BASE_URL = "https://api.openalex.org"

# In clients/scielo.py
SCIELO_BASE_URL = "https://articlemeta.scielo.org/api/v1"

# In clients/arxiv.py
ARXIV_BASE_URL = "https://export.arxiv.org/api"
```

These constants are not environment-configurable. Hardcoding prevents SSRF via misconfigured base URLs.

**Validation rules:**
- If `llm_provider` is `"anthropic"`, `anthropic_api_key` MUST be non-empty
- If `llm_provider` is `"openai"`, `openai_api_key` MUST be non-empty
- `llm_provider` MUST be one of `"anthropic"`, `"openai"`
- `api_timeout_seconds` MUST be between 1 and 120
- `llm_temperature` MUST be between 0.0 and 2.0

Use a `@model_validator(mode="after")` to enforce the provider/key dependency. The validator MUST use `.get_secret_value()` for emptiness checks on `anthropic_api_key` and `openai_api_key`.

### 4. Environment Variables — `.env.example`

Add the following to `.env.example`:

```env
# --- LLM ---
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LLM_MODEL=claude-sonnet-4-20250514
LLM_TEMPERATURE=0.0

# --- External APIs ---
OPENALEX_EMAIL=
API_TIMEOUT_SECONDS=30

# --- Pipeline ---
PIPELINE_NAME=biblio-checker
PIPELINE_VERSION=0.1.0
MAX_TEXT_CHARS=500000
MAX_REFERENCES=150
```

The `.env.example` keys use SCREAMING_SNAKE_CASE because that is the conventional env var naming format. pydantic-settings maps them to the snake_case `Settings` fields case-insensitively.

### 6. Settings Factory

Add a `get_settings()` function to `apps/worker/biblio_checker_worker/core/config.py`:

```python
def get_settings() -> Settings:
    return settings
```

Where `settings` is the module-level `Settings` singleton (already instantiated at module import). This pattern allows tests to monkeypatch `get_settings` to return a modified `Settings` instance without modifying the singleton.

All nodes and clients MUST import settings via:

```python
from biblio_checker_worker.core.config import get_settings

settings = get_settings()
```

Never import the `settings` singleton directly in node code.

### 7. Schemas — `langgraph/schemas.py`

This file contains two categories of models:

#### 5a. ResultsV1 Pydantic Models (copy from backend)

Copy the complete contents of `apps/backend/app/schemas/results.py` into `apps/worker/biblio_checker_worker/langgraph/schemas.py`. This includes:
- `Classification` (StrEnum)
- `ConfidenceBand` (StrEnum)
- `ReasonCode` (StrEnum)
- `_ALLOWED_BANDS` (compatibility matrix)
- `_REQUIRED_MANUAL_REVIEW` (set)
- `NormalizedReference`, `MatchedRecord`, `EvidenceItem`, `Warning`, `CountsByClassification`, `Summary`, `Pipeline`, `ReferenceResult`, `ResultsV1` (all Pydantic models)

The copy MUST be byte-identical to the backend version at the time of implementation. Add a comment at the top:

```python
# WARNING: This file is a copy of apps/backend/app/schemas/results.py
# Any changes to the ResultsV1 contract MUST be applied to BOTH files
# in the same commit. See spec/results-contract-v1/ for the normative spec.
```

#### 5b. Internal Graph Models

Add after the ResultsV1 copy:

```python
@dataclass(frozen=True)
class MatchCandidate:
    """Standardized result from any external API search."""
    source: str          # "openalex" | "scielo" | "arxiv"
    external_id: str     # Source-specific identifier
    title: str | None
    authors: list[str]
    year: int | None
    doi: str | None
    url: str | None
    match_type: str      # "doi_exact" | "title_fuzzy" | "identifier_exact" | "metadata_partial"
    raw_score: float     # 0.0-1.0, source-specific similarity score
```

`MatchCandidate` is the uniform interface between API clients (Step 07) and the classification engine (Step 09). All three API clients MUST return `list[MatchCandidate]`.

## Acceptance Criteria

- [ ] Directory structure under `langgraph/` matches the specification (all subdirectories and `__init__.py` files created)
- [ ] All 6 new dependencies are added to `pyproject.toml` with correct version constraints
- [ ] `uv sync` completes successfully after dependency changes
- [ ] All new config fields are added to `Settings` in `core/config.py` with snake_case names, correct types, defaults, and validation
- [ ] `anthropic_api_key` and `openai_api_key` are typed as `SecretStr`; the model validator uses `.get_secret_value()` for emptiness checks
- [ ] Model validator enforces API key presence based on `llm_provider` value
- [ ] API base URLs are defined as module-level constants in their respective client files (not in Settings)
- [ ] `get_settings()` factory function is defined in `core/config.py` and returns the module-level `settings` singleton
- [ ] `.env.example` is updated with all new environment variables (SCREAMING_SNAKE_CASE)
- [ ] `schemas.py` contains an exact copy of the backend ResultsV1 models
- [ ] `schemas.py` contains the `MatchCandidate` dataclass
- [ ] Existing worker tests still pass (`pnpm test:worker`)

## Dependencies

- **Depends on:** None (this is the foundation step)
- **Informs:** All subsequent steps (02–14)
