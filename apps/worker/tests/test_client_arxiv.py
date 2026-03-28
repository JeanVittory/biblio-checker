from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from biblio_checker_worker.langgraph.clients.arxiv import ARXIV_BASE_URL, ArxivClient, _parse_feed
from biblio_checker_worker.langgraph.schemas import MatchCandidate


# ---------------------------------------------------------------------------
# Fixtures: Atom XML templates
# ---------------------------------------------------------------------------

_ATOM_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
"""

_ATOM_FOOTER = """</feed>"""


def _atom_entry(
    abs_url: str = "http://arxiv.org/abs/2301.12345v1",
    title: str = "Attention Is All You Need",
    authors: list[str] | None = None,
    published: str = "2023-01-15T00:00:00Z",
    doi: str | None = None,
) -> str:
    if authors is None:
        authors = ["Vaswani, Ashish", "Shazeer, Noam"]
    author_xml = "".join(
        f"<author><name>{a}</name></author>" for a in authors
    )
    doi_xml = f"<arxiv:doi>{doi}</arxiv:doi>" if doi else ""
    return f"""
  <entry>
    <id>{abs_url}</id>
    <title>{title}</title>
    {author_xml}
    <published>{published}</published>
    {doi_xml}
  </entry>
"""


def _atom_feed(*entries: str) -> str:
    return _ATOM_HEADER + "".join(entries) + _ATOM_FOOTER


def _empty_feed() -> str:
    return _ATOM_HEADER + _ATOM_FOOTER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(**kwargs) -> ArxivClient:
    return ArxivClient(timeout=5, **kwargs)


def _mock_response(status_code: int, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "HTTP error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# XML parsing unit tests
# ---------------------------------------------------------------------------

class TestArxivXmlParsing:
    def test_parse_single_entry(self) -> None:
        xml = _atom_feed(_atom_entry())
        results = _parse_feed(xml, match_type="identifier_exact", raw_score=1.0)
        assert len(results) == 1
        c = results[0]
        assert c.source == "arxiv"
        assert c.external_id == "2301.12345"
        assert c.title == "Attention Is All You Need"
        assert "Vaswani, Ashish" in c.authors
        assert c.year == 2023
        assert c.match_type == "identifier_exact"
        assert c.raw_score == 1.0

    def test_parse_entry_with_doi(self) -> None:
        xml = _atom_feed(_atom_entry(doi="10.5555/example"))
        results = _parse_feed(xml, match_type="doi_exact", raw_score=1.0)
        assert results[0].doi == "10.5555/example"

    def test_parse_empty_feed_returns_empty_list(self) -> None:
        xml = _empty_feed()
        results = _parse_feed(xml, match_type="title_fuzzy", raw_score=0.0)
        assert results == []

    def test_parse_multiple_entries(self) -> None:
        entry1 = _atom_entry(abs_url="http://arxiv.org/abs/2301.00001v1", title="Paper One")
        entry2 = _atom_entry(abs_url="http://arxiv.org/abs/2301.00002v1", title="Paper Two")
        xml = _atom_feed(entry1, entry2)
        results = _parse_feed(xml, match_type="title_fuzzy", raw_score=0.0)
        assert len(results) == 2

    def test_external_id_strips_version_suffix(self) -> None:
        xml = _atom_feed(_atom_entry(abs_url="http://arxiv.org/abs/2301.12345v3"))
        results = _parse_feed(xml, match_type="identifier_exact", raw_score=1.0)
        assert results[0].external_id == "2301.12345"

    def test_url_is_the_full_abs_url(self) -> None:
        url = "http://arxiv.org/abs/2301.12345v1"
        xml = _atom_feed(_atom_entry(abs_url=url))
        results = _parse_feed(xml, match_type="identifier_exact", raw_score=1.0)
        assert results[0].url == url

    def test_malformed_xml_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="XML parse error"):
            _parse_feed("<<<not xml>>>", match_type="title_fuzzy", raw_score=0.0)


# ---------------------------------------------------------------------------
# arXiv ID lookup
# ---------------------------------------------------------------------------

class TestArxivIdLookup:
    def test_id_found_returns_candidate_with_identifier_exact(self) -> None:
        xml = _atom_feed(_atom_entry())
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, text=xml)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id="2301.12345")
        assert len(results) == 1
        assert results[0].match_type == "identifier_exact"
        assert results[0].raw_score == 1.0

    def test_id_not_found_returns_empty_list(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, text=_empty_feed())):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id="2301.99999")
        assert results == []

    def test_invalid_arxiv_id_format_skips_lookup(self) -> None:
        """Invalid arXiv ID skips ID lookup; falls through to title search."""
        client = _make_client()
        title_resp = _mock_response(200, text=_empty_feed())
        with patch.object(client._client, "get", return_value=title_resp) as mock_get:
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title="Some Title", authors=[], year=None, doi=None, arxiv_id="not-valid-id")
        # Only title search should have been called (1 call)
        assert mock_get.call_count == 1
        assert results == []

    def test_old_format_arxiv_id_is_accepted(self) -> None:
        """Old-style arXiv IDs like hep-ph/9901234 should be passed to the API."""
        xml = _atom_feed(_atom_entry(abs_url="http://arxiv.org/abs/hep-ph/9901234"))
        client = _make_client()
        captured: list[dict] = []

        def fake_get(path, **kwargs):
            captured.append(kwargs.get("params", {}))
            return _mock_response(200, text=xml)

        with patch.object(client._client, "get", side_effect=fake_get):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                client.search(title=None, authors=[], year=None, doi=None, arxiv_id="hep-ph/9901234")

        assert captured[0].get("id_list") == "hep-ph/9901234"


# ---------------------------------------------------------------------------
# DOI search
# ---------------------------------------------------------------------------

class TestArxivDoiSearch:
    def test_doi_search_returns_doi_exact_candidate(self) -> None:
        xml = _atom_feed(_atom_entry(doi="10.1234/example"))
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, text=xml)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title=None, authors=[], year=None, doi="10.1234/example", arxiv_id=None)
        assert len(results) == 1
        assert results[0].match_type == "doi_exact"

    def test_invalid_doi_skips_doi_search(self) -> None:
        client = _make_client()
        title_resp = _mock_response(200, text=_empty_feed())
        with patch.object(client._client, "get", return_value=title_resp) as mock_get:
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title="Some Title", authors=[], year=None, doi="not-a-doi", arxiv_id=None)
        # Only title search should have fired (1 call)
        assert mock_get.call_count == 1
        assert results == []


# ---------------------------------------------------------------------------
# Title search
# ---------------------------------------------------------------------------

class TestArxivTitleSearch:
    def test_title_search_returns_title_fuzzy_candidates(self) -> None:
        entry1 = _atom_entry(abs_url="http://arxiv.org/abs/2301.00001v1", title="Neural Nets")
        entry2 = _atom_entry(abs_url="http://arxiv.org/abs/2301.00002v1", title="Neural Networks")
        xml = _atom_feed(entry1, entry2)
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, text=xml)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title="Neural", authors=[], year=None, doi=None, arxiv_id=None)
        assert len(results) == 2
        assert all(c.match_type == "title_fuzzy" for c in results)
        assert all(c.raw_score == 0.0 for c in results)

    def test_title_search_no_results_returns_empty(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, text=_empty_feed())):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title="UnknownTitle", authors=[], year=None, doi=None, arxiv_id=None)
        assert results == []


# ---------------------------------------------------------------------------
# Throttling behaviour
# ---------------------------------------------------------------------------

class TestArxivThrottling:
    def test_sleep_called_between_strategies(self) -> None:
        """When multiple strategies are tried, time.sleep(3) is called between them."""
        # arxiv_id found nothing (empty feed), so DOI search runs next, then title
        responses = [
            _mock_response(200, text=_empty_feed()),  # id lookup -> empty
            _mock_response(200, text=_empty_feed()),  # doi search -> empty
            _mock_response(200, text=_empty_feed()),  # title search -> empty
        ]
        client = _make_client()
        sleep_calls: list[float] = []

        with patch.object(client._client, "get", side_effect=lambda *a, **k: responses.pop(0)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
                client.search(
                    title="Some Title",
                    authors=[],
                    year=None,
                    doi="10.1234/example",
                    arxiv_id="2301.12345",
                )

        # First request has no delay; subsequent ones each have a 3-second delay
        assert len(sleep_calls) == 2
        assert all(s == 3 for s in sleep_calls)

    def test_no_sleep_before_first_request(self) -> None:
        xml = _atom_feed(_atom_entry())
        client = _make_client()
        sleep_calls: list[float] = []

        with patch.object(client._client, "get", return_value=_mock_response(200, text=xml)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
                client.search(title=None, authors=[], year=None, doi=None, arxiv_id="2301.12345")

        # First (and only) request: no sleep
        assert sleep_calls == []


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------

class TestArxivHttpErrors:
    def test_http_500_propagates(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(500)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                with pytest.raises(httpx.HTTPStatusError):
                    client.search(title=None, authors=[], year=None, doi=None, arxiv_id="2301.12345")

    def test_http_404_returns_empty(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(404)):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id="2301.12345")
        assert results == []


# ---------------------------------------------------------------------------
# Malformed XML response
# ---------------------------------------------------------------------------

class TestArxivMalformedXml:
    def test_malformed_xml_returns_empty_list_with_warning(self) -> None:
        client = _make_client()
        with patch.object(client._client, "get", return_value=_mock_response(200, text="<not valid xml")):
            with patch("biblio_checker_worker.langgraph.clients.arxiv.time.sleep"):
                results = client.search(title=None, authors=[], year=None, doi=None, arxiv_id="2301.12345")
        assert results == []


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestArxivClose:
    def test_close_calls_underlying_client(self) -> None:
        client = _make_client()
        with patch.object(client._client, "close") as mock_close:
            client.close()
        mock_close.assert_called_once()
