# Step 07 — Worker: Translate `warnings[].message`

## Scope

- Catalog every warning-message template produced by the worker under a `warn.*` namespace, with ES / PT / EN copies.
- Refactor every `warnings[].message` literal in `apps/worker/biblio_checker_worker/langgraph/nodes/*.py` (and `graph.py`) to go through `render("warn.<key>", locale, **params)`.
- Set `ResultsV1.reportLanguage` to the active locale inside the `assemble_report` node.

**Out of scope:** Classification `decisionReason` (Step 06). Frontend warning rendering (Step 10 — the UI just shows `warnings[].message` as-is).

## Context

Warnings are structured records with shape:

```python
{
    "code": "source_timeout_partial",
    "message": "La fuente OpenAlex no respondió correctamente: timeout",
    "referenceId": "ref-3" | None,
    "details": {...} | None,
}
```

The `code` is a machine-readable enum kept in English. Only `message` is translated.

Known warning sites (from `grep "code":\s*"[a-z_]+"`):

| File | Line | Code |
|------|------|------|
| `langgraph/graph.py` | 92 | `references_truncated` |
| `langgraph/nodes/verify.py` | 201 | `source_timeout_partial` |
| `langgraph/nodes/verify.py` | 301 | `reference_verification_failed` |
| `langgraph/nodes/parse_references.py` | 58 | `empty_document` |
| `langgraph/nodes/normalize.py` | 45 | `invalid_doi_format` |
| `langgraph/nodes/normalize.py` | 65 | `invalid_arxiv_id_format` |
| `langgraph/nodes/normalize.py` | 85 | `invalid_issn_format` |
| `langgraph/nodes/normalize.py` | 205 | `normalization_count_mismatch` |
| `langgraph/nodes/cross_patterns.py` | 195–329 | multiple (self-citation, future years, suspicious DOI patterns) |

Re-scan in implementation to catch any new warning sites added after this spec was written.

## Requirements

### 1. Catalog Keys

**File:** `apps/worker/biblio_checker_worker/langgraph/i18n_catalog/warnings.py` (new)

```python
from biblio_checker_worker.langgraph.i18n import register

register("warn.references_truncated", {
    "es": "Se detectaron {total} referencias pero solo se procesaron las primeras {limit}.",
    "pt": "Foram detectadas {total} referências, mas apenas as primeiras {limit} foram processadas.",
    "en": "{total} references were detected but only the first {limit} were processed.",
})

register("warn.source_timeout_partial", {
    "es": "La fuente {source_name} no respondió correctamente: {reason}.",
    "pt": "A fonte {source_name} não respondeu corretamente: {reason}.",
    "en": "Source {source_name} did not respond correctly: {reason}.",
})

register("warn.reference_verification_failed", {
    "es": "No se pudo verificar la referencia: {reason}.",
    "pt": "Não foi possível verificar a referência: {reason}.",
    "en": "Could not verify the reference: {reason}.",
})

register("warn.empty_document", {
    "es": "El documento no contiene texto extraíble.",
    "pt": "O documento não contém texto extraível.",
    "en": "The document contains no extractable text.",
})

register("warn.invalid_doi_format", {
    "es": "El DOI '{doi}' no cumple el formato esperado y se descartó.",
    "pt": "O DOI '{doi}' não cumpre o formato esperado e foi descartado.",
    "en": "DOI '{doi}' does not match the expected format and was discarded.",
})

register("warn.invalid_arxiv_id_format", {
    "es": "El identificador arXiv '{arxiv_id}' no cumple el formato esperado y se descartó.",
    "pt": "O identificador arXiv '{arxiv_id}' não cumpre o formato esperado e foi descartado.",
    "en": "arXiv identifier '{arxiv_id}' does not match the expected format and was discarded.",
})

register("warn.invalid_issn_format", {
    "es": "El ISSN '{issn}' no cumple el formato esperado y se descartó.",
    "pt": "O ISSN '{issn}' não cumpre o formato esperado e foi descartado.",
    "en": "ISSN '{issn}' does not match the expected format and was discarded.",
})

register("warn.normalization_count_mismatch", {
    "es": "El LLM devolvió {returned} entradas normalizadas; se esperaban {expected}.",
    "pt": "O LLM retornou {returned} entradas normalizadas; esperavam-se {expected}.",
    "en": "LLM returned {returned} normalized entries; expected {expected}.",
})

# Cross-pattern warnings
register("warn.self_citation_suspected", {
    "es": "La referencia podría ser una auto-cita no reconocida.",
    "pt": "A referência pode ser uma autocitação não reconhecida.",
    "en": "The reference may be an unacknowledged self-citation.",
})

register("warn.future_year", {
    "es": "La referencia cita el año {year}, posterior al año actual ({current}).",
    "pt": "A referência cita o ano {year}, posterior ao ano atual ({current}).",
    "en": "The reference cites year {year}, which is after the current year ({current}).",
})

register("warn.suspicious_doi_pattern", {
    "es": "El DOI '{doi}' presenta un patrón atípico: {detail}.",
    "pt": "O DOI '{doi}' apresenta um padrão atípico: {detail}.",
    "en": "DOI '{doi}' shows an atypical pattern: {detail}.",
})
```

Add one line at the top of `apps/worker/biblio_checker_worker/langgraph/i18n.py` (or its `__init__`) to ensure the catalog module is imported — so `register()` runs at import time:

```python
# Triggered for side effects — populates TEMPLATES
from biblio_checker_worker.langgraph.i18n_catalog import classification as _  # noqa: F401
from biblio_checker_worker.langgraph.i18n_catalog import warnings as _w       # noqa: F401
```

### 2. Refactor Each Warning Site

**Pattern:** every appearance of a dict literal with `"code"` and a templated `"message"` becomes:

```python
from biblio_checker_worker.langgraph.i18n import render

warnings.append({
    "code": "source_timeout_partial",
    "message": render(
        "warn.source_timeout_partial",
        state["locale"],
        source_name=source_name,
        reason=safe_msg,
    ),
    "referenceId": reference_id,
    "details": {"source": source_name, "reason": safe_msg},
})
```

**Important:** keep the `code` exactly as-is; frontends and analytics key off it. Only the `message` string changes.

### 3. Nodes Without Direct State Access

Some helper functions in `nodes/normalize.py` (`_validate_doi`, `_validate_arxiv_id`, `_validate_issn`) currently return dicts with a pre-built Spanish `message`. They don't currently receive `locale`.

Two options — pick one and apply uniformly:

**Option A — add `locale` parameter to validators (recommended):**

```python
def _validate_doi(doi: str | None, locale: str) -> tuple[str | None, dict[str, Any] | None]:
    ...
    warning = {
        "code": "invalid_doi_format",
        "message": render("warn.invalid_doi_format", locale, doi=doi),
        "referenceId": None,
        "details": None,
    }
```

and pass `state["locale"]` from `normalize_references()`.

**Option B — validators return `code + params`, `normalize_references()` renders:**

```python
def _validate_doi(doi): ...
    return None, {"code": "invalid_doi_format", "params": {"doi": doi}}
# caller:
for w in partial_warnings:
    warnings.append({
        "code": w["code"],
        "message": render(f"warn.{w['code']}", state["locale"], **w["params"]),
        ...
    })
```

**Choose Option A** for this suite — it keeps the current return shape and is a smaller diff per test. Document the choice in the module docstring so future authors don't regress.

### 4. `graph.py` Truncation Warning

**File:** `apps/worker/biblio_checker_worker/langgraph/graph.py:92`

The truncation warning is emitted outside a node, at graph construction / mid-invocation. Ensure the function that emits it receives `locale` (either from `state` or threaded through the caller). Translate the message via `render("warn.references_truncated", locale, total=..., limit=...)`.

### 5. Set `reportLanguage` in the Assemble-Report Node

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/assemble_report.py` (or wherever the ResultsV1 payload is built — grep for `reportLanguage`)

Currently hardcoded to `"es"`. Change to:

```python
payload = ResultsV1(
    schemaVersion="1.0",
    reportLanguage=state["locale"],
    ...
)
```

Because Step 03 widened the Pydantic pattern to `^(es|pt|en)$`, this is now valid. Without this change, setting `locale="pt"` would produce a Portuguese report but claim `reportLanguage="es"`, breaking the contract.

### 6. Structured Logs Stay English

Structured log events (`logger.info("reference_verification_failed", ...)`) remain in English — no translation. Only the user-visible `message` field passes through `render()`.

### 7. Verify Node Fan-Out

`verify_single_reference` is invoked via `Send()` with a partial state. Ensure that partial state always includes `"locale": state["locale"]` so nested calls can render warnings.

Grep for the `Send()` call in the verify fan-out and audit the dict it constructs.

### 8. `cross_patterns.py` — Multiple Warnings

This file produces several different warning kinds (self-citation, future year, suspicious DOI pattern — see lines 195–329). Each gets its own catalog key under `warn.*`. Do not collapse them into a single generic `warn.cross_pattern` key — discrete codes make filter/translation maintenance easier.

## Acceptance Criteria

- [ ] Every `"message":` literal in worker `nodes/*.py`, `classification.py`, and `graph.py` that produces a user-facing warning has been replaced with a `render("warn.<key>", state["locale"], ...)` call.
- [ ] `warnings[].code` values are unchanged (breaking the code set would be an API break).
- [ ] `_validate_doi`, `_validate_arxiv_id`, `_validate_issn` accept `locale` and use `render()`.
- [ ] `assemble_report` node sets `reportLanguage=state["locale"]`.
- [ ] With `locale="pt"`, an uploaded empty document produces a warning with `message = "O documento não contém texto extraível."` and `code = "empty_document"`.
- [ ] Running the pipeline with `locale="es"` produces byte-identical warning messages to today for the same input.
- [ ] No structured-log event names or log payload keys were translated.

## Unit Tests

**File:** `apps/worker/tests/test_warnings_i18n.py` (new)

```python
from biblio_checker_worker.langgraph.nodes.normalize import _validate_doi, _validate_issn


class TestValidateDoiWarning:
    def test_spanish(self):
        _, warn = _validate_doi("not-a-doi", locale="es")
        assert warn["code"] == "invalid_doi_format"
        assert "no cumple el formato" in warn["message"]

    def test_portuguese(self):
        _, warn = _validate_doi("not-a-doi", locale="pt")
        assert "não cumpre o formato" in warn["message"]

    def test_english(self):
        _, warn = _validate_doi("not-a-doi", locale="en")
        assert "does not match the expected format" in warn["message"]


class TestValidateIssnWarning:
    def test_all_locales(self):
        for loc in ("es", "pt", "en"):
            _, warn = _validate_issn("bad", locale=loc)
            assert warn["code"] == "invalid_issn_format"
            assert warn["message"]  # not empty, not a placeholder
```

**File:** `apps/worker/tests/test_assemble_report.py` (extend existing)

```python
def test_report_language_reflects_locale(assemble_report_fn):
    for loc in ("es", "pt", "en"):
        state = _base_state(locale=loc)
        out = assemble_report_fn(state)
        assert out["results_v1"]["reportLanguage"] == loc
```

## Edge Cases

| Scenario | Expected |
|----------|----------|
| Warning emitted before `locale` is set in state (shouldn't happen but defensively) | `render()` normalises `None` to `es` via `normalize_locale(None)` |
| Unknown warning code added without a catalog entry | `render()` returns `"[i18n:warn.<key>]"` and logs `i18n_missing_key`; the worker still emits the warning |
| Existing payloads in the DB with `reportLanguage="es"` | Unchanged — retroactive re-rendering is explicitly out of scope |

## Dependencies

- **Depends on:** Step 05 (i18n module), Step 06 (sets precedent for classification).
- **Informs:** Step 12 (tests).
