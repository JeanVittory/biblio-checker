"""i18n tests for worker warning messages (Step 07)."""

from __future__ import annotations

import pytest

from biblio_checker_worker.langgraph.nodes.normalize import (
    _validate_arxiv_id,
    _validate_doi,
    _validate_issn,
)


class TestValidateDoiWarning:
    def test_valid_doi_returns_none_warning(self) -> None:
        doi, warn = _validate_doi("10.1234/example", locale="es")
        assert doi == "10.1234/example"
        assert warn is None

    def test_spanish(self) -> None:
        _, warn = _validate_doi("not-a-doi", locale="es")
        assert warn is not None
        assert warn["code"] == "invalid_doi_format"
        assert "no cumple el formato" in warn["message"]
        assert "not-a-doi" in warn["message"]

    def test_portuguese(self) -> None:
        _, warn = _validate_doi("not-a-doi", locale="pt")
        assert warn is not None
        assert "não cumpre o formato" in warn["message"]
        assert "not-a-doi" in warn["message"]

    def test_english(self) -> None:
        _, warn = _validate_doi("not-a-doi", locale="en")
        assert warn is not None
        assert "does not match the expected format" in warn["message"]
        assert "not-a-doi" in warn["message"]

    def test_default_locale_es(self) -> None:
        """When locale is omitted the default (es) is used."""
        _, warn = _validate_doi("bad")
        assert warn is not None
        assert "no cumple el formato" in warn["message"]


class TestValidateArxivIdWarning:
    def test_valid_arxiv_id_returns_none_warning(self) -> None:
        arxiv_id, warn = _validate_arxiv_id("2301.12345", locale="es")
        assert arxiv_id == "2301.12345"
        assert warn is None

    def test_spanish(self) -> None:
        _, warn = _validate_arxiv_id("bad-arxiv", locale="es")
        assert warn is not None
        assert warn["code"] == "invalid_arxiv_id_format"
        assert "no cumple el formato" in warn["message"]

    def test_portuguese(self) -> None:
        _, warn = _validate_arxiv_id("bad-arxiv", locale="pt")
        assert warn is not None
        assert "não cumpre o formato" in warn["message"]

    def test_english(self) -> None:
        _, warn = _validate_arxiv_id("bad-arxiv", locale="en")
        assert warn is not None
        assert "does not match the expected format" in warn["message"]


class TestValidateIssnWarning:
    def test_valid_issn_returns_none_warning(self) -> None:
        issn, warn = _validate_issn("1234-567X", locale="es")
        assert issn == "1234-567X"
        assert warn is None

    @pytest.mark.parametrize("loc", ["es", "pt", "en"])
    def test_all_locales_return_warning(self, loc: str) -> None:
        _, warn = _validate_issn("bad", locale=loc)
        assert warn is not None
        assert warn["code"] == "invalid_issn_format"
        assert warn["message"]  # not empty
        assert not warn["message"].startswith("[i18n:")  # not a placeholder

    def test_spanish_message_content(self) -> None:
        _, warn = _validate_issn("bad", locale="es")
        assert warn is not None
        assert "no cumple el formato" in warn["message"]

    def test_portuguese_message_content(self) -> None:
        _, warn = _validate_issn("bad", locale="pt")
        assert warn is not None
        assert "não cumpre o formato" in warn["message"]

    def test_english_message_content(self) -> None:
        _, warn = _validate_issn("bad", locale="en")
        assert warn is not None
        assert "does not match the expected format" in warn["message"]
