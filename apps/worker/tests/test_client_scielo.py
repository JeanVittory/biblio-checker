from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from biblio_checker_worker.langgraph.clients.scielo import SCIELO_BASE_URL, ScieloClient
from biblio_checker_worker.langgraph.schemas import MatchCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**kwargs) -> ScieloClient:
    return ScieloClient(timeout=5, **kwargs)


def _article_fixture(
    code: str = "S0123-45672020000100001",
    title: str = "Example Article Title",
    authors: list[tuple[str, str]] | None = None,
    date: str = "20200601",
    doi: str = "10.1234/example",
) -> dict:
    if authors is None:
        authors = [("John", "Smith"), ("Jane", "Doe")]
    return {
        "code": code,
        "collection": "scl",
        "article": {
            "v12": [{"_": title}],
            "v10": [{"n": n, "s": s} for n, s in authors],
            "v65": [{"_": date}],
            "v237": [{"_": doi}],
            "v880": [{"_": code}],
        },
    }


def _mock_response(status_code: int, json_body=None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = Exception("no JSON")
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "HTTP error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# DOI lookup
# ---------------------------------------------------------------------------


class TestScieloDoiLookup:
    def test_doi_found_returns_single_candidate(self) -> None:
        article = _article_fixture()
        client = _make_client()
        with patch.object(
            client._client, "get", return_value=_mock_response(200, json_body=article)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi="10.1234/example",
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )

        assert len(results) == 1
        candidate = results[0]
        assert isinstance(candidate, MatchCandidate)
        assert candidate.source == "scielo"
        assert candidate.external_id == "S0123-45672020000100001"
        assert candidate.title == "Example Article Title"
        assert candidate.authors == ["John Smith", "Jane Doe"]
        assert candidate.year == 2020
        assert candidate.doi == "10.1234/example"
        assert candidate.match_type == "doi_exact"
        assert candidate.raw_score == 1.0
        assert "S0123-45672020000100001" in candidate.url

    def test_doi_not_found_returns_empty_list(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(404)):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi="10.9999/notfound",
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results == []

    def test_invalid_doi_format_skips_doi_lookup(self) -> None:
        """Malformed DOI skips lookup; without ISSN, returns empty."""
        client = _make_client()
        with patch.object(client._client, "get") as mock_get:
            results = client.search(
                title="Some Title",
                authors=[],
                year=None,
                doi="not-a-doi",
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        # No HTTP call should have been made (no ISSN to fall back to)
        mock_get.assert_not_called()
        assert results == []

    def test_year_extracted_from_date_string(self) -> None:
        article = _article_fixture(date="20150301")
        client = _make_client()
        with patch.object(
            client._client, "get", return_value=_mock_response(200, json_body=article)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi="10.1234/example",
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results[0].year == 2015


# ---------------------------------------------------------------------------
# ISSN search (replaces broken title search)
# ---------------------------------------------------------------------------


class TestScieloIssnSearch:
    def test_issn_search_returns_candidates(self) -> None:
        """ISSN search returns identifiers, then fetches each article."""
        identifiers_body = {
            "objects": [
                {"code": "S0034-89102000000500018", "collection": "spa"},
            ]
        }
        article = _article_fixture(code="S0034-89102000000500018")
        responses = iter(
            [
                _mock_response(200, json_body=identifiers_body),
                _mock_response(200, json_body=article),
            ]
        )
        client = _make_client()
        with patch.object(
            client._client, "get", side_effect=lambda *a, **k: next(responses)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="0034-8910",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert len(results) == 1
        assert results[0].match_type == "issn_filter"

    def test_issn_search_empty_objects_returns_empty(self) -> None:
        client = _make_client()
        with patch.object(
            client._client,
            "get",
            return_value=_mock_response(200, json_body={"objects": []}),
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="9999-9999",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results == []

    def test_issn_search_pid_not_found_skips(self) -> None:
        """A 404 on PID fetch is handled gracefully — candidate is skipped."""
        identifiers_body = {"objects": [{"code": "S_MISSING", "collection": "scl"}]}
        responses = iter(
            [
                _mock_response(200, json_body=identifiers_body),
                _mock_response(404),
            ]
        )
        client = _make_client()
        with patch.object(
            client._client, "get", side_effect=lambda *a, **k: next(responses)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="0034-8910",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results == []

    def test_no_issn_and_no_doi_returns_empty(self) -> None:
        """Without DOI or ISSN, SciELO cannot search."""
        client = _make_client()
        results = client.search(
            title="Some Title",
            authors=["Smith"],
            year=2020,
            doi=None,
            arxiv_id=None,
            issn=None,
            volume=None,
            issue=None,
            pages=None,
            publisher=None,
        )
        assert results == []

    def test_issn_search_multiple_pids_returns_all_candidates(self) -> None:
        """Multiple PIDs in identifiers response yield multiple candidates."""
        identifiers_body = {
            "objects": [
                {"code": "S0034-89102000000500018", "collection": "spa"},
                {"code": "S0034-89102000000300015", "collection": "spa"},
            ]
        }
        article1 = _article_fixture(code="S0034-89102000000500018", title="Article One")
        article2 = _article_fixture(code="S0034-89102000000300015", title="Article Two")
        responses = iter(
            [
                _mock_response(200, json_body=identifiers_body),
                _mock_response(200, json_body=article1),
                _mock_response(200, json_body=article2),
            ]
        )
        client = _make_client()
        with patch.object(
            client._client, "get", side_effect=lambda *a, **k: next(responses)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="0034-8910",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert len(results) == 2
        assert all(r.match_type == "issn_filter" for r in results)

    def test_issn_search_malformed_json_returns_empty(self) -> None:
        """Malformed JSON on identifiers endpoint returns empty list."""
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("not JSON")
        client = _make_client()
        with patch.object(client._client, "get", return_value=resp):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="0034-8910",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results == []


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------


class TestScieloHttpErrors:
    def test_http_500_propagates_as_exception(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(500)):
            with pytest.raises(httpx.HTTPStatusError):
                client.search(
                    title=None,
                    authors=[],
                    year=None,
                    doi="10.1234/example",
                    arxiv_id=None,
                    issn=None,
                    volume=None,
                    issue=None,
                    pages=None,
                    publisher=None,
                )

    def test_http_429_propagates_as_exception(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(429)):
            with pytest.raises(httpx.HTTPStatusError):
                client.search(
                    title=None,
                    authors=[],
                    year=None,
                    doi="10.1234/example",
                    arxiv_id=None,
                    issn=None,
                    volume=None,
                    issue=None,
                    pages=None,
                    publisher=None,
                )


# ---------------------------------------------------------------------------
# Malformed response
# ---------------------------------------------------------------------------


class TestScieloMalformedResponse:
    def test_malformed_json_on_doi_lookup_returns_empty(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("not JSON")
        client = _make_client()
        with patch.object(client._client, "get", return_value=resp):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi="10.1234/example",
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results == []

    def test_malformed_objects_field_returns_empty(self) -> None:
        body = {"objects": "not-a-list"}
        client = _make_client()
        with patch.object(
            client._client, "get", return_value=_mock_response(200, json_body=body)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="0034-8910",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert results == []

    def test_article_with_missing_isis_fields_returns_partial_candidate(self) -> None:
        """Article with empty ISIS fields degrades gracefully — returns candidate with None fields."""
        article = {
            "code": "S0000-00002020000100001",
            "collection": "scl",
            "article": {},  # no v12, v10, v65, v237
        }
        client = _make_client()
        with patch.object(
            client._client, "get", return_value=_mock_response(200, json_body=article)
        ):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi="10.1234/example",
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert len(results) == 1
        assert results[0].title is None
        assert results[0].authors == []
        assert results[0].year is None
        assert results[0].doi is None


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


class TestScieloClose:
    def test_close_calls_underlying_client(self) -> None:
        client = _make_client()
        with patch.object(client._client, "close") as mock_close:
            client.close()
        mock_close.assert_called_once()
