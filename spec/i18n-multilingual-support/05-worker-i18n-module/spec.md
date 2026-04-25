# Step 05 — Worker i18n Module and State Propagation

## Scope

- Introduce a new module `apps/worker/biblio_checker_worker/langgraph/i18n.py` that owns every translatable template the worker emits.
- Expose a `render(key, locale, **params)` function used by classification and node code (Steps 06–07).
- Add `locale` to `GraphState` and propagate it from `pipeline/stages/run_langgraph.py` to the graph.
- Update `apps/worker/biblio_checker_worker/jobs/repo.py` to read the `locale` column out of the `claim_analysis_job` RPC result.

**Out of scope:** The concrete template text for classification reasons (Step 06) and warnings (Step 07). Those steps populate the catalog this module defines.

## Context

The worker today builds user-facing strings with f-strings scattered across six files (`classification.py` + five `nodes/*.py` files). Centralising them in one module has three benefits:

1. A single place to add PT/EN copies.
2. A testable `render()` entry point with a well-defined missing-key fallback.
3. Code-review clarity — every user-facing change to copy is a diff in one module.

The module is **pure data + a tiny helper**. It must not depend on anything from `langgraph/nodes/*` or `pipeline/*` to avoid import cycles.

## Requirements

### 1. Create `apps/worker/biblio_checker_worker/langgraph/i18n.py`

```python
"""Worker-side message catalog and renderer.

This module is the single source of truth for every natural-language string the
worker emits into the final ResultsV1 payload (``decisionReason`` values on
``ReferenceResult`` and ``message`` values on ``Warning``).

Do NOT import this module from anything outside the worker. Frontend and
backend have their own catalogs.

Missing-key policy: if ``key`` is not present in the requested ``locale`` we
fall back to Spanish (``DEFAULT_LOCALE``). If it is missing there too we return
``f"[i18n:{key}]"`` and emit a structured-log warning ``i18n_missing_key`` so
QA surfaces the gap.
"""

from __future__ import annotations

from typing import Any, Literal

import structlog

logger = structlog.get_logger(__name__)

Locale = Literal["es", "pt", "en"]
LOCALES: tuple[Locale, ...] = ("es", "pt", "en")
DEFAULT_LOCALE: Locale = "es"


def normalize_locale(value: str | None) -> Locale:
    """Coerce an arbitrary string into a supported Locale.

    Region suffixes are stripped (``"es-MX"`` -> ``"es"``). Unknown values
    fall back to :data:`DEFAULT_LOCALE`. ``None`` / empty returns default.
    """
    if not value:
        return DEFAULT_LOCALE
    base = value.lower().split("-")[0]
    if base in LOCALES:
        return base  # type: ignore[return-value]
    return DEFAULT_LOCALE


# Templates are initialised as empty dicts per locale; Steps 06 and 07 populate
# the ``class.*`` and ``warn.*`` namespaces respectively.
TEMPLATES: dict[Locale, dict[str, str]] = {
    "es": {},
    "pt": {},
    "en": {},
}


def register(key: str, translations: dict[Locale, str]) -> None:
    """Register a translation bundle. Called at import time from catalog files.

    Exists so that catalog entries can be colocated with their callers' specs
    (e.g. classification.py can call ``register(...)`` near the top to declare
    the keys it uses). In practice, the initial implementation places all
    ``register()`` calls inside this module — see Steps 06/07.
    """
    for locale, text in translations.items():
        TEMPLATES[locale][key] = text


def render(key: str, locale: str | None = None, **params: Any) -> str:
    """Return the localised template for ``key`` interpolated with ``params``.

    * ``locale`` is normalised via :func:`normalize_locale`.
    * Missing keys fall back to ``DEFAULT_LOCALE``.
    * Missing in default too -> returns ``f"[i18n:{key}]"`` and logs a warning.
    * Interpolation uses :meth:`str.format_map` so extra ``params`` are ignored
      and missing ones raise ``KeyError`` (which propagates — catalog authors
      must keep placeholder lists in sync).
    """
    loc = normalize_locale(locale)
    bucket = TEMPLATES.get(loc, {})
    template = bucket.get(key)
    if template is None and loc != DEFAULT_LOCALE:
        template = TEMPLATES[DEFAULT_LOCALE].get(key)
    if template is None:
        logger.warning("i18n_missing_key", key=key, locale=loc)
        return f"[i18n:{key}]"
    try:
        return template.format_map(_SafeFormatMap(params))
    except KeyError as exc:
        logger.error("i18n_missing_param", key=key, locale=loc, param=str(exc))
        raise


class _SafeFormatMap(dict):
    """Raises KeyError on missing keys — the standard ``str.format_map`` default.

    A thin subclass is kept so we can later swap to a leniency mode (e.g. return
    ``""`` for missing params) without touching every call site.
    """
```

### 2. Add `locale` to `GraphState`

**File:** `apps/worker/biblio_checker_worker/langgraph/state.py`

Add it in the "Inputs" group:

```python
class GraphState(TypedDict):
    # --- Inputs (set once at graph invocation) ---
    job_id: str
    """UUID of the analysis job."""
    source_type: str
    """Document type: ``"pdf"`` or ``"docx"``."""
    file_bytes: bytes
    """Raw document bytes downloaded from Supabase Storage."""
    locale: str
    """User-selected locale for decisionReason/warnings rendering.
    One of ``"es" | "pt" | "en"``. Set at graph invocation; never mutated."""
    ...
```

Keep it as a plain `str` (not `Literal[...]`) because `TypedDict` with `Literal` aliases interact poorly with runtime dictionary construction in some LangGraph call sites. The `render()` helper normalises at read time, so an out-of-range value still degrades safely.

### 3. Read `locale` from the RPC

**File:** `apps/worker/biblio_checker_worker/jobs/repo.py`

Inspect the current `claim_job()` function. Wherever it destructures the RPC response, include `locale`:

```python
@dataclass
class ClaimedJob:
    job_id: str
    sha256: str
    source_type: str
    storage_path: str
    worker_lease_token: str
    locale: str     # NEW


def claim_job(...) -> ClaimedJob | None:
    row = _rpc("claim_analysis_job", {"p_worker_lease_seconds": LEASE_SECONDS})
    if row is None:
        return None
    return ClaimedJob(
        job_id=row["job_id"],
        sha256=row["sha256"],
        source_type=row["source_type"],
        storage_path=row["storage_path"],
        worker_lease_token=row["worker_lease_token"],
        locale=row.get("locale") or "es",   # defensive default for pre-migration rows
    )
```

### 4. Pass `locale` into the Graph

**File:** `apps/worker/biblio_checker_worker/pipeline/stages/run_langgraph.py`

At the invocation site, include it in the initial state:

```python
initial_state: GraphState = {
    "job_id": claimed.job_id,
    "source_type": claimed.source_type,
    "file_bytes": file_bytes,
    "locale": claimed.locale,      # NEW
    # ... other fields initialised to their defaults
}
graph.invoke(initial_state, ...)
```

### 5. Node Access Pattern

All nodes and `classification.py` that need to build a translated string do:

```python
from biblio_checker_worker.langgraph.i18n import render
...
reason = render("class.doi_match.single", state["locale"], doi=doi, title=title_snippet, year=year, source=src)
```

**For fan-out helpers (`verify_single_reference` is invoked via `Send()` with a partial state)** make sure the partial state forwarded to those sub-invocations includes `locale`. This is already natural because the partial state is a subset built from the parent `state`; just add `"locale": state["locale"]` to it.

### 6. Logging Discipline

- Structured log event names, error codes, and keys stay in English.
- Only payloads that end up in `warnings[].message` or `references[].decisionReason` go through `render()`.
- Emit a `info(..., event="i18n_render", key=..., locale=...)` log *only* if a debug flag is set — do not spam logs.

### 7. Safety: don't translate dynamic content

`render()` receives params (DOI strings, titles, years) that are **not** translatable. The caller passes them in as-is. Only the template around them changes per locale.

### 8. Concurrency

`TEMPLATES` is populated at import time and is effectively read-only thereafter. `render()` does not take locks. Tests that monkeypatch `TEMPLATES` must restore state.

## Acceptance Criteria

- [ ] `apps/worker/biblio_checker_worker/langgraph/i18n.py` exports `Locale`, `LOCALES`, `DEFAULT_LOCALE`, `normalize_locale`, `register`, `render`, `TEMPLATES`.
- [ ] `render("unknown.key", "pt")` returns `"[i18n:unknown.key]"` and logs `i18n_missing_key`.
- [ ] `render("class.doi_match.single", "pt", doi="10.1/x", title="t", year=2024, source="OpenAlex")` returns the Portuguese template with substitutions (once Step 06 populates the catalog).
- [ ] `normalize_locale("pt-BR")` → `"pt"`; `normalize_locale("fr")` → `"es"`; `normalize_locale(None)` → `"es"`; `normalize_locale("")` → `"es"`.
- [ ] `GraphState` has a `locale: str` field and every downstream node can read `state["locale"]` without `KeyError`.
- [ ] `ClaimedJob` (or the equivalent dataclass in `jobs/repo.py`) carries `locale`; `run_langgraph` stage includes it in the initial state.
- [ ] If the RPC omits `locale` (shouldn't happen after Step 02, but defensive), the worker defaults to `"es"` and still processes the job.
- [ ] No existing test regresses.

## Unit Tests

**File:** `apps/worker/tests/test_i18n.py` (new)

```python
from biblio_checker_worker.langgraph import i18n


def setup_module(module):
    i18n.register("test.simple", {"es": "hola {name}", "pt": "olá {name}", "en": "hi {name}"})
    i18n.register("test.only_es", {"es": "solo-es"})


class TestNormalizeLocale:
    def test_none(self):
        assert i18n.normalize_locale(None) == "es"

    def test_strips_region(self):
        assert i18n.normalize_locale("pt-BR") == "pt"

    def test_lowercases(self):
        assert i18n.normalize_locale("EN") == "en"

    def test_fallback_for_unknown(self):
        assert i18n.normalize_locale("fr") == "es"


class TestRender:
    def test_supported_locales(self):
        assert i18n.render("test.simple", "es", name="A") == "hola A"
        assert i18n.render("test.simple", "pt", name="A") == "olá A"
        assert i18n.render("test.simple", "en", name="A") == "hi A"

    def test_fallback_to_default(self):
        assert i18n.render("test.only_es", "pt") == "solo-es"

    def test_unknown_key_returns_placeholder(self):
        assert i18n.render("no.such.key", "es") == "[i18n:no.such.key]"

    def test_missing_param_raises(self):
        import pytest
        with pytest.raises(KeyError):
            i18n.render("test.simple", "es")   # missing {name}
```

## Dependencies

- **Depends on:** Step 02 (DB column), Step 03 (backend persists/returns `locale`).
- **Informs:** Steps 06 and 07 (catalog population), Step 12 (tests exercising each locale).
