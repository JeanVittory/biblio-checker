"""End-to-end integration test: locale='pt' produces Portuguese output (Step 05-07)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from biblio_checker_worker.jobs.models import AnalysisJob
from biblio_checker_worker.langgraph.prompts.normalize import (
    NormalizedFields,
    NormalizedReferenceEntry,
    NormalizeReferencesOutput,
)
from biblio_checker_worker.langgraph.prompts.parse_references import (
    ParsedReference,
    ParseReferencesOutput,
)
from biblio_checker_worker.langgraph.schemas import MatchCandidate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(locale: str = "es") -> AnalysisJob:
    return AnalysisJob(
        id="test-job-i18n",
        status="claimed",
        stage="LANGGRAPH_RUNNING",
        bucket="uploads",
        path="test/file.pdf",
        sha256="abc123",
        source_type="pdf",
        attempts=1,
        max_attempts=3,
        locale=locale,
        job_token="tok-test",
    )


def _make_settings(**kwargs: Any) -> MagicMock:
    s = MagicMock()
    s.pipeline_name = "biblio-checker"
    s.pipeline_version = "0.1.0"
    s.max_references = kwargs.get("max_references", 150)
    s.max_text_chars = 500_000
    s.job_lease_seconds = 300
    s.api_timeout_seconds = 30
    s.openalex_email = ""
    s.cross_pattern_analysis_enabled = False
    s.cross_pattern_llm_enabled = False
    s.ai_adjudication_enabled = False
    return s


def _make_candidate_no_doi(
    source: str = "openalex",
    title: str = "A Title About Science",
    year: int = 2022,
) -> MatchCandidate:
    """Return a fuzzy-match candidate (no DOI) so we exercise Rule 5."""
    return MatchCandidate(
        source=source,
        external_id="W999",
        title=title,
        authors=["Author A"],
        year=year,
        doi=None,
        url=None,
        match_type="title_fuzzy",
        raw_score=0.9,
    )


def _invoke_locale(
    *,
    locale: str,
    raw_text: str = "Reference 1. Author A. A Title About Science. 2022.",
) -> dict:
    """Invoke the full graph pipeline with a given locale and minimal stubs."""
    raw_texts = [raw_text]
    parse_output = ParseReferencesOutput(
        references=[ParsedReference(raw_text=t) for t in raw_texts]
    )
    normalize_output = NormalizeReferencesOutput(
        references=[
            NormalizedReferenceEntry(
                index=0,
                normalized=NormalizedFields(
                    title="A Title About Science",
                    authors=["Author A"],
                    year=2022,
                    venue="Journal Y",
                    doi=None,
                    arxiv_id=None,
                ),
            )
        ]
    )
    candidate = _make_candidate_no_doi()
    _settings = _make_settings()
    job = _make_job(locale=locale)
    file_bytes = b"%PDF-1.4 test"

    import biblio_checker_worker.langgraph.flow as flow_module  # noqa: PLC0415

    flow_module._compiled_graph = None

    def _get_llm_factory() -> MagicMock:
        llm = MagicMock()

        def _with_structured_output(schema: type) -> MagicMock:
            s = MagicMock()
            name = getattr(schema, "__name__", "")
            if "Parse" in name:
                s.invoke = MagicMock(return_value=parse_output)
            else:
                s.invoke = MagicMock(return_value=normalize_output)
            return s

        llm.with_structured_output.side_effect = _with_structured_output
        return llm

    with (
        patch(
            "biblio_checker_worker.langgraph.nodes.extract_text.get_settings",
            return_value=_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.graph.get_settings",
            return_value=_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.flow.get_settings",
            return_value=_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.verify.get_settings",
            return_value=_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.assemble.get_settings",
            return_value=_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings",
            return_value=_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.ai_adjudicate.get_settings",
            return_value=_settings,
        ),
        patch("pdfminer.high_level.extract_text", return_value=raw_text),
        patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            side_effect=_get_llm_factory,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            side_effect=_get_llm_factory,
        ),
        patch("biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient") as mock_oa,
        patch("biblio_checker_worker.langgraph.nodes.verify.ScieloClient") as mock_sc,
        patch("biblio_checker_worker.langgraph.nodes.verify.ArxivClient") as mock_ar,
        patch(
            "biblio_checker_worker.langgraph.nodes.verify.renew_lease_if_needed",
            return_value=False,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.assemble.renew_lease_if_needed",
            return_value=False,
        ),
        patch("biblio_checker_worker.langgraph.flow.init_lease_context"),
        patch("biblio_checker_worker.langgraph.flow.clear_lease_context"),
    ):
        mock_oa.return_value.search.return_value = [candidate]
        mock_sc.return_value.search.return_value = []
        mock_ar.return_value.search.return_value = []

        from biblio_checker_worker.langgraph.flow import (  # noqa: PLC0415
            start_analysis_flow,
        )

        return start_analysis_flow(job=job, file_bytes=file_bytes, supabase=None)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestLocaleEndToEnd:
    def test_portuguese_locale_produces_pt_decision_reason(self) -> None:
        """With locale='pt', at least one decisionReason must contain PT substrings."""
        result = _invoke_locale(locale="pt")

        assert result["reportLanguage"] == "pt"
        references = result["references"]
        assert len(references) >= 1

        reasons = [r["decisionReason"] for r in references]
        # At least one reason must contain a Portuguese marker
        pt_markers = (
            "corresponde",
            "não",
            "Não",
            "Correspondência",
            "candidatos",
            "Foram",
            "fonte",
            "Sem",
        )
        has_pt = any(
            any(marker in reason for marker in pt_markers) for reason in reasons
        )
        assert has_pt, f"No PT substring found in reasons: {reasons}"

    def test_portuguese_locale_no_es_substrings(self) -> None:
        """With locale='pt', decisionReasons must NOT contain ES-only substrings."""
        result = _invoke_locale(locale="pt")
        references = result["references"]
        reasons = [r["decisionReason"] for r in references]

        es_only = ("coincide", "ninguna", "Ninguna", "Coincidencia")
        for reason in reasons:
            for es_word in es_only:
                assert es_word not in reason, (
                    f"ES word {es_word!r} found in PT reason: {reason!r}"
                )

    def test_english_locale_report_language(self) -> None:
        """With locale='en', reportLanguage must be 'en'."""
        result = _invoke_locale(locale="en")
        assert result["reportLanguage"] == "en"

    def test_spanish_default_locale(self) -> None:
        """With locale='es', reportLanguage must be 'es'."""
        result = _invoke_locale(locale="es")
        assert result["reportLanguage"] == "es"

    def test_defensive_missing_locale_defaults_to_es(self) -> None:
        """AnalysisJob with no locale in row (pre-migration) defaults to 'es'."""
        row = {
            "id": "test-job-x",
            "status": "claimed",
            "stage": "created",
            "bucket": "uploads",
            "path": "file.pdf",
            "sha256": "abc",
            "source_type": "pdf",
            "attempts": 1,
            "max_attempts": 3,
            # "locale" key intentionally absent
        }
        job = AnalysisJob.from_row(row)
        assert job.locale == "es"
