# Step 03 — Backend API Contract: accept, persist, and propagate `locale`

## Scope

- Extend the `POST /api/analysis/start` request contract with an optional `locale` field.
- Persist `locale` into `analysis_jobs.locale` when creating the row.
- Widen `ResultsV1.reportLanguage` from `^es$` to `^(es|pt|en)$` in the Pydantic schema (backend) and the Zod schema (frontend) so that the report payload can legitimately declare `"pt"` or `"en"`.
- Update `apps/backend/app/services/analysis_jobs_repo.py` to insert the new column.

**Out of scope:** Translating HTTP error responses (Step 04). Worker consumption (Step 05). Frontend toggle (Step 11).

## Context

The analysis start flow today looks like:

1. `apps/frontend/app/api/analysis-start-gateway/route.ts` proxies to FastAPI.
2. `apps/backend/app/api/controllers/analysis/start.py` validates the payload and writes the row via the repo.
3. `apps/backend/app/services/analysis_jobs_repo.py` issues the INSERT.

None of these currently know about `locale`. This step threads it through without otherwise changing the flow.

## Requirements

### 1. Extend the Pydantic Request Schema

**File:** `apps/backend/app/schemas/` (locate the module that defines the start request — likely `analysis.py` or `jobs.py`). Add a `locale` field:

```python
from typing import Literal
from pydantic import BaseModel, Field

Locale = Literal["es", "pt", "en"]

class AnalysisStartRequest(BaseModel):
    sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    source_type: Literal["pdf", "docx"]
    storage_path: str
    locale: Locale = "es"       # NEW — default preserves existing behaviour
    # ... existing fields unchanged
```

**Semantics:**
- Field is **optional** from a request perspective (defaulted to `"es"`).
- Unknown values (`"fr"`, `"zh"`) **must** return HTTP 422 with Pydantic's standard validation error.
- Case and region suffixes are **not** normalised server-side: the gateway (Step 11) is responsible for sending a canonical two-letter code. If a client sends `"es-ES"`, it is rejected — document this explicitly in the OpenAPI description.

### 2. Persist `locale` in the Jobs Repo

**File:** `apps/backend/app/services/analysis_jobs_repo.py`

Find the function that inserts into `analysis_jobs` (likely `create_job` or similar). Add `locale` to the insert payload:

```python
def create_job(
    *,
    sha256: str,
    source_type: str,
    storage_path: str,
    locale: str = "es",
    # ... existing kwargs
) -> dict:
    payload = {
        "sha256": sha256,
        "source_type": source_type,
        "storage_path": storage_path,
        "locale": locale,          # NEW
        # ... existing fields
    }
    return supabase.table("analysis_jobs").insert(payload).execute().data[0]
```

Ensure any helper that reads back the job also includes `locale` in the projection (e.g. `SELECT id, sha256, ..., locale`).

### 3. Wire Through the Controller

**File:** `apps/backend/app/api/controllers/analysis/start.py`

```python
@router.post("/api/analysis/start", response_model=AnalysisStartResponse)
def start_analysis(payload: AnalysisStartRequest, ...):
    ...
    job = jobs_repo.create_job(
        sha256=payload.sha256,
        source_type=payload.source_type,
        storage_path=payload.storage_path,
        locale=payload.locale,     # NEW
        # ...
    )
    ...
```

No other controller logic changes.

### 4. Widen `ResultsV1.reportLanguage`

**File:** `apps/backend/app/schemas/results.py` (line 183 at time of writing)

Before:

```python
reportLanguage: str = Field(..., pattern=r"^es$")
```

After:

```python
reportLanguage: str = Field(..., pattern=r"^(es|pt|en)$")
```

**File:** `apps/frontend/lib/schemas/resultsV1.ts`

Mirror the change in the Zod schema (locate the corresponding `reportLanguage` definition; it currently accepts only `"es"`):

```typescript
reportLanguage: z.enum(["es", "pt", "en"]),
```

(If the current Zod schema uses a regex, replace it with `z.enum([...])` for clarity — both representations are equivalent here.)

### 5. Update the OpenAPI / docstring

The controller / router's description should mention:
- `locale` — Optional. `"es" | "pt" | "en"`. Defaults to `"es"`. Determines the language of `decisionReason` and `warnings[].message` in the final report. Immutable after creation.

### 6. `claim_analysis_job` Consumption (Backend)

Backend does not call `claim_analysis_job` directly (the worker does), but if any backend endpoint projects `locale` — e.g. a status endpoint that exposes it for debugging — add it to the response model. Otherwise, no change here.

### 7. Backwards Compatibility

- Requests that omit `locale` default to `"es"` → identical to today's behaviour.
- Existing rows with `locale = 'es'` (from Step 02's DEFAULT) render in Spanish as before.
- Any existing consumer that validates `reportLanguage == "es"` continues to pass when the worker still emits `"es"`. Relaxing the pattern is strictly additive.

### 8. Schemas Contract Sync

The SYSTEM_SPEC Results Contract v1 treats `apps/backend/app/schemas/results.py` and `apps/frontend/lib/schemas/resultsV1.ts` as **two mirrors of one canonical contract**. Any change to one must be echoed in the other in the same commit. See `CLAUDE.md` → "Results Contract v1".

If the `spec/results-contract-v1/` suite contains a concrete enumeration of allowed `reportLanguage` values, update that spec file as well in the same change.

## Acceptance Criteria

- [ ] `POST /api/analysis/start` accepts `{"locale": "pt"}` and inserts a row with `locale = 'pt'`.
- [ ] `POST /api/analysis/start` without `locale` inserts a row with `locale = 'es'`.
- [ ] `POST /api/analysis/start` with `locale = 'fr'` returns 422.
- [ ] `POST /api/analysis/start` with `locale = 'es-ES'` returns 422 (must be canonical).
- [ ] Pydantic `ResultsV1` model accepts `reportLanguage = "pt"` and `"en"` in addition to `"es"`.
- [ ] Zod `resultsV1Schema` parses `reportLanguage = "pt"` and `"en"`.
- [ ] `jobs_repo.create_job(..., locale="pt")` round-trips through the DB.
- [ ] No existing tests regress — default paths still behave exactly as before.

## Unit Tests

**File:** `apps/backend/tests/test_analysis_start.py` (or the existing contract test file — discover with `grep -rn "AnalysisStartRequest\|/api/analysis/start" apps/backend/tests`)

```python
def test_start_request_accepts_supported_locales():
    for locale in ("es", "pt", "en"):
        req = AnalysisStartRequest(
            sha256="a" * 64, source_type="pdf", storage_path="x", locale=locale
        )
        assert req.locale == locale

def test_start_request_rejects_unsupported_locale():
    with pytest.raises(ValidationError):
        AnalysisStartRequest(
            sha256="a" * 64, source_type="pdf", storage_path="x", locale="fr"
        )

def test_start_request_defaults_locale_to_es():
    req = AnalysisStartRequest(sha256="a" * 64, source_type="pdf", storage_path="x")
    assert req.locale == "es"

def test_start_request_rejects_region_suffix():
    with pytest.raises(ValidationError):
        AnalysisStartRequest(
            sha256="a" * 64, source_type="pdf", storage_path="x", locale="es-ES"
        )
```

**File:** `apps/backend/tests/test_results_schema.py`

```python
def test_report_language_allows_all_supported_locales():
    for locale in ("es", "pt", "en"):
        obj = _minimal_results_v1(report_language=locale)
        assert obj.reportLanguage == locale

def test_report_language_rejects_unknown_locale():
    with pytest.raises(ValidationError):
        _minimal_results_v1(report_language="fr")
```

## Dependencies

- **Depends on:** Step 02 (column exists)
- **Informs:** Step 05 (worker consumes `locale`), Step 11 (gateway forwards it)
