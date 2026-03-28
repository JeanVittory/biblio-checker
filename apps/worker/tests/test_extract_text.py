from __future__ import annotations

import io
import struct
import zlib
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from biblio_checker_worker.langgraph.nodes.extract_text import extract_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(file_bytes: bytes, source_type: str) -> dict:
    return {"file_bytes": file_bytes, "source_type": source_type}


def _make_minimal_pdf(text: str = "Hello PDF") -> bytes:
    """Build a minimal but valid PDF with one page containing the given text."""
    # This is a well-known minimal PDF template that pdfminer can parse.
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n"
    )
    stream = b"BT /F1 12 Tf 100 700 Td (" + text.encode() + b") Tj ET"
    content += (
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    xref_offset = len(content)
    content += (
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000360 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
    )
    return content


def _make_minimal_docx(paragraphs: list[str]) -> bytes:
    """Build a minimal valid DOCX (ZIP) with the given paragraph texts."""
    buf = io.BytesIO()

    # Minimal document.xml
    para_xml = "".join(
        f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"'
        ' xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + para_xml
        + "</w:body></w:document>"
    ).encode()

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    ).encode()

    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
        ' Target="word/document.xml"/>'
        "</Relationships>"
    ).encode()

    word_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "</Relationships>"
    ).encode()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/_rels/document.xml.rels", word_rels_xml)
        zf.writestr("word/document.xml", document_xml)

    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

class TestPdfExtraction:
    def test_pdf_returns_raw_text(self) -> None:
        """PDF text is extracted and returned under 'raw_text' key."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            state = _make_state(b"fake-pdf-bytes", "pdf")

            with patch(
                "biblio_checker_worker.langgraph.nodes.extract_text.extract_text.__module__"
            ):
                pass

            # Patch pdfminer at the import location inside the function
            with patch(
                "pdfminer.high_level.extract_text", return_value="Reference one\nReference two"
            ):
                result = extract_text(state)

        assert result == {"raw_text": "Reference one\nReference two"}

    def test_pdf_normalizes_crlf_line_endings(self) -> None:
        """CRLF and CR line endings are normalized to LF."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", return_value="line1\r\nline2\rline3"):
                result = extract_text(_make_state(b"pdf", "pdf"))

        assert result["raw_text"] == "line1\nline2\nline3"

    def test_pdf_propagates_extraction_error(self) -> None:
        """Errors from pdfminer propagate out of the node."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", side_effect=RuntimeError("corrupt PDF")):
                with pytest.raises(RuntimeError, match="corrupt PDF"):
                    extract_text(_make_state(b"bad-pdf", "pdf"))


# ---------------------------------------------------------------------------
# DOCX extraction
# ---------------------------------------------------------------------------

class TestDocxExtraction:
    def test_docx_joins_paragraphs_with_newline(self) -> None:
        """DOCX paragraphs are joined with newlines."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        docx_bytes = _make_minimal_docx(["Author A (2020)", "Author B (2019)"])
        state = _make_state(docx_bytes, "docx")

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            result = extract_text(state)

        assert "Author A (2020)" in result["raw_text"]
        assert "Author B (2019)" in result["raw_text"]
        assert result["raw_text"].count("\n") >= 1

    def test_docx_normalizes_crlf(self) -> None:
        """CRLF in DOCX text is normalized."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        mock_paragraph = MagicMock()
        mock_paragraph.text = "line1\r\nline2"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_paragraph]

        docx_bytes = _make_minimal_docx(["placeholder"])

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("docx.Document", return_value=mock_doc):
                result = extract_text(_make_state(docx_bytes, "docx"))

        assert "\r" not in result["raw_text"]

    def test_docx_propagates_extraction_error(self) -> None:
        """Errors from python-docx propagate out of the node."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        docx_bytes = _make_minimal_docx(["placeholder"])

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("docx.Document", side_effect=RuntimeError("corrupt DOCX")):
                with pytest.raises(RuntimeError, match="corrupt DOCX"):
                    extract_text(_make_state(docx_bytes, "docx"))


# ---------------------------------------------------------------------------
# Empty document
# ---------------------------------------------------------------------------

class TestEmptyDocument:
    def test_pdf_empty_returns_empty_string(self) -> None:
        """PDF returning empty string does not raise — returns raw_text=''."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", return_value=""):
                result = extract_text(_make_state(b"pdf", "pdf"))

        assert result == {"raw_text": ""}

    def test_docx_empty_returns_empty_string(self) -> None:
        """DOCX with no paragraphs does not raise — returns raw_text=''."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        docx_bytes = _make_minimal_docx([])
        state = _make_state(docx_bytes, "docx")

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            result = extract_text(state)

        assert result == {"raw_text": ""}

    def test_pdfminer_returns_none_treated_as_empty(self) -> None:
        """If pdfminer returns None, node coerces to empty string."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", return_value=None):
                result = extract_text(_make_state(b"pdf", "pdf"))

        assert result == {"raw_text": ""}


# ---------------------------------------------------------------------------
# Oversized document
# ---------------------------------------------------------------------------

class TestOversizedDocument:
    def test_raises_value_error_when_text_exceeds_max_chars(self) -> None:
        """ValueError is raised when extracted text exceeds max_text_chars."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 10  # very small limit

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", return_value="x" * 11):
                with pytest.raises(ValueError, match="max_text_chars"):
                    extract_text(_make_state(b"pdf", "pdf"))

    def test_error_message_includes_char_count_and_limit(self) -> None:
        """ValueError message includes the actual char count and the configured limit."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 5

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", return_value="x" * 100):
                with pytest.raises(ValueError) as exc_info:
                    extract_text(_make_state(b"pdf", "pdf"))

        msg = str(exc_info.value)
        assert "100" in msg
        assert "5" in msg

    def test_text_at_exact_limit_does_not_raise(self) -> None:
        """Text exactly at max_text_chars does not raise."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 10

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("pdfminer.high_level.extract_text", return_value="x" * 10):
                result = extract_text(_make_state(b"pdf", "pdf"))

        assert len(result["raw_text"]) == 10


# ---------------------------------------------------------------------------
# Unsupported source_type
# ---------------------------------------------------------------------------

class TestUnsupportedSourceType:
    def test_raises_value_error_for_unknown_type(self) -> None:
        """ValueError is raised for unsupported source_type values."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with pytest.raises(ValueError, match="Unsupported source_type: txt"):
                extract_text(_make_state(b"data", "txt"))

    def test_error_message_includes_source_type(self) -> None:
        """ValueError message includes the offending source_type value."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with pytest.raises(ValueError, match="Unsupported source_type: html"):
                extract_text(_make_state(b"data", "html"))


# ---------------------------------------------------------------------------
# ZIP bomb protection
# ---------------------------------------------------------------------------

class TestZipBombProtection:
    def test_raises_value_error_for_oversized_docx_archive(self) -> None:
        """ValueError is raised when DOCX uncompressed size exceeds 50MB."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        # Build a fake ZipFile.infolist() where total uncompressed > 50MB
        mock_info = MagicMock()
        mock_info.file_size = 51 * 1024 * 1024  # 51 MB

        mock_zip = MagicMock()
        mock_zip.__enter__ = MagicMock(return_value=mock_zip)
        mock_zip.__exit__ = MagicMock(return_value=False)
        mock_zip.infolist.return_value = [mock_info]

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            with patch("zipfile.ZipFile", return_value=mock_zip):
                with pytest.raises(ValueError, match="DOCX archive too large"):
                    extract_text(_make_state(b"zip-data", "docx"))

    def test_docx_within_size_limit_is_accepted(self) -> None:
        """DOCX archives within the 50MB limit are processed normally."""
        mock_settings = MagicMock()
        mock_settings.max_text_chars = 500_000

        docx_bytes = _make_minimal_docx(["Valid reference"])

        with patch("biblio_checker_worker.langgraph.nodes.extract_text.get_settings", return_value=mock_settings):
            result = extract_text(_make_state(docx_bytes, "docx"))

        assert "Valid reference" in result["raw_text"]
