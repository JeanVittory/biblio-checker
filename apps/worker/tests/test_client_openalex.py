from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from biblio_checker_worker.langgraph.clients.openalex import OPENALEX_BASE_URL, OpenAlexClient
from biblio_checker_worker.langgraph.schemas import MatchCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(**kwargs) -> OpenAlexClient:
    """Return a client pointing at the real base URL (HTTP calls are mocked in tests)."""
    return OpenAlexClient(timeout=5, **kwargs)


def _work_fixture(
    openalex_id: str = "https://openalex.org/W1234567890",
    title: str = "Deep Learning for NLP",
    authors: list[str] | None = None,
    year: int = 2020,
    doi: str = "https://doi.org/10.1234/example",
) -> dict:
    if authors is None:
        authors = ["Jane Smith", "John Doe"]
    return {
        "id": openalex_id,
        "title": title,
        "authorships": [
            {"author": {"display_name": name}} for name in authors
        ],
        "publication_year": year,
        "doi": doi,
    }


def _mock_response(status_code: int, json_body=None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = Exception("no JSON")
    resp.text = text
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

class TestOpenAlexDoiLookup:
    def test_doi_found_returns_single_candidate(self) -> None:
        work = _work_fixture()
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=work)):
            results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)

        assert len(results) == 1
        candidate = results[0]
        assert isinstance(candidate, MatchCandidate)
        assert candidate.source == "openalex"
        assert candidate.external_id == "W1234567890"
        assert candidate.title == "Deep Learning for NLP"
        assert candidate.authors == ["Jane Smith", "John Doe"]
        assert candidate.year == 2020
        assert candidate.doi == "10.1234/example"
        assert candidate.match_type == "doi_exact"
        assert candidate.raw_score == 1.0

    def test_doi_not_found_returns_empty_list(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(404)):
            results = client.search(title=None, authors=[], year=None, doi="10.1234/notfound", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)
        assert results == []

    def test_invalid_doi_format_skips_lookup_falls_through_to_title(self) -> None:
        """If DOI is malformed, skip DOI lookup and try title search instead."""
        client = _make_client()
        title_response = _mock_response(200, json_body={"results": []})
        with patch.object(client._client, "get", return_value=title_response) as mock_get:
            results = client.search(title="Some Title", authors=[], year=None, doi="not-a-doi", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)
        # Should have called title search, not DOI path
        call_args = mock_get.call_args[0][0]
        assert "/works" in call_args or call_args == "/works"
        assert results == []

    def test_doi_url_path_encodes_doi(self) -> None:
        """DOI with special characters must be URL-encoded in the path."""
        client = _make_client()
        resp = _mock_response(404)
        captured_calls: list[str] = []

        def fake_get(path, **kwargs):
            captured_calls.append(path)
            return resp

        with patch.object(client._client, "get", side_effect=fake_get):
            client.search(title=None, authors=[], year=None, doi="10.1234/ex(ample)", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)

        assert len(captured_calls) == 1
        # Parentheses must be encoded
        assert "(" not in captured_calls[0]
        assert ")" not in captured_calls[0]
        assert "%28" in captured_calls[0] or "%2528" in captured_calls[0] or "ex%28ample%29" in captured_calls[0]


# ---------------------------------------------------------------------------
# Title search
# ---------------------------------------------------------------------------

class TestOpenAlexTitleSearch:
    def test_title_search_returns_candidates(self) -> None:
        work1 = _work_fixture(openalex_id="https://openalex.org/W111", title="NLP Study", year=2021, doi=None)
        work2 = _work_fixture(openalex_id="https://openalex.org/W222", title="NLP Survey", year=2022, doi=None)
        body = {"results": [work1, work2]}
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=body)):
            results = client.search(title="NLP", authors=[], year=None, doi=None, arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)

        assert len(results) == 2
        assert all(c.match_type == "title_fuzzy" for c in results)
        assert all(c.raw_score == 0.0 for c in results)
        assert results[0].external_id == "W111"

    def test_title_search_no_results_returns_empty_list(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body={"results": []})):
            results = client.search(title="Completely Obscure", authors=[], year=None, doi=None, arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)
        assert results == []

    def test_title_search_work_with_no_title_maps_to_none(self) -> None:
        work = _work_fixture(title=None)
        work["title"] = None
        body = {"results": [work]}
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=body)):
            results = client.search(title="Something", authors=[], year=None, doi=None, arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)
        assert results[0].title is None


# ---------------------------------------------------------------------------
# Author + Title search (metadata_partial)
# ---------------------------------------------------------------------------

class TestOpenAlexAuthorTitleSearch:
    def test_author_title_search_triggered_when_title_and_authors_provided(self) -> None:
        """When higher strategies return empty, author+title search runs."""
        work = _work_fixture()
        empty_body = {"results": []}
        results_body = {"results": [work]}

        # title+author+year skipped (no year), title+year skipped (no year),
        # author+title_search finds result
        responses = iter([
            _mock_response(200, json_body=results_body),  # author+title search finds result
        ])

        client = _make_client()
        with patch.object(client._client, "get", side_effect=lambda *a, **k: next(responses)):
            results = client.search(title="Deep Learning", authors=["Jane Smith"], year=None, doi=None, arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)

        assert len(results) == 1
        assert results[0].match_type == "metadata_partial"


# ---------------------------------------------------------------------------
# Title + Author + Year search (NEW)
# ---------------------------------------------------------------------------

class TestOpenAlexTitleAuthorYearSearch:
    def test_returns_candidates_when_all_three_provided(self) -> None:
        """title+author+year search returns results when all three fields are present."""
        work = _work_fixture()
        body = {"results": [work]}
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=body)):
            results = client.search(
                title="Deep Learning for NLP",
                authors=["Jane Smith"],
                year=2020,
                doi=None,
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )
        assert len(results) == 1
        assert results[0].match_type == "metadata_partial"

    def test_skipped_when_year_is_none(self) -> None:
        """Without year, strategy 2 is skipped; falls through to author+title (strategy 5)."""
        work = _work_fixture()
        body = {"results": [work]}
        captured_params: list[dict] = []

        def fake_get(path, **kwargs):
            captured_params.append(kwargs.get("params", {}))
            return _mock_response(200, json_body=body)

        client = _make_client()
        with patch.object(client._client, "get", side_effect=fake_get):
            results = client.search(
                title="Deep Learning for NLP",
                authors=["Jane Smith"],
                year=None,
                doi=None,
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )

        # The first call should NOT use publication_year in the filter
        assert len(captured_params) >= 1
        first_filter = captured_params[0].get("filter", "")
        assert "publication_year" not in first_filter

    def test_returns_empty_when_no_results(self) -> None:
        """title+author+year returns empty list when API returns no results."""
        client = _make_client()
        # All strategies return empty
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body={"results": []})):
            results = client.search(
                title="Obscure Title",
                authors=["Unknown Author"],
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


# ---------------------------------------------------------------------------
# ISSN + Volume search (NEW)
# ---------------------------------------------------------------------------

class TestOpenAlexIssnVolumeSearch:
    def test_returns_candidates_with_issn_and_volume(self) -> None:
        """ISSN+volume search returns candidates when both fields are present."""
        work = _work_fixture()
        empty_body = {"results": []}
        results_body = {"results": [work]}

        # DOI is None, title+author+year skipped (no title/authors/year),
        # ISSN+volume hits
        responses = iter([
            _mock_response(200, json_body=results_body),
        ])
        client = _make_client()
        with patch.object(client._client, "get", side_effect=lambda *a, **k: next(responses)):
            results = client.search(
                title=None,
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="1234-5678",
                volume="42",
                issue=None,
                pages=None,
                publisher=None,
            )
        assert len(results) == 1
        assert results[0].match_type == "metadata_partial"

    def test_skipped_when_issn_is_none(self) -> None:
        """Without ISSN, ISSN+volume strategy is skipped entirely."""
        captured_params: list[dict] = []

        def fake_get(path, **kwargs):
            captured_params.append(kwargs.get("params", {}))
            return _mock_response(200, json_body={"results": []})

        client = _make_client()
        with patch.object(client._client, "get", side_effect=fake_get):
            results = client.search(
                title="Some Title",
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn=None,
                volume="42",
                issue=None,
                pages=None,
                publisher=None,
            )

        # No call should use ISSN filter
        for params in captured_params:
            filt = params.get("filter", "")
            assert "primary_location.source.issn" not in filt

    def test_skipped_when_volume_is_none(self) -> None:
        """Without volume, ISSN+volume strategy is skipped."""
        captured_params: list[dict] = []

        def fake_get(path, **kwargs):
            captured_params.append(kwargs.get("params", {}))
            return _mock_response(200, json_body={"results": []})

        client = _make_client()
        with patch.object(client._client, "get", side_effect=fake_get):
            results = client.search(
                title="Some Title",
                authors=[],
                year=None,
                doi=None,
                arxiv_id=None,
                issn="1234-5678",
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )

        for params in captured_params:
            filt = params.get("filter", "")
            assert "biblio.volume" not in filt


# ---------------------------------------------------------------------------
# Title + Year search (NEW)
# ---------------------------------------------------------------------------

class TestOpenAlexTitleYearSearch:
    def test_returns_candidates_with_title_and_year(self) -> None:
        """Title+year search returns results when both fields are present."""
        work = _work_fixture()
        results_body = {"results": [work]}

        captured_params: list[dict] = []

        def fake_get(path, **kwargs):
            params = kwargs.get("params", {})
            captured_params.append(params)
            filt = params.get("filter", "")
            # Only return results for title+year query
            if "publication_year" in filt and "raw_author_name" not in filt:
                return _mock_response(200, json_body=results_body)
            return _mock_response(200, json_body={"results": []})

        client = _make_client()
        with patch.object(client._client, "get", side_effect=fake_get):
            results = client.search(
                title="Deep Learning for NLP",
                authors=[],
                year=2020,
                doi=None,
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )

        assert len(results) == 1
        assert results[0].match_type == "title_fuzzy"

    def test_title_year_filter_uses_publication_year(self) -> None:
        """The title+year strategy sends publication_year in the filter."""
        captured_params: list[dict] = []

        def fake_get(path, **kwargs):
            captured_params.append(kwargs.get("params", {}))
            return _mock_response(200, json_body={"results": []})

        client = _make_client()
        with patch.object(client._client, "get", side_effect=fake_get):
            client.search(
                title="Some Paper",
                authors=[],
                year=2021,
                doi=None,
                arxiv_id=None,
                issn=None,
                volume=None,
                issue=None,
                pages=None,
                publisher=None,
            )

        filters_used = [p.get("filter", "") for p in captured_params]
        assert any("publication_year:2021" in f for f in filters_used)


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------

class TestOpenAlexHttpErrors:
    def test_http_500_propagates_as_exception(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(500)):
            with pytest.raises(httpx.HTTPStatusError):
                client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)

    def test_http_429_propagates_as_exception(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(429)):
            with pytest.raises(httpx.HTTPStatusError):
                client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)


# ---------------------------------------------------------------------------
# Malformed response handling
# ---------------------------------------------------------------------------

class TestOpenAlexMalformedResponse:
    def test_malformed_json_on_doi_lookup_returns_empty_list(self) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("not JSON")
        client = _make_client()
        with patch.object(client._client, "get", return_value=resp):
            results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)
        assert results == []

    def test_malformed_results_field_returns_empty_list(self) -> None:
        body = {"results": "not-a-list"}
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, json_body=body)):
            results = client.search(title="Something", authors=[], year=None, doi=None, arxiv_id=None, issn=None, volume=None, issue=None, pages=None, publisher=None)
        assert results == []


# ---------------------------------------------------------------------------
# Polite pool email header
# ---------------------------------------------------------------------------

class TestOpenAlexPolitePool:
    def test_email_included_in_user_agent_header(self) -> None:
        client = OpenAlexClient(timeout=5, email="test@example.com")
        assert "mailto:test@example.com" in client._client.headers.get("user-agent", "")

    def test_no_email_omits_user_agent_override(self) -> None:
        client = OpenAlexClient(timeout=5, email="")
        # User-Agent header should not contain mailto when email is empty
        ua = client._client.headers.get("user-agent", "")
        assert "mailto:" not in ua


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestOpenAlexClose:
    def test_close_calls_underlying_client(self) -> None:
        client = _make_client()
        with patch.object(client._client, "close") as mock_close:
            client.close()
        mock_close.assert_called_once()
