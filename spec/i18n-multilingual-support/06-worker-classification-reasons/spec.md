# Step 06 — Worker: Translate Classification `decisionReason`

## Scope

- Catalog every classification-reason template in `apps/worker/biblio_checker_worker/langgraph/classification.py` under a `class.*` namespace and provide ES / PT / EN copies.
- Refactor every f-string in `classification.py` that produces a `decisionReason` to go through `render("class.<key>", locale, **params)`.
- Thread `locale` through the signatures of helper functions that currently build reasons (`_single_candidate_reason`, rule handlers).

**Out of scope:** Warning-message templates (Step 07). Structured logs (stay English). Changes to classification *logic* — only the *string-building* changes.

## Context

`classification.py` has 11 deterministic rules (DOI exact match, DOI conflict, cross-source conflict, strong metadata match, weak metadata match, ambiguous multi-candidate, not-found, suspicious patterns, …) and a helper `_single_candidate_reason` used by a subset of those rules. Every rule today constructs a Spanish `decisionReason` via f-strings. A full inventory of the affected lines (from grep of `classification.py`):

| Line | Current literal start |
|------|-----------------------|
| 52 | `f"Coincidencia del {score_str}% con '{title_snippet}' en {source}."` |
| 54 | `f"Coincidencia del {score_str}% en {source}."` |
| 136 | `f"El DOI {doi} coincide con"` (multi-line concat for multi-candidate) |
| 141 | `f"El DOI {doi} coincide con '{_title_snip}' en {_src}."` |
| 145 | `f"El DOI {doi} coincide con"` (variation) |
| 149 | `f"El DOI {doi} coincide con un registro en {_src}."` |
| 240 | `f"El DOI {doi} apunta a"` (DOI conflict, multi-line) |
| 247–277 | Several `El DOI {doi} apunta a ...` variants |
| 349 | `f"Se encontraron coincidencias en {_source_a} y {_source_b}, ..."` |
| 413 | `f"Se encontraron {len(plausible)} candidatos. Los mejores: ..."` |

Re-read the file in full during implementation and capture any other Spanish literal reached by a `decisionReason` assignment.

## Requirements

### 1. Catalog Keys

Register the following keys. Use `biblio_checker_worker.langgraph.i18n.register()` calls in a new sub-module `apps/worker/biblio_checker_worker/langgraph/i18n_catalog/classification.py` that is imported by `i18n.py` (or imported from the top of `classification.py`). Keep all three locales in the same call so copy drift is obvious.

**Base set (derive final key list from the live file — this is the minimum):**

| Key | Placeholders | Usage |
|-----|--------------|-------|
| `class.match.single.with_title` | `{score}`, `{title}`, `{source}`, `{suffix}` | `_single_candidate_reason` — candidate with a title |
| `class.match.single.no_title` | `{score}`, `{source}`, `{suffix}` | `_single_candidate_reason` — candidate without a title |
| `class.doi_match.single.with_title` | `{doi}`, `{title}`, `{year}`, `{source}` | Rule 1 — exact DOI match, one candidate with title |
| `class.doi_match.single.no_title` | `{doi}`, `{source}` | Rule 1 — exact DOI match, one candidate without title |
| `class.doi_match.multi` | `{doi}`, `{sources}` | Rule 1 — DOI matches in multiple sources |
| `class.doi_conflict.title_known` | `{doi}`, `{matched_title}`, `{ref_title}` | Rule 3 — DOI conflict, both titles known |
| `class.doi_conflict.title_unknown_matched` | `{doi}`, `{matched_title}` | Rule 3 — only the matched title is known |
| `class.doi_conflict.title_unknown_ref` | `{doi}`, `{ref_title}` | Rule 3 — only the reference title is known |
| `class.doi_conflict.no_titles` | `{doi}` | Rule 3 — both unknown; DOI conflict of record |
| `class.cross_source_conflict` | `{source_a}`, `{source_b}`, `{conflict_detail}` | Rule 4 — contradictory metadata across sources |
| `class.strong_metadata.suffix` | — | Suffix appended to single-candidate reason for strong match |
| `class.weak_metadata.suffix` | — | Suffix for weak/ambiguous single-candidate match |
| `class.ambiguous_multi` | `{count}`, `{best}` | Rule 7 — multiple plausible candidates |
| `class.not_found` | — | Rule 8 — no candidates across any source |
| `class.suspicious.pattern_flag` | `{detail}` | Rule 9 — suspicious pattern without supporting evidence |
| `class.processing_error` | — | Rule fallback — classification could not be computed |

(Confirm the final list against `classification.py` — prefer one catalog key per distinct sentence; combine only when the difference is purely a placeholder.)

**Example translations** (illustrative; refine against the canonical Spanish text currently in the file):

```python
# apps/worker/biblio_checker_worker/langgraph/i18n_catalog/classification.py
from biblio_checker_worker.langgraph.i18n import register

register("class.match.single.with_title", {
    "es": "Coincidencia del {score} con '{title}' en {source}. {suffix}",
    "pt": "Correspondência de {score} com '{title}' em {source}. {suffix}",
    "en": "{score} match with '{title}' in {source}. {suffix}",
})

register("class.match.single.no_title", {
    "es": "Coincidencia del {score} en {source}. {suffix}",
    "pt": "Correspondência de {score} em {source}. {suffix}",
    "en": "{score} match in {source}. {suffix}",
})

register("class.doi_match.single.with_title", {
    "es": "El DOI {doi} coincide con '{title}' ({year}) en {source}.",
    "pt": "O DOI {doi} corresponde a '{title}' ({year}) em {source}.",
    "en": "DOI {doi} matches '{title}' ({year}) in {source}.",
})

register("class.doi_match.single.no_title", {
    "es": "El DOI {doi} coincide con un registro en {source}.",
    "pt": "O DOI {doi} corresponde a um registro em {source}.",
    "en": "DOI {doi} matches a record in {source}.",
})

register("class.doi_match.multi", {
    "es": "El DOI {doi} coincide con registros en {sources}.",
    "pt": "O DOI {doi} corresponde a registros em {sources}.",
    "en": "DOI {doi} matches records in {sources}.",
})

register("class.doi_conflict.title_known", {
    "es": "El DOI {doi} apunta a '{matched_title}' pero la referencia cita '{ref_title}'. La discrepancia sugiere una referencia fabricada o un DOI incorrecto.",
    "pt": "O DOI {doi} aponta para '{matched_title}' mas a referência cita '{ref_title}'. A discrepância sugere uma referência fabricada ou um DOI incorreto.",
    "en": "DOI {doi} points to '{matched_title}' but the reference cites '{ref_title}'. The discrepancy suggests a fabricated reference or an incorrect DOI.",
})

register("class.cross_source_conflict", {
    "es": "Se encontraron coincidencias en {source_a} y {source_b}, pero sus metadatos son contradictorios: {conflict_detail}.",
    "pt": "Foram encontradas correspondências em {source_a} e {source_b}, mas seus metadados são contraditórios: {conflict_detail}.",
    "en": "Matches were found in {source_a} and {source_b}, but their metadata are contradictory: {conflict_detail}.",
})

register("class.ambiguous_multi", {
    "es": "Se encontraron {count} candidatos. Los mejores: {best}.",
    "pt": "Foram encontrados {count} candidatos. Os melhores: {best}.",
    "en": "Found {count} candidates. Top matches: {best}.",
})

register("class.not_found", {
    "es": "No se encontraron candidatos en ninguna fuente.",
    "pt": "Não foram encontrados candidatos em nenhuma fonte.",
    "en": "No candidates were found in any source.",
})

register("class.strong_metadata.suffix", {
    "es": "Los metadatos coinciden con alta confianza.",
    "pt": "Os metadados correspondem com alta confiança.",
    "en": "Metadata matches with high confidence.",
})

register("class.weak_metadata.suffix", {
    "es": "La coincidencia es débil; se recomienda revisión manual.",
    "pt": "A correspondência é fraca; recomenda-se revisão manual.",
    "en": "The match is weak; manual review recommended.",
})

register("class.suspicious.pattern_flag", {
    "es": "La referencia presenta patrones sospechosos: {detail}.",
    "pt": "A referência apresenta padrões suspeitos: {detail}.",
    "en": "The reference shows suspicious patterns: {detail}.",
})

register("class.processing_error", {
    "es": "Ocurrió un error interno al procesar esta referencia.",
    "pt": "Ocorreu um erro interno ao processar esta referência.",
    "en": "An internal error occurred while processing this reference.",
})
```

Ensure the module is loaded once at process start — simplest way is to add `from biblio_checker_worker.langgraph.i18n_catalog import classification as _   # noqa: F401` at the top of `classification.py`.

### 2. Refactor `_single_candidate_reason`

Change its signature to accept a locale:

```python
def _single_candidate_reason(
    score: float,
    title: str | None,
    source: str,
    *,
    suffix_key: str,
    locale: str,
) -> str:
    title_snippet = _truncate_title(title)
    score_str = _score_pct(score)
    suffix = render(suffix_key, locale)
    if title_snippet is not None:
        return render(
            "class.match.single.with_title",
            locale,
            score=score_str,
            title=title_snippet,
            source=source,
            suffix=suffix,
        )
    return render(
        "class.match.single.no_title",
        locale,
        score=score_str,
        source=source,
        suffix=suffix,
    )
```

`suffix` is now a catalog key (`"class.strong_metadata.suffix"` or `"class.weak_metadata.suffix"`), not a literal string. Callers pass keys, not text.

### 3. Refactor Each Rule

The entry point function (`classify_reference(...)` — grep the file to confirm the exact name) already receives the evidence list and normalized fields. It must also receive `locale` and pass it down. The **minimum diff** shape is:

```python
def classify_reference(
    ...,
    locale: str,
) -> dict:
    ...
    if rule_1_doi_match:
        if len(matching_sources) == 1 and title is not None:
            reason = render(
                "class.doi_match.single.with_title",
                locale,
                doi=doi,
                title=_truncate_title(title),
                year=year or "—",
                source=src,
            )
        elif len(matching_sources) == 1:
            reason = render("class.doi_match.single.no_title", locale, doi=doi, source=src)
        else:
            reason = render("class.doi_match.multi", locale, doi=doi, sources=", ".join(matching_sources))
    ...
```

**Repeat for every rule that assembles a Spanish reason.** Do the refactor rule-by-rule so `git diff` per rule is reviewable. Keep the existing control flow untouched.

### 4. Update the Caller (`classify_results` node)

**File:** `apps/worker/biblio_checker_worker/langgraph/nodes/classify.py`

Pass `state["locale"]` to `classify_reference`:

```python
classified = classify_reference(
    ...,
    locale=state["locale"],
)
```

Fallback string at the node level (`"Ocurrió un error interno al procesar esta referencia."` — line 98) becomes:

```python
from biblio_checker_worker.langgraph.i18n import render
...
except Exception:
    classified = {
        "classification": "processing_error",
        "decisionReason": render("class.processing_error", state["locale"]),
        ...
    }
```

### 5. Year Placeholder Formatting

Some templates include `{year}`. When `year is None`, substitute `"—"` (em dash) *before* calling `render()` — do not push this logic into the template. This keeps the templates presentational only.

### 6. Lists and Sources in Templates

`{sources}` expects a pre-joined string, e.g. `"OpenAlex, SciELO"`. Build the string in Python with `", ".join(sorted(sources))` and pass it as a single placeholder. **Do not** use ICU plural syntax in worker templates — it is not supported by `str.format_map` and adds parsing complexity.

### 7. Source Names

`{source}` values (`"OpenAlex"`, `"SciELO"`, `"arXiv"`) are proper nouns and **not** translated. Pass them through verbatim.

## Acceptance Criteria

- [ ] Every f-string in `classification.py` that previously produced a Spanish `decisionReason` now calls `render("class.<key>", locale, **params)`.
- [ ] `classify_reference(...)` takes `locale: str` and threads it to every reason-building branch.
- [ ] `nodes/classify.py` passes `state["locale"]` into `classify_reference`.
- [ ] Fallback `processing_error` reason uses `render("class.processing_error", locale)`.
- [ ] The catalog module registers every key used by `classification.py` in all three locales.
- [ ] Running the worker with `locale='pt'` end-to-end produces Portuguese reasons; with `locale='en'`, English.
- [ ] Existing Spanish text is byte-identical for any reference processed with `locale='es'` (no regression).

## Unit Tests

**File:** `apps/worker/tests/test_classification_i18n.py` (new)

```python
from biblio_checker_worker.langgraph.classification import classify_reference
from biblio_checker_worker.langgraph.schemas import MatchCandidate


def _doi_match_candidate():
    return MatchCandidate(
        source="OpenAlex",
        match_type="doi_exact",
        raw_score=1.0,
        external_id="W1",
        title="Example Title",
        year=2024,
        doi="10.1/x",
        url="http://example.com",
    )


class TestDoiMatchReason:
    def test_spanish(self):
        out = classify_reference(
            candidates=[_doi_match_candidate()],
            normalized={"doi": "10.1/x", "title": "Example Title", "year": 2024},
            locale="es",
        )
        assert out["decisionReason"].startswith("El DOI 10.1/x coincide con")

    def test_portuguese(self):
        out = classify_reference(..., locale="pt")
        assert out["decisionReason"].startswith("O DOI 10.1/x corresponde a")

    def test_english(self):
        out = classify_reference(..., locale="en")
        assert out["decisionReason"].startswith("DOI 10.1/x matches")


class TestNotFoundReason:
    def test_all_locales(self):
        for loc, expected in [
            ("es", "No se encontraron candidatos en ninguna fuente."),
            ("pt", "Não foram encontrados candidatos em nenhuma fonte."),
            ("en", "No candidates were found in any source."),
        ]:
            out = classify_reference(candidates=[], normalized={}, locale=loc)
            assert out["decisionReason"] == expected
```

Extend `apps/worker/tests/test_assemble_report.py` to make sure `ResultsV1.reportLanguage` is set to the value of `locale` used by the classification (this check lives in the assemble-report node, which should read `state["locale"]` — see Step 07 for its companion change).

## Dependencies

- **Depends on:** Step 05 (i18n module + `GraphState.locale`).
- **Informs:** Step 07 (warnings share the same pattern), Step 12 (tests).
