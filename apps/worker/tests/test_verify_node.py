"""Tests for the verify_single_reference node (Step 10).

Mocks API clients and the lease renewal module so tests run without network
access. Covers: all sources succeed, one source fails, all sources fail,
no candidates found, and score computation for non-exact matches.
"""

from __future__ import annotations

from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from biblio_checker_worker.langgraph.schemas import MatchCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    *,
    source: str = "openalex",
    external_id: str = "W123",
    title: str | None = "Deep Learning for NLP",
    authors: list[str] | None = None,
    year: int | None = 2020,
    doi: str | None = None,
    url: str | None = "https://openalex.org/W123",
    match_type: str = "title_fuzzy",
    raw_score: float = 0.0,
) -> MatchCandidate:
    return MatchCandidate(
        source=source,
        external_id=external_id,
        title=title,
        authors=authors or ["Smith, Jane"],
        year=year,
        doi=doi,
        url=url,
        match_type=match_type,
        raw_score=raw_score,
    )


def _make_state(
    *,
    reference_id: str = "ref-001",
    raw_text: str = "Smith, J. (2020). Deep Learning for NLP.",
    title: str | None = "Deep Learning for NLP",
    authors: list[str] | None = None,
    year: int | None = 2020,
    doi: str | None = None,
    arxiv_id: str | None = None,
    issn: str | None = "0034-8910",
    volume: str | None = "26",
    issue: str | None = "3",
    pages: str | None = "41-72",
    publisher: str | None = None,
) -> dict:
    return {
        "job_id": "job-uuid-001",
        "reference": {
            "referenceId": reference_id,
            "rawText": raw_text,
            "normalized": {
                "title": title,
                "authors": authors or ["Smith, Jane"],
                "year": year,
                "venue": None,
                "doi": doi,
                "arxivId": arxiv_id,
                "issn": issn,
                "volume": volume,
                "issue": issue,
                "pages": pages,
                "publisher": publisher,
            },
        },
        "warnings": [],
        "verified_references": [],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent actual lease renewal during tests."""
    monkeypatch.setattr(
        "biblio_checker_worker.langgraph.nodes.verify.renew_lease_if_needed",
        lambda: None,
    )


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide dummy settings for client construction."""
    mock_settings = MagicMock()
    mock_settings.api_timeout_seconds = 5
    mock_settings.openalex_email = "test@example.com"
    monkeypatch.setattr(
        "biblio_checker_worker.langgraph.nodes.verify.get_settings",
        lambda: mock_settings,
    )


# ---------------------------------------------------------------------------
# Test: all sources succeed
# ---------------------------------------------------------------------------


class TestAllSourcesSucceed:
    def test_returns_verified_references_list(self) -> None:
        openalex_cand = _make_candidate(source="openalex", match_type="title_fuzzy")
        scielo_cand = _make_candidate(source="scielo", match_type="title_fuzzy")
        arxiv_cand = _make_candidate(source="arxiv", match_type="title_fuzzy")

        mock_openalex = MagicMock()
        mock_openalex.search.return_value = [openalex_cand]
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = [scielo_cand]
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = [arxiv_cand]

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        assert "verified_references" in result
        assert len(result["verified_references"]) == 1
        verified = result["verified_references"][0]
        assert verified["referenceId"] == "ref-001"
        assert len(verified["candidates"]) == 3
        assert verified["source_errors"] == {}

    def test_clients_are_closed_after_invocation(self) -> None:
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = []
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            verify_single_reference(_make_state())

        mock_openalex.close.assert_called_once()
        mock_scielo.close.assert_called_once()
        mock_arxiv.close.assert_called_once()

    def test_warnings_list_is_empty_when_all_succeed(self) -> None:
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = []
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        assert result["warnings"] == []


# ---------------------------------------------------------------------------
# Test: score computation applied to non-exact matches
# ---------------------------------------------------------------------------


class TestScoreComputation:
    def test_raw_score_computed_for_title_fuzzy_candidates(self) -> None:
        """Non-exact-match candidates must have raw_score set by compute_match_score."""
        candidate = _make_candidate(
            match_type="title_fuzzy",
            raw_score=0.0,  # placeholder from API client
            title="Deep Learning for NLP",
            authors=["Smith, Jane"],
            year=2020,
        )
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = [candidate]
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(
                _make_state(
                    title="Deep Learning for NLP",
                    authors=["Smith, Jane"],
                    year=2020,
                )
            )

        verified = result["verified_references"][0]
        assert len(verified["candidates"]) == 1
        stored_score = verified["candidates"][0]["raw_score"]
        # Identical title + identical author + identical year → high score
        assert stored_score > 0.80

    def test_doi_exact_match_raw_score_preserved(self) -> None:
        """Exact-match candidates must NOT have their raw_score overwritten."""
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
        )
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = [candidate]
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state(doi="10.1234/example"))

        stored_score = result["verified_references"][0]["candidates"][0]["raw_score"]
        assert stored_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test: one source fails, others continue
# ---------------------------------------------------------------------------


class TestOneSourceFails:
    def test_openalex_fails_others_continue(self) -> None:
        scielo_cand = _make_candidate(source="scielo", match_type="title_fuzzy")
        arxiv_cand = _make_candidate(source="arxiv", match_type="title_fuzzy")

        mock_openalex = MagicMock()
        mock_openalex.search.side_effect = Exception("network error")
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = [scielo_cand]
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = [arxiv_cand]

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        verified = result["verified_references"][0]
        # Only 2 candidates from the two sources that succeeded
        assert len(verified["candidates"]) == 2
        # OpenAlex recorded as error
        assert "openalex" in verified["source_errors"]
        assert verified["source_errors"]["openalex"] == "unexpected_error"
        # Warning emitted for the failed source
        assert any(w["code"] == "source_timeout_partial" for w in result["warnings"])

    def test_timeout_error_records_sanitized_message(self) -> None:
        import httpx

        mock_openalex = MagicMock()
        mock_openalex.search.side_effect = httpx.TimeoutException("timeout")
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        verified = result["verified_references"][0]
        assert verified["source_errors"]["openalex"] == "timeout"

    def test_http_status_error_records_sanitized_message(self) -> None:
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_openalex = MagicMock()
        mock_openalex.search.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=mock_response
        )
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        verified = result["verified_references"][0]
        assert verified["source_errors"]["openalex"] == "http_503"


# ---------------------------------------------------------------------------
# Test: all sources fail → processing_error
# ---------------------------------------------------------------------------


class TestAllSourcesFail:
    def test_all_sources_raise_does_not_raise(self) -> None:
        """When all three sources fail individually (per-source isolation), the node
        still returns a valid verified_references dict with source_errors populated.
        Classification (processing_error vs. not_found) is deferred to classify_results.
        """
        mock_openalex = MagicMock()
        mock_openalex.search.side_effect = Exception("openalex down")
        mock_scielo = MagicMock()
        mock_scielo.search.side_effect = Exception("scielo down")
        mock_arxiv = MagicMock()
        mock_arxiv.search.side_effect = Exception("arxiv down")

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        # Must not raise — node-level error isolation
        assert len(result["verified_references"]) == 1
        verified = result["verified_references"][0]
        # All three sources are in source_errors
        assert set(verified["source_errors"].keys()) == {"openalex", "scielo", "arxiv"}
        # Candidates list is empty (no successful lookups)
        assert verified["candidates"] == []
        # One warning emitted per failed source
        assert len(result["warnings"]) == 3

    def test_catastrophic_error_returns_processing_error_classification(
        self,
    ) -> None:
        """If renew_lease_if_needed or client construction raises, entire reference fails."""
        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.renew_lease_if_needed",
                side_effect=RuntimeError("lease error"),
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=MagicMock(),
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=MagicMock(),
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=MagicMock(),
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        assert len(result["verified_references"]) == 1
        verified = result["verified_references"][0]
        assert verified["classification"] == "processing_error"
        assert verified["confidenceScore"] is None
        assert verified["confidenceBand"] is None
        assert verified["manualReviewRequired"] is True
        assert verified["reasonCode"] == "reference_processing_failure"
        # Warning also emitted for the catastrophic failure
        assert any(
            w["code"] == "reference_verification_failed" for w in result["warnings"]
        )


# ---------------------------------------------------------------------------
# Test: new fields forwarded to client.search()
# ---------------------------------------------------------------------------


class TestNewFieldsForwarded:
    def test_issn_volume_issue_pages_publisher_passed_to_search(self) -> None:
        """All five new normalized fields must be forwarded via client.search() kwargs."""
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = []
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        state = _make_state(
            issn="0034-8910",
            volume="26",
            issue="3",
            pages="41-72",
            publisher="Elsevier",
        )

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            verify_single_reference(state)

        for mock_client in (mock_openalex, mock_scielo, mock_arxiv):
            _, kwargs = mock_client.search.call_args
            assert kwargs["issn"] == "0034-8910"
            assert kwargs["volume"] == "26"
            assert kwargs["issue"] == "3"
            assert kwargs["pages"] == "41-72"
            assert kwargs["publisher"] == "Elsevier"

    def test_none_new_fields_forwarded_as_none(self) -> None:
        """When new fields are absent from normalized, None is forwarded to search()."""
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = []
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        state = _make_state(
            issn=None, volume=None, issue=None, pages=None, publisher=None
        )

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            verify_single_reference(state)

        for mock_client in (mock_openalex, mock_scielo, mock_arxiv):
            _, kwargs = mock_client.search.call_args
            assert kwargs["issn"] is None
            assert kwargs["volume"] is None
            assert kwargs["issue"] is None
            assert kwargs["pages"] is None
            assert kwargs["publisher"] is None


# ---------------------------------------------------------------------------
# Test: no candidates found
# ---------------------------------------------------------------------------


class TestNoCandidatesFound:
    def test_no_candidates_returns_empty_candidates_list(self) -> None:
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = []
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(_make_state())

        verified = result["verified_references"][0]
        assert verified["candidates"] == []
        assert verified["source_errors"] == {}

    def test_reference_fields_preserved_in_output(self) -> None:
        mock_openalex = MagicMock()
        mock_openalex.search.return_value = []
        mock_scielo = MagicMock()
        mock_scielo.search.return_value = []
        mock_arxiv = MagicMock()
        mock_arxiv.search.return_value = []

        state = _make_state(
            reference_id="ref-abc",
            raw_text="Custom raw text for this reference.",
        )

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.OpenAlexClient",
                return_value=mock_openalex,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ScieloClient",
                return_value=mock_scielo,
            ),
            patch(
                "biblio_checker_worker.langgraph.nodes.verify.ArxivClient",
                return_value=mock_arxiv,
            ),
        ):
            from biblio_checker_worker.langgraph.nodes.verify import (
                verify_single_reference,
            )

            result = verify_single_reference(state)

        verified = result["verified_references"][0]
        assert verified["referenceId"] == "ref-abc"
        assert verified["rawText"] == "Custom raw text for this reference."
