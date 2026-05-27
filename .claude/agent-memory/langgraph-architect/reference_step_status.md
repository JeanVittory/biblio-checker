---
name: step-implementation-status
description: Which spec steps have been implemented and where (langgraph + i18n slices)
type: reference
---

## single-reference-text-check steps

- **Step 04** — Worker text mode: `AnalysisJob` extended (input_kind, raw_reference_text, nullable file fields), `JobContext.raw_reference_text`, `extract_stage` branched, `run_langgraph_stage` branched, `start_text_analysis_flow` added as separate compiled subgraph, `GraphState.file_bytes`/`source_type` made NotRequired, normalize+adjudicate prompts hardened with `<reference>` delimiters, tests in `tests/test_text_mode.py`.

## langgraph-reference-analysis steps

All implemented in `apps/worker/biblio_checker_worker/langgraph/`.

## i18n-multilingual-support steps (worker slice)

- **Step 05** — Worker i18n module: `langgraph/i18n.py`, `langgraph/i18n_catalog/__init__.py`. `AnalysisJob.locale` added. `flow.py` threads locale. `GraphState.locale` added.
- **Step 06** — Classification i18n: `langgraph/i18n_catalog/classification.py`, `langgraph/classification.py` refactored, `nodes/classify.py` passes locale.
- **Step 07** — Warning i18n: `langgraph/i18n_catalog/warnings.py`, `nodes/normalize.py` (_validate_doi/arxiv_id/issn accept locale), `nodes/verify.py`, `nodes/parse_references.py`, `graph.py` fan_out_verify, `nodes/assemble.py` (reportLanguage from locale).

## Tests added (i18n slice)

- `tests/test_i18n.py` — normalize_locale, render, security (CWE-134)
- `tests/test_classification_i18n.py` — DOI match ES/PT/EN, not_found ES/PT/EN, snapshot
- `tests/test_warnings_i18n.py` — _validate_doi/_validate_issn/_validate_arxiv_id locale
- `tests/test_assemble_report.py` — extended with `test_report_language_reflects_locale`
- `tests/test_i18n_integration.py` — end-to-end with locale='pt' checks PT markers, no ES

## Key design decisions

- `_SafeFormatter` (CWE-134): blocks `{field.attr}` traversal; `render()` fails-soft to `[i18n:key]`
- Catalog imports at the BOTTOM of `i18n.py` with `# noqa: E402, I001` to avoid circular import
- `ResultsV1.reportLanguage` widened to `^(es|pt|en)$` in `schemas.py`
- `AnalysisJob.locale` has `_FIELDS` whitelist entry; `from_row()` uses `filtered.get("locale") or "es"`
