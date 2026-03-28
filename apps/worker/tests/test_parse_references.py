"""Tests for Step 05 — Parse References Node."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from biblio_checker_worker.langgraph.nodes.parse_references import parse_references
from biblio_checker_worker.langgraph.prompts.parse_references import (
    ParsedReference,
    ParseReferencesOutput,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(raw_text: str = "") -> dict:
    return {"raw_text": raw_text}


def _make_parse_output(refs: list[str]) -> ParseReferencesOutput:
    """Build a ParseReferencesOutput from a list of reference text strings."""
    return ParseReferencesOutput(
        references=[ParsedReference(raw_text=t) for t in refs]
    )


def _mock_structured_llm(output: ParseReferencesOutput) -> MagicMock:
    """Return a mock LLM whose .with_structured_output().invoke() returns *output*."""
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = output
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    return mock_llm


# ---------------------------------------------------------------------------
# Normal extraction
# ---------------------------------------------------------------------------


class TestNormalExtraction:
    def test_returns_raw_references_and_count(self) -> None:
        """Normal extraction returns references list and total_references_detected."""
        raw_text = (
            "Smith, J. (2020). A study of things. Journal of Studies, 10(2), 1–10.\n\n"
            "Doe, A. & Lee, B. (2019). Another paper. Acta Scientiarum, 5, 42–50."
        )
        parse_output = _make_parse_output(
            [
                "Smith, J. (2020). A study of things. Journal of Studies, 10(2), 1–10.",
                "Doe, A. & Lee, B. (2019). Another paper. Acta Scientiarum, 5, 42–50.",
            ]
        )
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            result = parse_references(_make_state(raw_text))

        assert "raw_references" in result
        assert result["total_references_detected"] == 2
        assert len(result["raw_references"]) == 2

    def test_each_entry_has_raw_text_and_index(self) -> None:
        """Each dict in raw_references has 'rawText' (str) and 'index' (int)."""
        raw_text = "Author A. (2021). Title one.\n\nAuthor B. (2022). Title two."
        parse_output = _make_parse_output(
            ["Author A. (2021). Title one.", "Author B. (2022). Title two."]
        )
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            result = parse_references(_make_state(raw_text))

        refs = result["raw_references"]
        for i, ref in enumerate(refs):
            assert "rawText" in ref
            assert "index" in ref
            assert ref["index"] == i
            assert isinstance(ref["rawText"], str)

    def test_indices_are_zero_based_and_sequential(self) -> None:
        """Reference indices start at 0 and are contiguous."""
        parse_output = _make_parse_output(["Ref A.", "Ref B.", "Ref C."])
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            result = parse_references(_make_state("Ref A.\n\nRef B.\n\nRef C."))

        indices = [r["index"] for r in result["raw_references"]]
        assert indices == [0, 1, 2]

    def test_single_reference_document(self) -> None:
        """A document with one reference returns a list of length 1."""
        parse_output = _make_parse_output(["Only one ref here."])
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            result = parse_references(_make_state("Only one ref here."))

        assert result["total_references_detected"] == 1
        assert len(result["raw_references"]) == 1

    def test_llm_called_with_structured_output(self) -> None:
        """with_structured_output is called with ParseReferencesOutput schema."""
        parse_output = _make_parse_output(["Some ref."])
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            parse_references(_make_state("Some ref."))

        mock_llm.with_structured_output.assert_called_once_with(ParseReferencesOutput)

    def test_no_warnings_key_on_normal_success(self) -> None:
        """The 'warnings' key is absent from the result on a normal (non-empty) run."""
        parse_output = _make_parse_output(["A reference."])
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            result = parse_references(_make_state("A reference."))

        assert "warnings" not in result


# ---------------------------------------------------------------------------
# Empty text
# ---------------------------------------------------------------------------


class TestEmptyText:
    def test_empty_string_returns_empty_list_without_calling_llm(self) -> None:
        """Empty raw_text returns immediately without invoking the LLM."""
        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm"
        ) as mock_get_llm:
            result = parse_references(_make_state(""))

        mock_get_llm.assert_not_called()
        assert result["raw_references"] == []
        assert result["total_references_detected"] == 0

    def test_whitespace_only_string_returns_empty_list(self) -> None:
        """Whitespace-only raw_text is treated as empty."""
        with patch("biblio_checker_worker.langgraph.nodes.parse_references.get_llm"):
            result = parse_references(_make_state("   \n\t  "))

        assert result["raw_references"] == []
        assert result["total_references_detected"] == 0

    def test_empty_text_returns_empty_document_warning(self) -> None:
        """The empty_document warning dict is returned for empty raw_text."""
        with patch("biblio_checker_worker.langgraph.nodes.parse_references.get_llm"):
            result = parse_references(_make_state(""))

        assert "warnings" in result
        assert len(result["warnings"]) == 1
        warning = result["warnings"][0]
        assert warning["code"] == "empty_document"
        assert warning["referenceId"] is None

    def test_empty_text_warning_message_is_in_spanish(self) -> None:
        """The empty_document warning message is in Spanish."""
        with patch("biblio_checker_worker.langgraph.nodes.parse_references.get_llm"):
            result = parse_references(_make_state(""))

        assert "El documento no contiene" in result["warnings"][0]["message"]

    def test_llm_returns_empty_list_is_valid(self) -> None:
        """LLM returning no references is a valid result — not an error."""
        parse_output = _make_parse_output([])
        mock_llm = _mock_structured_llm(parse_output)

        with patch(
            "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
            return_value=mock_llm,
        ):
            result = parse_references(_make_state("Some text that has no references."))

        assert result["raw_references"] == []
        assert result["total_references_detected"] == 0


# ---------------------------------------------------------------------------
# LLM error propagation
# ---------------------------------------------------------------------------


class TestLLMErrorPropagation:
    def test_llm_network_error_propagates(self) -> None:
        """Network errors from the LLM call are not swallowed."""
        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = ConnectionError("Network unavailable")
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
                return_value=mock_llm,
            ),
            pytest.raises(ConnectionError, match="Network unavailable"),
        ):
            parse_references(_make_state("Some references here."))

    def test_llm_output_parser_exception_propagates(self) -> None:
        """OutputParserException from with_structured_output is not swallowed."""
        from langchain_core.exceptions import OutputParserException

        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = OutputParserException("bad output")
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
                return_value=mock_llm,
            ),
            pytest.raises(OutputParserException),
        ):
            parse_references(_make_state("References list."))

    def test_llm_runtime_error_propagates(self) -> None:
        """Arbitrary RuntimeError from the LLM is not swallowed."""
        mock_structured = MagicMock()
        mock_structured.invoke.side_effect = RuntimeError("API quota exceeded")
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        with (
            patch(
                "biblio_checker_worker.langgraph.nodes.parse_references.get_llm",
                return_value=mock_llm,
            ),
            pytest.raises(RuntimeError, match="API quota exceeded"),
        ):
            parse_references(_make_state("Some text."))
