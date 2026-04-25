"""End-to-end integration tests for the LangGraph analysis pipeline.

All external dependencies (LLM calls, HTTP API clients, lease renewal) are
mocked. The real graph is compiled and invoked via ``start_analysis_flow()``
so the full node wiring, fan-out, and fan-in paths are exercised without
network access.

Test matrix:
  1. Happy path — 3 references fully verified
  2. Empty document — 0 references, warning "empty_document"
  3. API failures — one source raises httpx.TimeoutException
  4. All APIs fail for all references — "processing_error" classification
  5. LLM returns no references — valid empty ResultsV1
  6. ResultsV1 Pydantic validation — output validates against the model
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx

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
from biblio_checker_worker.langgraph.schemas import MatchCandidate, ResultsV1

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_job(source_type: str = "pdf") -> AnalysisJob:
    """Return a minimal AnalysisJob for testing."""
    return AnalysisJob(
        id="test-job-001",
        status="claimed",
        stage="LANGGRAPH_RUNNING",
        bucket="uploads",
        path="test/file.pdf",
        sha256="abc123",
        source_type=source_type,
        attempts=1,
        max_attempts=3,
        job_token="tok-test",
    )


def _make_settings(**kwargs: Any) -> MagicMock:
    """Return a Settings-like mock with sensible defaults."""
    s = MagicMock()
    s.pipeline_name = kwargs.get("pipeline_name", "biblio-checker")
    s.pipeline_version = kwargs.get("pipeline_version", "0.1.0")
    s.max_references = kwargs.get("max_references", 150)
    s.max_text_chars = kwargs.get("max_text_chars", 500_000)
    s.job_lease_seconds = kwargs.get("job_lease_seconds", 300)
    s.api_timeout_seconds = kwargs.get("api_timeout_seconds", 30)
    s.openalex_email = kwargs.get("openalex_email", "")
    return s


def _make_candidate(
    *,
    source: str = "openalex",
    external_id: str = "W001",
    title: str | None = "A Deep Learning Survey",
    authors: list[str] | None = None,
    year: int | None = 2022,
    doi: str | None = "10.1234/test.001",
    url: str | None = "https://openalex.org/W001",
    match_type: str = "doi_exact",
    raw_score: float = 1.0,
) -> MatchCandidate:
    return MatchCandidate(
        source=source,
        external_id=external_id,
        title=title,
        authors=authors or ["LeCun, Y.", "Bengio, Y."],
        year=year,
        doi=doi,
        url=url,
        match_type=match_type,
        raw_score=raw_score,
    )


def _parse_output_for_refs(raw_texts: list[str]) -> ParseReferencesOutput:
    """Build a ParseReferencesOutput with one ParsedReference per raw text."""
    return ParseReferencesOutput(
        references=[ParsedReference(raw_text=t) for t in raw_texts]
    )


def _normalize_output_for_refs(
    raw_texts: list[str],
    *,
    doi_prefix: str = "10.1234/ref",
) -> NormalizeReferencesOutput:
    """Build a NormalizeReferencesOutput with one entry per raw text."""
    entries = [
        NormalizedReferenceEntry(
            index=i,
            normalized=NormalizedFields(
                title=f"Title {i + 1}",
                authors=["Author A", "Author B"],
                year=2022,
                venue="Journal X",
                doi=f"{doi_prefix}.{i + 1:03d}",
                arxiv_id=None,
            ),
        )
        for i, _ in enumerate(raw_texts)
    ]
    return NormalizeReferencesOutput(references=entries)


# ---------------------------------------------------------------------------
# Core invocation helper
# ---------------------------------------------------------------------------


def _invoke_with_node_patches(
    *,
    raw_text: str,
    parse_output: ParseReferencesOutput,
    normalize_output: NormalizeReferencesOutput,
    openalex_candidates: list[MatchCandidate] | Exception,
    scielo_candidates: list[MatchCandidate] | Exception,
    arxiv_candidates: list[MatchCandidate] | Exception,
    settings: MagicMock | None = None,
) -> dict:
    """Run the full graph with all LLM/HTTP/lease boundaries patched.

    Compiles a fresh graph per call (resets module-level cache first) so tests
    are isolated from each other.
    """
    _settings = settings or _make_settings()
    job = _make_job()
    file_bytes = b"%PDF-1.4 test"

    # Reset the cached compiled graph so each test gets a fresh one.
    import biblio_checker_worker.langgraph.flow as flow_module  # noqa: PLC0415

    flow_module._compiled_graph = None

    def _get_llm_factory() -> MagicMock:
        """Return a fresh LLM mock whose with_structured_output dispatches by schema."""
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

    def _make_search_side_effect(result: list[MatchCandidate] | Exception):
        if isinstance(result, Exception):
            exc = result

            def _raise(**_kw: Any) -> None:
                raise exc

            return _raise
        else:

            def _return(**_kw: Any) -> list[MatchCandidate]:
                return result

            return _return

    with (
        # Settings patches across all nodes and graph/flow modules
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
        # Patch pdfminer so we don't need real PDF bytes
        patch(
            "pdfminer.high_level.extract_text",
            return_value=raw_text,
        ),
        # Patch LLM clients in parse and normalize nodes
        patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            side_effect=_get_llm_factory,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            side_effect=_get_llm_factory,
        ),
        # Patch API clients
        patch("biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient") as mock_oa,
        patch("biblio_checker_worker.langgraph.nodes.verify.ScieloClient") as mock_sc,
        patch("biblio_checker_worker.langgraph.nodes.verify.ArxivClient") as mock_ar,
        # Patch lease renewal so tests don't need Supabase
        patch(
            "biblio_checker_worker.langgraph.nodes.verify.renew_lease_if_needed",
            return_value=False,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.assemble.renew_lease_if_needed",
            return_value=False,
        ),
        # Patch lease context lifecycle in flow.py
        patch(
            "biblio_checker_worker.langgraph.flow.init_lease_context",
        ),
        patch(
            "biblio_checker_worker.langgraph.flow.clear_lease_context",
        ),
    ):
        mock_oa.return_value.search.side_effect = _make_search_side_effect(
            openalex_candidates
        )
        mock_sc.return_value.search.side_effect = _make_search_side_effect(
            scielo_candidates
        )
        mock_ar.return_value.search.side_effect = _make_search_side_effect(
            arxiv_candidates
        )

        from biblio_checker_worker.langgraph.flow import (
            start_analysis_flow,  # noqa: PLC0415
        )

        return start_analysis_flow(job=job, file_bytes=file_bytes, supabase=None)


# ---------------------------------------------------------------------------
# Test 1 — Happy path with 3 references
# ---------------------------------------------------------------------------


class TestHappyPath:
    """Full pipeline run with 3 references that all verify successfully."""

    RAW_TEXTS = [
        "LeCun, Y. (2015). Deep learning. Nature, 521, 436–444.",
        "Vaswani, A. et al. (2017). Attention is all you need. NeurIPS.",
        "Goodfellow, I. (2016). Deep Learning. MIT Press.",
    ]

    def test_three_references_verified(self) -> None:
        candidate = _make_candidate(match_type="doi_exact", raw_score=1.0)
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=[candidate],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        assert isinstance(result, dict)
        assert result["schemaVersion"] == "1.0"
        assert result["reportLanguage"] == "es"
        assert result["summary"]["totalReferencesAnalyzed"] == 3
        assert len(result["references"]) == 3

    def test_required_fields_present_on_each_reference(self) -> None:
        candidate = _make_candidate(match_type="doi_exact", raw_score=1.0)
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=[candidate],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        required_keys = {
            "referenceId",
            "rawText",
            "normalized",
            "classification",
            "confidenceScore",
            "confidenceBand",
            "manualReviewRequired",
            "reasonCode",
            "decisionReason",
            "evidence",
        }
        for ref in result["references"]:
            assert required_keys.issubset(ref.keys()), (
                f"Reference missing keys: {required_keys - ref.keys()}"
            )

    def test_summary_total_references_analyzed(self) -> None:
        candidate = _make_candidate(match_type="doi_exact", raw_score=1.0)
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=[candidate],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        assert result["summary"]["totalReferencesAnalyzed"] == 3

    def test_schema_version_and_language(self) -> None:
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        assert result["schemaVersion"] == "1.0"
        assert result["reportLanguage"] == "es"


# ---------------------------------------------------------------------------
# Test 2 — Empty document (extract produces no text)
# ---------------------------------------------------------------------------


class TestEmptyDocument:
    """Empty documents should produce a valid ResultsV1 with 0 references."""

    def test_zero_references(self) -> None:
        result = _invoke_with_node_patches(
            raw_text="",
            parse_output=ParseReferencesOutput(references=[]),
            normalize_output=NormalizeReferencesOutput(references=[]),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        assert result["summary"]["totalReferencesAnalyzed"] == 0
        assert result["references"] == []

    def test_empty_document_warning_present(self) -> None:
        result = _invoke_with_node_patches(
            raw_text="",
            parse_output=ParseReferencesOutput(references=[]),
            normalize_output=NormalizeReferencesOutput(references=[]),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        warning_codes = [w["code"] for w in result["warnings"]]
        assert "empty_document" in warning_codes

    def test_valid_results_v1_structure(self) -> None:
        result = _invoke_with_node_patches(
            raw_text="",
            parse_output=ParseReferencesOutput(references=[]),
            normalize_output=NormalizeReferencesOutput(references=[]),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        validated = ResultsV1(**result)
        assert validated.summary.totalReferencesAnalyzed == 0


# ---------------------------------------------------------------------------
# Test 3 — One API source raises TimeoutException, others succeed
# ---------------------------------------------------------------------------


class TestApiFailurePartial:
    """When one source times out, the reference is still classified using
    evidence from the remaining sources."""

    RAW_TEXTS = ["Smith, J. (2020). Attention mechanisms. AI Journal."]

    def test_reference_classified_with_partial_evidence(self) -> None:
        candidate = _make_candidate(match_type="doi_exact", raw_score=1.0)

        result = _invoke_with_node_patches(
            raw_text=self.RAW_TEXTS[0],
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=httpx.TimeoutException("timeout"),
            scielo_candidates=[candidate],
            arxiv_candidates=[],
        )

        assert result["summary"]["totalReferencesAnalyzed"] == 1
        ref = result["references"][0]
        assert ref["classification"] is not None

    def test_source_timeout_warning_present(self) -> None:
        result = _invoke_with_node_patches(
            raw_text=self.RAW_TEXTS[0],
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=httpx.TimeoutException("timeout"),
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        warning_codes = [w["code"] for w in result["warnings"]]
        assert "source_timeout_partial" in warning_codes


# ---------------------------------------------------------------------------
# Test 4 — All APIs fail for all references
# ---------------------------------------------------------------------------


class TestAllApisFail:
    """When all three sources raise connection errors for every reference, the
    classification engine receives zero candidates and assigns not_found with
    reason source_timeout_partial.  A processing_error classification is only
    produced when the verify node itself crashes (unhandled exception) — that
    is distinct from per-source error handling which the node recovers from."""

    RAW_TEXTS_TWO = [
        "Smith, J. (2020). Good paper. Journal A.",
        "Jones, K. (2019). Another paper. Journal B.",
    ]

    def test_all_references_classified_when_all_sources_fail(self) -> None:
        """All references receive a classification even when all API sources fail."""
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS_TWO),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS_TWO),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS_TWO),
            openalex_candidates=httpx.ConnectError("connection refused"),
            scielo_candidates=httpx.ConnectError("connection refused"),
            arxiv_candidates=httpx.ConnectError("connection refused"),
        )

        assert result["summary"]["totalReferencesAnalyzed"] == 2
        # Each reference must carry a non-null classification
        for ref in result["references"]:
            assert ref["classification"] is not None

    def test_source_timeout_warnings_present_when_all_sources_fail(self) -> None:
        """source_timeout_partial warnings emitted per failing source."""
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS_TWO),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS_TWO),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS_TWO),
            openalex_candidates=httpx.ConnectError("connection refused"),
            scielo_candidates=httpx.ConnectError("connection refused"),
            arxiv_candidates=httpx.ConnectError("connection refused"),
        )

        warning_codes = [w["code"] for w in result["warnings"]]
        # 2 references × 3 failing sources = 6 source_timeout_partial warnings
        assert warning_codes.count("source_timeout_partial") == 6

    def test_results_v1_valid_when_all_sources_fail(self) -> None:
        """Output must be a valid ResultsV1 even when all API calls failed."""
        result = _invoke_with_node_patches(
            raw_text="\n".join(self.RAW_TEXTS_TWO),
            parse_output=_parse_output_for_refs(self.RAW_TEXTS_TWO),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS_TWO),
            openalex_candidates=httpx.ConnectError("connection refused"),
            scielo_candidates=httpx.ConnectError("connection refused"),
            arxiv_candidates=httpx.ConnectError("connection refused"),
        )

        # Must not raise ValidationError
        validated = ResultsV1(**result)
        assert validated.summary.totalReferencesAnalyzed == 2


# ---------------------------------------------------------------------------
# Test 5 — LLM returns no references (empty parse output)
# ---------------------------------------------------------------------------


class TestLlmReturnsNoReferences:
    """When the LLM parser returns an empty list the graph should produce a
    valid empty ResultsV1 even when raw text is non-empty."""

    def test_valid_empty_results_v1(self) -> None:
        result = _invoke_with_node_patches(
            raw_text="This document has some text but no references section.",
            parse_output=ParseReferencesOutput(references=[]),
            normalize_output=NormalizeReferencesOutput(references=[]),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        assert result["summary"]["totalReferencesAnalyzed"] == 0
        assert result["references"] == []
        assert result["schemaVersion"] == "1.0"

    def test_no_empty_document_warning_for_nonempty_text(self) -> None:
        """empty_document warning is only added when raw_text is blank."""
        result = _invoke_with_node_patches(
            raw_text="Non-empty document text without a reference list.",
            parse_output=ParseReferencesOutput(references=[]),
            normalize_output=NormalizeReferencesOutput(references=[]),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        warning_codes = [w["code"] for w in result["warnings"]]
        assert "empty_document" not in warning_codes


# ---------------------------------------------------------------------------
# Test 6 — ResultsV1 Pydantic validation
# ---------------------------------------------------------------------------


class TestResultsV1Validation:
    """The output of start_analysis_flow must pass Pydantic ResultsV1
    validation in all scenarios."""

    RAW_TEXTS = ["Bengio, Y. (2013). Representation learning. TPAMI."]

    def test_pydantic_validation_passes_happy_path(self) -> None:
        candidate = _make_candidate(match_type="doi_exact", raw_score=1.0)

        result = _invoke_with_node_patches(
            raw_text=self.RAW_TEXTS[0],
            parse_output=_parse_output_for_refs(self.RAW_TEXTS),
            normalize_output=_normalize_output_for_refs(self.RAW_TEXTS),
            openalex_candidates=[candidate],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        # Must not raise ValidationError
        validated = ResultsV1(**result)
        assert validated.schemaVersion == "1.0"
        assert validated.reportLanguage == "es"

    def test_pydantic_validation_passes_for_empty_result(self) -> None:
        result = _invoke_with_node_patches(
            raw_text="",
            parse_output=ParseReferencesOutput(references=[]),
            normalize_output=NormalizeReferencesOutput(references=[]),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        validated = ResultsV1(**result)
        assert validated.summary.totalReferencesAnalyzed == 0

    def test_all_reference_ids_unique(self) -> None:
        raw_texts = [
            f"Author {i}. (202{i % 10}). Title {i}. Journal {i}." for i in range(5)
        ]

        result = _invoke_with_node_patches(
            raw_text="\n".join(raw_texts),
            parse_output=_parse_output_for_refs(raw_texts),
            normalize_output=_normalize_output_for_refs(raw_texts),
            openalex_candidates=[],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        ids = [r["referenceId"] for r in result["references"]]
        assert len(ids) == len(set(ids)), "referenceId values must be unique"

    def test_counts_by_classification_sum_equals_analyzed(self) -> None:
        candidate = _make_candidate(match_type="doi_exact", raw_score=1.0)
        raw_texts = self.RAW_TEXTS * 3  # 3 identical references

        result = _invoke_with_node_patches(
            raw_text="\n".join(raw_texts),
            parse_output=_parse_output_for_refs(raw_texts),
            normalize_output=_normalize_output_for_refs(raw_texts),
            openalex_candidates=[candidate],
            scielo_candidates=[],
            arxiv_candidates=[],
        )

        counts = result["summary"]["countsByClassification"]
        total = sum(counts[k] for k in counts)
        assert total == result["summary"]["totalReferencesAnalyzed"]
