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
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=article)):
            results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)

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
            results = client.search(title=None, authors=[], year=None, doi="10.9999/notfound", arxiv_id=None)
        assert results == []

    def test_invalid_doi_format_skips_doi_lookup(self) -> None:
        """Malformed DOI skips lookup and proceeds to title search."""
        client = _make_client()
        title_resp = _mock_response(200, json_body={"objects": []})
        with patch.object(client._client, "get", return_value=title_resp) as mock_get:
            results = client.search(title="Some Title", authors=[], year=None, doi="not-a-doi", arxiv_id=None)
        # The only call should be to identifiers endpoint (title search)
        call_path = mock_get.call_args[0][0]
        assert "identifiers" in call_path
        assert results == []

    def test_year_extracted_from_date_string(self) -> None:
        article = _article_fixture(date="20150301")
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=article)):
            results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)
        assert results[0].year == 2015


# ---------------------------------------------------------------------------
# Title search (two-step: identifiers then fetch)
# ---------------------------------------------------------------------------

class TestScieloTitleSearch:
    def test_title_search_fetches_metadata_per_pid(self) -> None:
        identifiers_body = {
            "objects": [
                {"code": "S0123-45672020000100001", "collection": "scl"},
            ]
        }
        article = _article_fixture()
        responses = iter([
            _mock_response(200, json_body=identifiers_body),
            _mock_response(200, json_body=article),
        ])
        client = _make_client()
        with patch.object(client._client, "get", side_effect=lambda *a, **k: next(responses)):
            results = client.search(title="Example", authors=[], year=None, doi=None, arxiv_id=None)

        assert len(results) == 1
        assert results[0].match_type == "title_fuzzy"
        assert results[0].raw_score == 0.0

    def test_title_search_no_identifiers_returns_empty(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body={"objects": []})):
            results = client.search(title="Obscure Paper", authors=[], year=None, doi=None, arxiv_id=None)
        assert results == []

    def test_title_search_pid_not_found_skips_entry(self) -> None:
        identifiers_body = {
            "objects": [{"code": "S_MISSING", "collection": "scl"}]
        }
        responses = iter([
            _mock_response(200, json_body=identifiers_body),
            _mock_response(404),
        ])
        client = _make_client()
        with patch.object(client._client, "get", side_effect=lambda *a, **k: next(responses)):
            results = client.search(title="Title", authors=[], year=None, doi=None, arxiv_id=None)
        assert results == []


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------

class TestScieloHttpErrors:
    def test_http_500_propagates_as_exception(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(500)):
            with pytest.raises(httpx.HTTPStatusError):
                client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)

    def test_http_429_propagates_as_exception(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(429)):
            with pytest.raises(httpx.HTTPStatusError):
                client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)


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
            results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)
        assert results == []

    def test_malformed_objects_field_returns_empty(self) -> None:
        body = {"objects": "not-a-list"}
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=body)):
            results = client.search(title="Something", authors=[], year=None, doi=None, arxiv_id=None)
        assert results == []

    def test_article_with_missing_isis_fields_returns_partial_candidate(self) -> None:
        """Article with empty ISIS fields degrades gracefully — returns candidate with None fields."""
        article = {
            "code": "S0000-00002020000100001",
            "collection": "scl",
            "article": {},  # no v12, v10, v65, v237
        }
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=article)):
            results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)
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
