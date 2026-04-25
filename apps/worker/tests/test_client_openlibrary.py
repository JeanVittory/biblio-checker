"""Tests for the Open Library API client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from biblio_checker_worker.langgraph.clients.openlibrary import OpenLibraryClient


def _make_response(status_code: int, body: dict | list | None = None) -> httpx.Response:
    content = json.dumps(body).encode() if body is not None else b""
    return httpx.Response(
        status_code=status_code,
        content=content,
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://openlibrary.org/search.json"),
    )


SAMPLE_DOC = {
    "key": "/works/OL123W",
    "title": "Desarrollo y libertad",
    "author_name": ["Amartya Sen"],
    "first_publish_year": 2000,
}

SAMPLE_RESPONSE = {"numFound": 1, "docs": [SAMPLE_DOC]}


class TestTitleAuthorSearch:
    def test_returns_candidates_on_match(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        client._client.get.return_value = _make_response(200, SAMPLE_RESPONSE)
        client._client.base_url = "https://openlibrary.org"

        results = client.search(
            title="Desarrollo y libertad",
            authors=["Sen, Amartya"],
            year=2000,
            doi=None,
            arxiv_id=None,
        )

        assert len(results) == 1
        assert results[0].source == "openlibrary"
        assert results[0].title == "Desarrollo y libertad"
        assert results[0].authors == ["Amartya Sen"]
        assert results[0].year == 2000
        assert results[0].external_id == "/works/OL123W"
        assert results[0].url == "https://openlibrary.org/works/OL123W"
        assert results[0].match_type == "title_author"
        client.close()

    def test_falls_back_to_title_only_when_title_author_returns_empty(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        empty_response = _make_response(200, {"numFound": 0, "docs": []})
        title_response = _make_response(200, SAMPLE_RESPONSE)
        client._client.get.side_effect = [empty_response, title_response]
        client._client.base_url = "https://openlibrary.org"

        results = client.search(
            title="Desarrollo y libertad",
            authors=["Sen, Amartya"],
            year=2000,
            doi=None,
            arxiv_id=None,
        )

        assert len(results) == 1
        assert results[0].match_type == "title_fuzzy"
        assert client._client.get.call_count == 2
        client.close()


class TestTitleOnlySearch:
    def test_returns_candidates_without_authors(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        client._client.get.return_value = _make_response(200, SAMPLE_RESPONSE)
        client._client.base_url = "https://openlibrary.org"

        results = client.search(
            title="Desarrollo y libertad",
            authors=[],
            year=2000,
            doi=None,
            arxiv_id=None,
        )

        assert len(results) == 1
        assert results[0].match_type == "title_fuzzy"
        client.close()


class TestErrorHandling:
    def test_http_error_raises(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        client._client.get.return_value = _make_response(500)
        client._client.base_url = "https://openlibrary.org"

        with pytest.raises(httpx.HTTPStatusError):
            client.search(
                title="Test",
                authors=["Author"],
                year=2000,
                doi=None,
                arxiv_id=None,
            )
        client.close()

    def test_404_returns_empty_list(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        client._client.get.return_value = _make_response(404)
        client._client.base_url = "https://openlibrary.org"

        results = client.search(
            title="Test",
            authors=["Author"],
            year=2000,
            doi=None,
            arxiv_id=None,
        )

        assert results == []
        client.close()

    def test_malformed_json_returns_empty(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        response = httpx.Response(
            status_code=200,
            content=b"not json",
            headers={"content-type": "application/json"},
            request=httpx.Request("GET", "https://openlibrary.org/search.json"),
        )
        client._client.get.return_value = response
        client._client.base_url = "https://openlibrary.org"

        results = client.search(
            title="Test",
            authors=["Author"],
            year=2000,
            doi=None,
            arxiv_id=None,
        )

        assert results == []
        client.close()


class TestNoSearchCriteria:
    def test_no_title_returns_empty(self):
        client = OpenLibraryClient(timeout=10)

        results = client.search(
            title=None,
            authors=[],
            year=None,
            doi=None,
            arxiv_id=None,
        )

        assert results == []
        client.close()


class TestParseDoc:
    def test_missing_fields_handled_gracefully(self):
        client = OpenLibraryClient(timeout=10)
        client._client = MagicMock()
        doc_minimal = {"key": "/works/OL999W", "title": "Some Book"}
        client._client.get.return_value = _make_response(200, {"docs": [doc_minimal]})
        client._client.base_url = "https://openlibrary.org"

        results = client.search(
            title="Some Book",
            authors=[],
            year=None,
            doi=None,
            arxiv_id=None,
        )

        assert len(results) == 1
        assert results[0].authors == []
        assert results[0].year is None
        assert results[0].doi is None
        client.close()
