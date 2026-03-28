from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-untyped]

from biblio_checker_worker.langgraph.clients.llm import get_llm
from biblio_checker_worker.langgraph.prompts.parse_references import (
    PARSE_REFERENCES_SYSTEM_PROMPT,
    PARSE_REFERENCES_USER_PROMPT,
    ParseReferencesOutput,
)

if TYPE_CHECKING:
    from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger(
    "biblio_checker_worker.langgraph.nodes.parse_references"
)

# Patterns that suggest prompt injection attempts embedded in reference text.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore.{0,30}(instruction|above|previous)", re.IGNORECASE),
    re.compile(r"override", re.IGNORECASE),
    re.compile(r"system:", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
]


def _has_suspicious_content(text: str) -> bool:
    """Return True if *text* matches any known prompt-injection pattern."""
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def parse_references(state: "GraphState") -> dict[str, Any]:
    """Extract individual bibliographic references from raw document text.

    Reads ``state["raw_text"]``, calls an LLM with structured output to split
    the text into one entry per reference, then applies post-response validation
    before returning.

    Returns a dict with keys:
        - ``raw_references``: list of ``{rawText: str, index: int}`` dicts
        - ``total_references_detected``: int count
        - ``warnings``: (only present when raw_text is empty) list of warning dicts
    """
    raw_text: str = state["raw_text"]

    if not raw_text or not raw_text.strip():
        logger.warning("parse_references_empty_text")
        return {
            "raw_references": [],
            "total_references_detected": 0,
            "warnings": [
                {
                    "code": "empty_document",
                    "message": "El documento no contiene texto extraíble.",
                    "referenceId": None,
                    "details": None,
                }
            ],
        }

    logger.info("parse_references_starting", text_chars=len(raw_text))

    llm = get_llm()
    structured_llm = llm.with_structured_output(ParseReferencesOutput)

    messages = [
        SystemMessage(content=PARSE_REFERENCES_SYSTEM_PROMPT),
        HumanMessage(
            content=PARSE_REFERENCES_USER_PROMPT.format(raw_text=raw_text)
        ),
    ]

    try:
        result: ParseReferencesOutput = structured_llm.invoke(messages)  # type: ignore[assignment]
    except Exception as exc:
        logger.error("parse_references_llm_failed", error=str(exc))
        raise

    raw_references = [
        {"rawText": ref.raw_text, "index": i}
        for i, ref in enumerate(result.references)
    ]

    # Post-response validation: containment check and suspicious content check.
    for ref_dict in raw_references:
        ref_text: str = ref_dict["rawText"]

        # Advisory containment check — log if the returned text is not a
        # plausible substring of the original input.
        if ref_text not in raw_text:
            logger.warning(
                "parse_references_containment_mismatch",
                ref_index=ref_dict["index"],
            )

        if _has_suspicious_content(ref_text):
            logger.warning(
                "parse_references_suspicious_content",
                ref_index=ref_dict["index"],
            )

    logger.info("parse_references_complete", references_found=len(raw_references))

    return {
        "raw_references": raw_references,
        "total_references_detected": len(raw_references),
    }
