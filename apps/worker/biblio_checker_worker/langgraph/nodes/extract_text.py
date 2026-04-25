from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING, Any

import structlog

from biblio_checker_worker.core.config import get_settings

if TYPE_CHECKING:
    from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger(
    "biblio_checker_worker.langgraph.nodes.extract_text"
)


def extract_text(state: "GraphState") -> dict[str, Any]:
    file_bytes: bytes = state["file_bytes"]
    source_type: str = state["source_type"]

    settings = get_settings()
    max_chars = settings.max_text_chars

    logger.info(
        "extract_text_starting",
        source_type=source_type,
        content_bytes=len(file_bytes),
    )

    try:
        if source_type == "pdf":
            from pdfminer.high_level import extract_text as pdf_extract_text
            from pdfminer.layout import LAParams

            text = pdf_extract_text(io.BytesIO(file_bytes), laparams=LAParams())
        elif source_type == "docx":
            import zipfile as _zipfile

            from docx import Document

            # ZIP bomb protection — reject DOCX archives that decompress to more than 50 MB
            with _zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                total_uncompressed = sum(info.file_size for info in z.infolist())
                if total_uncompressed > 50 * 1024 * 1024:  # 50 MB
                    raise ValueError(
                        f"DOCX archive too large when decompressed: {total_uncompressed} bytes"
                    )

            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            raise ValueError(f"Unsupported source_type: {source_type}")
    except Exception as exc:
        logger.error("extract_text_failed", error=str(exc))
        raise

    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")

    if len(text) > max_chars:
        exc = ValueError(
            f"Extracted text exceeds max_text_chars limit: {len(text)} chars > {max_chars}"
        )
        logger.error("extract_text_failed", error=str(exc))
        raise exc

    logger.info("extract_text_complete", chars=len(text))
    return {"raw_text": text}
