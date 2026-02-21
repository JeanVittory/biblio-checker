from __future__ import annotations

import asyncio
import functools
import io
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TextExtractionError(Exception):
    code: str
    detail: str | None = None


def extract_text_from_bytes(
    *,
    source_type: Literal["pdf", "docx"],
    content: bytes,
    max_chars: int,
) -> str:
    try:
        if source_type == "pdf":
            try:
                from pdfminer.high_level import extract_text as pdf_extract_text
                from pdfminer.layout import LAParams
            except ImportError as exc:
                raise TextExtractionError(
                    code="text_extraction_unavailable",
                    detail=str(exc) or None,
                ) from exc

            text = pdf_extract_text(io.BytesIO(content), laparams=LAParams())
        elif source_type == "docx":
            try:
                from docx import Document
            except ImportError as exc:
                raise TextExtractionError(
                    code="text_extraction_unavailable",
                    detail=str(exc) or None,
                ) from exc

            doc = Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            raise TextExtractionError(
                code="text_extraction_failed",
                detail=f"Unsupported sourceType '{source_type}'.",
            )
    except TextExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TextExtractionError(
            code="text_extraction_failed", detail=str(exc) or None
        ) from exc

    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if max_chars >= 0 and len(text) > max_chars:
        raise TextExtractionError(code="extracted_text_too_large")
    return text


async def extract_text_from_bytes_async(
    *,
    source_type: Literal["pdf", "docx"],
    content: bytes,
    max_chars: int,
) -> str:
    loop = asyncio.get_running_loop()
    fn = functools.partial(
        extract_text_from_bytes,
        source_type=source_type,
        content=content,
        max_chars=max_chars,
    )
    return await loop.run_in_executor(None, fn)
