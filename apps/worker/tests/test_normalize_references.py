"""Tests for Step 06 — Normalize References Node."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from biblio_checker_worker.langgraph.nodes.normalize import (
    _validate_issn,
    normalize_references,
)
from biblio_checker_worker.langgraph.prompts.normalize import (
    NormalizedFields,
    NormalizedReferenceEntry,
    NormalizeReferencesOutput,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(raw_references: list[dict]) -> dict:
    return {"raw_references": raw_references}


def _make_raw_refs(*texts: str) -> list[dict]:
    return [{"rawText": t, "index": i} for i, t in enumerate(texts)]


def _make_normalized_fields(
    title: str | None = "A Title",
    authors: list[str] | None = None,
    year: int | None = 2020,
    venue: str | None = "Some Journal",
    doi: str | None = None,
    arxiv_id: str | None = None,
    issn: str | None = None,
    volume: str | None = None,
    issue: str | None = None,
    pages: str | None = None,
    publisher: str | None = None,
) -> NormalizedFields:
    return NormalizedFields(
        title=title,
        authors=authors or ["Author A"],
        year=year,
        venue=venue,
        doi=doi,
        arxivId=arxiv_id,
        issn=issn,
        volume=volume,
        issue=issue,
        pages=pages,
        publisher=publisher,
    )


def _make_normalize_output(
    entries: list[tuple[int, NormalizedFields]],
) -> NormalizeReferencesOutput:
    return NormalizeReferencesOutput(
        references=[
            NormalizedReferenceEntry(index=idx, normalized=fields)
            for idx, fields in entries
        ]
    )


def _mock_structured_llm(output: NormalizeReferencesOutput) -> MagicMock:
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = output
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


# ---------------------------------------------------------------------------
# Normal normalization
# ---------------------------------------------------------------------------


class TestNormalNormalization:
    def test_returns_normalized_references_list(self) -> None:
        """Normal call returns a list under 'normalized_references'."""
        raw = _make_raw_refs(
            "Smith, J. (2020). Title one.", "Doe, A. (2019). Title two."
        )
        output = _make_normalize_output(
            [
                (0, _make_normalized_fields(title="Title one", year=2020)),
                (1, _make_normalized_fields(title="Title two", year=2019)),
            ]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert "normalized_references" in result
        assert len(result["normalized_references"]) == 2

    def test_each_entry_has_required_keys(self) -> None:
        """Each dict has referenceId, rawText, and normalized keys."""
        raw = _make_raw_refs("Ref one.", "Ref two.")
        output = _make_normalize_output(
            [
                (0, _make_normalized_fields()),
                (1, _make_normalized_fields()),
            ]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        for entry in result["normalized_references"]:
            assert "referenceId" in entry
            assert "rawText" in entry
            assert "normalized" in entry

    def test_reference_id_format_is_ref_nnn(self) -> None:
        """referenceId follows the 'ref-001', 'ref-002' format."""
        raw = _make_raw_refs("A.", "B.", "C.")
        output = _make_normalize_output(
            [
                (0, _make_normalized_fields()),
                (1, _make_normalized_fields()),
                (2, _make_normalized_fields()),
            ]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        ids = [e["referenceId"] for e in result["normalized_references"]]
        assert ids == ["ref-001", "ref-002", "ref-003"]

    def test_reference_id_is_one_based(self) -> None:
        """The first reference gets ref-001, not ref-000."""
        raw = _make_raw_refs("First ref.")
        output = _make_normalize_output([(0, _make_normalized_fields())])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["referenceId"] == "ref-001"

    def test_normalized_dict_contains_eleven_fields(self) -> None:
        """The 'normalized' sub-dict has all 11 fields."""
        raw = _make_raw_refs("Author, A. (2021). Title. Journal, 5, 1-10.")
        output = _make_normalize_output(
            [
                (
                    0,
                    _make_normalized_fields(
                        title="Title",
                        authors=["Author, A."],
                        year=2021,
                        venue="Journal",
                    ),
                )
            ]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        norm = result["normalized_references"][0]["normalized"]
        assert "title" in norm
        assert "authors" in norm
        assert "year" in norm
        assert "venue" in norm
        assert "doi" in norm
        assert "arxivId" in norm
        assert "issn" in norm
        assert "volume" in norm
        assert "issue" in norm
        assert "pages" in norm
        assert "publisher" in norm

    def test_raw_text_preserved_in_output(self) -> None:
        """rawText in normalized entry matches the original raw reference text."""
        raw_text = "Smith, J. (2020). A specific title."
        raw = _make_raw_refs(raw_text)
        output = _make_normalize_output([(0, _make_normalized_fields())])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["rawText"] == raw_text

    def test_llm_called_with_structured_output_schema(self) -> None:
        """with_structured_output is called with NormalizeReferencesOutput."""
        raw = _make_raw_refs("Some ref.")
        output = _make_normalize_output([(0, _make_normalized_fields())])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            normalize_references(_make_state(raw))

        mock_llm.with_structured_output.assert_called_once_with(
            NormalizeReferencesOutput
        )

    def test_single_llm_call_for_all_references(self) -> None:
        """All references are sent in a single LLM call."""
        raw = _make_raw_refs("Ref A.", "Ref B.", "Ref C.", "Ref D.")
        output = _make_normalize_output(
            [(i, _make_normalized_fields()) for i in range(4)]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            normalize_references(_make_state(raw))

        # invoke() called exactly once despite 4 references
        mock_llm.with_structured_output.return_value.invoke.assert_called_once()

    def test_no_warnings_on_clean_normalization(self) -> None:
        """'warnings' key is absent when all references normalized cleanly."""
        raw = _make_raw_refs("Clean ref.")
        output = _make_normalize_output([(0, _make_normalized_fields())])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert "warnings" not in result


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


class TestEmptyInput:
    def test_empty_raw_references_returns_empty_list_without_llm(self) -> None:
        """Empty raw_references returns immediately without calling the LLM."""
        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm"
        ) as mock_get_llm:
            result = normalize_references(_make_state([]))

        mock_get_llm.assert_not_called()
        assert result == {"normalized_references": []}

    def test_empty_input_returns_empty_normalized_list(self) -> None:
        """normalized_references is an empty list for empty input."""
        result = normalize_references(_make_state([]))
        assert result["normalized_references"] == []


# ---------------------------------------------------------------------------
# Count mismatch
# ---------------------------------------------------------------------------


class TestCountMismatch:
    def test_mismatch_adds_warning(self) -> None:
        """When LLM returns fewer entries than input, a warning is added."""
        raw = _make_raw_refs("Ref A.", "Ref B.", "Ref C.")
        # LLM only returns 2 of the 3 references
        output = _make_normalize_output(
            [(0, _make_normalized_fields()), (1, _make_normalized_fields())]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert "warnings" in result
        codes = [w["code"] for w in result["warnings"]]
        assert "normalization_count_mismatch" in codes

    def test_mismatch_still_processes_returned_entries(self) -> None:
        """References that the LLM did return are still included in output."""
        raw = _make_raw_refs("Ref A.", "Ref B.", "Ref C.")
        output = _make_normalize_output(
            [
                (0, _make_normalized_fields(title="Title A")),
                (2, _make_normalized_fields(title="Title C")),
            ]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert len(result["normalized_references"]) == 2

    def test_out_of_range_index_is_skipped(self) -> None:
        """An LLM-returned index beyond the input list length is silently skipped."""
        raw = _make_raw_refs("Only one ref.")
        # LLM returns index 5, which doesn't exist
        output = _make_normalize_output([(5, _make_normalized_fields())])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        # The out-of-range entry is skipped — result is empty
        assert result["normalized_references"] == []


# ---------------------------------------------------------------------------
# DOI validation
# ---------------------------------------------------------------------------


class TestDOIValidation:
    @pytest.mark.parametrize(
        "doi",
        [
            "10.1234/example.2020.001",
            "10.12345/journal.pone.0000001",
            "10.1000/xyz123",
            "10.1016/j.cell.2020.01.001",
        ],
    )
    def test_valid_doi_is_preserved(self, doi: str) -> None:
        """A well-formed DOI passes through unchanged."""
        raw = _make_raw_refs("A ref with DOI.")
        output = _make_normalize_output([(0, _make_normalized_fields(doi=doi))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["doi"] == doi
        assert "warnings" not in result

    @pytest.mark.parametrize(
        "bad_doi",
        [
            "https://doi.org/10.1234/example",  # Full URL — not just the ID
            "10.123/bad",  # Less than 4 digits after "10."
            "not-a-doi",
            "10.1234",  # Missing the /suffix part
        ],
    )
    def test_invalid_doi_is_discarded_with_warning(self, bad_doi: str) -> None:
        """A malformed DOI is set to None and a warning is added."""
        raw = _make_raw_refs("A ref with bad DOI.")
        output = _make_normalize_output([(0, _make_normalized_fields(doi=bad_doi))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["doi"] is None
        assert "warnings" in result
        codes = [w["code"] for w in result["warnings"]]
        assert "invalid_doi_format" in codes

    def test_invalid_doi_warning_includes_reference_id(self) -> None:
        """The invalid_doi_format warning has the correct referenceId."""
        raw = _make_raw_refs("A ref.")
        output = _make_normalize_output([(0, _make_normalized_fields(doi="bad-doi"))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        doi_warning = next(
            w for w in result["warnings"] if w["code"] == "invalid_doi_format"
        )
        assert doi_warning["referenceId"] == "ref-001"

    def test_none_doi_passes_without_warning(self) -> None:
        """doi=None produces no validation warning."""
        raw = _make_raw_refs("A ref with no DOI.")
        output = _make_normalize_output([(0, _make_normalized_fields(doi=None))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["doi"] is None
        assert "warnings" not in result


# ---------------------------------------------------------------------------
# arXiv ID validation
# ---------------------------------------------------------------------------


class TestArxivIDValidation:
    @pytest.mark.parametrize(
        "arxiv_id",
        [
            "2301.12345",  # New-style, 5 digits
            "2301.1234",  # New-style, 4 digits
            "2301.12345v2",  # New-style with version
            "hep-ph/9901234",  # Old-style
            "math-ph/0201034",  # Old-style different category
        ],
    )
    def test_valid_arxiv_id_is_preserved(self, arxiv_id: str) -> None:
        """A well-formed arXiv ID passes through unchanged."""
        raw = _make_raw_refs("A ref with arXiv ID.")
        output = _make_normalize_output(
            [(0, _make_normalized_fields(arxiv_id=arxiv_id))]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["arxivId"] == arxiv_id
        assert "warnings" not in result

    @pytest.mark.parametrize(
        "bad_arxiv",
        [
            "https://arxiv.org/abs/2301.12345",  # Full URL
            "arxiv:2301.12345",  # Prefixed
            "230.12345",  # Too few digits in YYMM part
            "not-an-id",
        ],
    )
    def test_invalid_arxiv_id_is_discarded_with_warning(self, bad_arxiv: str) -> None:
        """A malformed arXiv ID is set to None and a warning is added."""
        raw = _make_raw_refs("A ref with bad arXiv ID.")
        output = _make_normalize_output(
            [(0, _make_normalized_fields(arxiv_id=bad_arxiv))]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["arxivId"] is None
        assert "warnings" in result
        codes = [w["code"] for w in result["warnings"]]
        assert "invalid_arxiv_id_format" in codes

    def test_invalid_arxiv_warning_includes_reference_id(self) -> None:
        """The invalid_arxiv_id_format warning has the correct referenceId."""
        raw = _make_raw_refs("A ref.")
        output = _make_normalize_output(
            [(0, _make_normalized_fields(arxiv_id="bad-arxiv"))]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        arxiv_warning = next(
            w for w in result["warnings"] if w["code"] == "invalid_arxiv_id_format"
        )
        assert arxiv_warning["referenceId"] == "ref-001"

    def test_none_arxiv_id_passes_without_warning(self) -> None:
        """arxivId=None produces no validation warning."""
        raw = _make_raw_refs("A ref with no arXiv ID.")
        output = _make_normalize_output([(0, _make_normalized_fields(arxiv_id=None))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["arxivId"] is None
        assert "warnings" not in result

    def test_both_doi_and_arxiv_invalid_produces_two_warnings(self) -> None:
        """When both DOI and arXiv ID are invalid, two separate warnings are added."""
        raw = _make_raw_refs("A ref with two bad identifiers.")
        output = _make_normalize_output(
            [(0, _make_normalized_fields(doi="bad-doi", arxiv_id="bad-arxiv"))]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        codes = [w["code"] for w in result["warnings"]]
        assert "invalid_doi_format" in codes
        assert "invalid_arxiv_id_format" in codes
        assert (
            len(
                [
                    c
                    for c in codes
                    if c in ("invalid_doi_format", "invalid_arxiv_id_format")
                ]
            )
            == 2
        )


# ---------------------------------------------------------------------------
# ISSN validation (unit tests for _validate_issn)
# ---------------------------------------------------------------------------


class TestValidateIssn:
    def test_valid_issn_passes(self) -> None:
        assert _validate_issn("0034-8910") == ("0034-8910", None)

    def test_valid_issn_with_x_check_digit(self) -> None:
        assert _validate_issn("1234-567X") == ("1234-567X", None)

    def test_valid_issn_with_lowercase_x_normalized_to_uppercase(self) -> None:
        assert _validate_issn("1234-567x") == ("1234-567X", None)

    def test_none_passes(self) -> None:
        assert _validate_issn(None) == (None, None)

    def test_missing_hyphen_fails(self) -> None:
        issn, warning = _validate_issn("00348910")
        assert issn is None
        assert warning is not None
        assert warning["code"] == "invalid_issn_format"

    def test_too_short_fails(self) -> None:
        issn, warning = _validate_issn("1234-56")
        assert issn is None
        assert warning is not None

    def test_letters_in_prefix_fails(self) -> None:
        issn, warning = _validate_issn("ABCD-1234")
        assert issn is None
        assert warning is not None

    def test_warning_message_includes_issn_value(self) -> None:
        """The warning message contains the offending ISSN string."""
        _, warning = _validate_issn("bad-issn")
        assert warning is not None
        assert "bad-issn" in warning["message"]

    def test_warning_reference_id_is_none_before_caller_fills_it(self) -> None:
        """referenceId is None in the raw warning — caller fills it in."""
        _, warning = _validate_issn("bad-issn")
        assert warning is not None
        assert warning["referenceId"] is None

    def test_issn_validation_in_normalize_node_invalid_discarded(self) -> None:
        """An invalid ISSN is set to None and a warning is added in the full node."""
        raw = _make_raw_refs("A ref with bad ISSN.")
        output = _make_normalize_output([(0, _make_normalized_fields(issn="00348910"))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["issn"] is None
        assert "warnings" in result
        codes = [w["code"] for w in result["warnings"]]
        assert "invalid_issn_format" in codes

    def test_issn_validation_in_normalize_node_valid_preserved(self) -> None:
        """A valid ISSN passes through unchanged in the full node."""
        raw = _make_raw_refs("A ref with valid ISSN.")
        output = _make_normalize_output(
            [(0, _make_normalized_fields(issn="0034-8910"))]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        assert result["normalized_references"][0]["normalized"]["issn"] == "0034-8910"
        assert "warnings" not in result

    def test_issn_warning_includes_reference_id(self) -> None:
        """The invalid_issn_format warning has the correct referenceId."""
        raw = _make_raw_refs("A ref.")
        output = _make_normalize_output([(0, _make_normalized_fields(issn="bad-issn"))])
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        issn_warning = next(
            w for w in result["warnings"] if w["code"] == "invalid_issn_format"
        )
        assert issn_warning["referenceId"] == "ref-001"

    def test_new_passthrough_fields_in_output(self) -> None:
        """volume, issue, pages, publisher pass through as-is from LLM output."""
        raw = _make_raw_refs("A journal article with full metadata.")
        output = _make_normalize_output(
            [
                (
                    0,
                    _make_normalized_fields(
                        volume="26",
                        issue="3",
                        pages="41-72",
                        publisher=None,
                    ),
                )
            ]
        )
        mock_llm = _mock_structured_llm(output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.normalize.get_llm",
            return_value=mock_llm,
        ):
            result = normalize_references(_make_state(raw))

        norm = result["normalized_references"][0]["normalized"]
        assert norm["volume"] == "26"
        assert norm["issue"] == "3"
        assert norm["pages"] == "41-72"
        assert norm["publisher"] is None
