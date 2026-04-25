"""i18n tests for classification decisionReason strings (Step 06).

Verifies that classify_reference() produces the correct locale-specific text
and that ES output is byte-identical to the original Spanish strings.
"""

from __future__ import annotations

import pytest

from biblio_checker_worker.langgraph.classification import classify_reference
from biblio_checker_worker.langgraph.schemas import MatchCandidate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doi_match_candidate(
    title: str = "Example Title",
    year: int = 2024,
    source: str = "OpenAlex",
) -> MatchCandidate:
    return MatchCandidate(
        source=source,
        match_type="doi_exact",
        raw_score=1.0,
        external_id="W1",
        title=title,
        year=year,
        doi="10.1/x",
        url="http://example.com",
        authors=["Author A"],
    )


def _no_candidate() -> list[MatchCandidate]:
    return []


# ---------------------------------------------------------------------------
# Rule 1: DOI exact match
# ---------------------------------------------------------------------------


class TestDoiMatchReason:
    def test_spanish(self) -> None:
        out = classify_reference(
            candidates=[_doi_match_candidate()],
            normalized={"doi": "10.1/x", "title": "Example Title", "year": 2024},
            source_errors={},
            locale="es",
        )
        assert out["decisionReason"].startswith(
            "El DOI 10.1/x coincide con 'Example Title' (2024) en OpenAlex."
        )

    def test_portuguese(self) -> None:
        out = classify_reference(
            candidates=[_doi_match_candidate()],
            normalized={"doi": "10.1/x", "title": "Example Title", "year": 2024},
            source_errors={},
            locale="pt",
        )
        assert out["decisionReason"].startswith(
            "O DOI 10.1/x corresponde a 'Example Title' (2024) em OpenAlex."
        )

    def test_english(self) -> None:
        out = classify_reference(
            candidates=[_doi_match_candidate()],
            normalized={"doi": "10.1/x", "title": "Example Title", "year": 2024},
            source_errors={},
            locale="en",
        )
        assert out["decisionReason"].startswith(
            "DOI 10.1/x matches 'Example Title' (2024) in OpenAlex."
        )


# ---------------------------------------------------------------------------
# Rule 8: No match (not_found)
# ---------------------------------------------------------------------------


class TestNotFoundReason:
    @pytest.mark.parametrize(
        "loc,expected",
        [
            (
                "es",
                "No se encontraron coincidencias en ninguna fuente consultada"
                " (OpenAlex, SciELO, arXiv, Open Library).",
            ),
            (
                "pt",
                "Não foram encontradas correspondências em nenhuma fonte consultada"
                " (OpenAlex, SciELO, arXiv, Open Library).",
            ),
            (
                "en",
                "No matches were found in any consulted source"
                " (OpenAlex, SciELO, arXiv, Open Library).",
            ),
        ],
    )
    def test_all_locales(self, loc: str, expected: str) -> None:
        out = classify_reference(
            candidates=_no_candidate(),
            normalized={"title": "Some Title", "doi": None, "arxivId": None},
            source_errors={},
            locale=loc,
        )
        assert out["decisionReason"] == expected


# ---------------------------------------------------------------------------
# Snapshot test: Spanish output must be byte-identical to original
# ---------------------------------------------------------------------------


class TestSpanishByteIdentical:
    """Pins the exact Spanish text so future refactors can't silently alter copy."""

    def test_doi_match_single_with_title_and_year_es(self) -> None:
        out = classify_reference(
            candidates=[_doi_match_candidate(title="Example Title", year=2024)],
            normalized={"doi": "10.1/x", "title": "Example Title", "year": 2024},
            source_errors={},
            locale="es",
        )
        assert (
            out["decisionReason"]
            == "El DOI 10.1/x coincide con 'Example Title' (2024) en OpenAlex."
        )

    def test_not_found_es(self) -> None:
        out = classify_reference(
            candidates=[],
            normalized={"title": "Some Title", "doi": None, "arxivId": None},
            source_errors={},
            locale="es",
        )
        assert out["decisionReason"] == (
            "No se encontraron coincidencias en ninguna fuente consultada"
            " (OpenAlex, SciELO, arXiv, Open Library)."
        )

    def test_processing_error_es(self) -> None:
        """ES processing_error message must match original Spanish literal."""
        from biblio_checker_worker.langgraph.i18n import render

        msg = render("class.processing_error", "es")
        assert msg == "Ocurrió un error interno al procesar esta referencia."


# ---------------------------------------------------------------------------
# Integration: locale='pt' produces PT substrings, not ES
# ---------------------------------------------------------------------------


class TestPortugueseNotSpanish:
    def test_not_found_pt_no_es_substrings(self) -> None:
        out = classify_reference(
            candidates=[],
            normalized={"title": "Some Title", "doi": None, "arxivId": None},
            source_errors={},
            locale="pt",
        )
        reason = out["decisionReason"]
        assert "corresponde" in reason or "não" in reason or "Não" in reason
        assert "coincide" not in reason
        assert "ninguna" not in reason
