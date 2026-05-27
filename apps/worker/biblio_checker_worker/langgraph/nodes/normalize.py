from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from biblio_checker_worker.langgraph.clients.llm import get_llm
from biblio_checker_worker.langgraph.i18n import render
from biblio_checker_worker.langgraph.prompts.normalize import (
    NORMALIZE_SYSTEM_PROMPT,
    NORMALIZE_USER_PROMPT,
    NormalizeReferencesOutput,
)

if TYPE_CHECKING:
    from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.nodes.normalize")

# DOI pattern: must start with "10." followed by 4+ digits, then "/", then
# one or more non-whitespace segments.
_DOI_RE = re.compile(r"^10\.\d{4,}(/\S+)+$")

# ISSN format: 4 digits, hyphen, 3 digits, check digit (0-9 or X)
_ISSN_RE = re.compile(r"^\d{4}-\d{3}[\dXx]$")

# arXiv ID patterns:
#   new-style: YYMM.NNNNN[vN]  e.g. 2301.12345 or 2301.12345v2
#   old-style: category/NNNNNNN  e.g. hep-ph/9901234
_ARXIV_NEW_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_ARXIV_OLD_RE = re.compile(r"^[a-z-]+/\d{7}$")


def _validate_doi(
    doi: str | None, locale: str = "es"
) -> tuple[str | None, dict[str, Any] | None]:
    """Validate a DOI string.

    Option A (per spec): accepts ``locale`` and calls ``render()`` for the message.
    Returns ``(doi, None)`` if valid, or ``(None, warning_dict)`` if invalid.
    """
    if doi is None:
        return None, None
    if _DOI_RE.match(doi):
        return doi, None
    warning: dict[str, Any] = {
        "code": "invalid_doi_format",
        "message": render("warn.invalid_doi_format", locale, doi=doi),
        "referenceId": None,  # filled in by caller
        "details": None,
    }
    return None, warning


def _validate_arxiv_id(
    arxiv_id: str | None,
    locale: str = "es",
) -> tuple[str | None, dict[str, Any] | None]:
    """Validate an arXiv identifier string.

    Option A (per spec): accepts ``locale`` and calls ``render()`` for the message.
    Returns ``(arxiv_id, None)`` if valid, or ``(None, warning_dict)`` if invalid.
    """
    if arxiv_id is None:
        return None, None
    if _ARXIV_NEW_RE.match(arxiv_id) or _ARXIV_OLD_RE.match(arxiv_id):
        return arxiv_id, None
    warning: dict[str, Any] = {
        "code": "invalid_arxiv_id_format",
        "message": render("warn.invalid_arxiv_id_format", locale, arxiv_id=arxiv_id),
        "referenceId": None,  # filled in by caller
        "details": None,
    }
    return None, warning


def _validate_issn(
    issn: str | None, locale: str = "es"
) -> tuple[str | None, dict[str, Any] | None]:
    """Validate an ISSN string.

    Option A (per spec): accepts ``locale`` and calls ``render()`` for the message.
    Returns ``(issn, None)`` if valid, or ``(None, warning_dict)`` if invalid.
    """
    if issn is None:
        return None, None
    if _ISSN_RE.match(issn):
        return issn.upper(), None  # Normalize lowercase 'x' check digit to 'X'
    warning: dict[str, Any] = {
        "code": "invalid_issn_format",
        "message": render("warn.invalid_issn_format", locale, issn=issn),
        "referenceId": None,  # filled in by caller
        "details": None,
    }
    return None, warning


def normalize_references(state: GraphState) -> dict[str, Any]:
    """Normalize raw bibliographic references into structured metadata.

    Sends all raw references to the LLM in a single batched call, then applies
    post-normalization identifier validation (DOI and arXiv ID format checks).

    Returns a dict with keys:
        - ``normalized_references``: list of dicts, each with ``referenceId``,
          ``rawText``, and ``normalized`` (title, authors, year, venue, doi,
          arxivId).
        - ``warnings``: list of warning dicts (only present when validation
          issues are detected).
    """
    raw_references: list[dict] = state["raw_references"]
    locale: str = state.get("locale", "es")  # type: ignore[attr-defined]

    if not raw_references:
        return {"normalized_references": []}

    logger.info("normalize_starting", reference_count=len(raw_references))

    # Wrap each reference in structural delimiters to prevent prompt injection.
    # Any instruction-like text inside the tags is treated as data, not commands.
    references_text = "\n\n".join(
        f"[{ref['index']}]\n<reference>\n{ref['rawText']}\n</reference>"
        for ref in raw_references
    )

    llm = get_llm()
    structured_llm = llm.with_structured_output(NormalizeReferencesOutput)

    messages = [
        SystemMessage(content=NORMALIZE_SYSTEM_PROMPT),
        HumanMessage(
            content=NORMALIZE_USER_PROMPT.format(
                count=len(raw_references),
                references_text=references_text,
            )
        ),
    ]

    result: NormalizeReferencesOutput = structured_llm.invoke(messages)  # type: ignore[assignment]

    if len(result.references) != len(raw_references):
        logger.warning(
            "normalize_count_mismatch",
            expected=len(raw_references),
            received=len(result.references),
        )

    normalized: list[dict] = []
    validation_warnings: list[dict] = []

    for entry in result.references:
        ref_index = entry.index
        if ref_index >= len(raw_references):
            logger.warning(
                "normalize_index_out_of_range",
                ref_index=ref_index,
                total=len(raw_references),
            )
            continue

        raw_ref = raw_references[ref_index]
        reference_id = f"ref-{ref_index + 1:03d}"

        # Validate DOI
        valid_doi, doi_warning = _validate_doi(entry.normalized.doi, locale)
        if doi_warning is not None:
            doi_warning["referenceId"] = reference_id
            validation_warnings.append(doi_warning)

        # Validate arXiv ID — note: the field uses alias "arxivId" so we access
        # it via the Python attribute name ``arxiv_id``.
        valid_arxiv, arxiv_warning = _validate_arxiv_id(
            entry.normalized.arxiv_id, locale
        )
        if arxiv_warning is not None:
            arxiv_warning["referenceId"] = reference_id
            validation_warnings.append(arxiv_warning)

        # Validate ISSN
        valid_issn, issn_warning = _validate_issn(entry.normalized.issn, locale)
        if issn_warning is not None:
            issn_warning["referenceId"] = reference_id
            validation_warnings.append(issn_warning)

        normalized.append(
            {
                "referenceId": reference_id,
                "rawText": raw_ref["rawText"],
                "normalized": {
                    "title": entry.normalized.title,
                    "authors": entry.normalized.authors,
                    "year": entry.normalized.year,
                    "venue": entry.normalized.venue,
                    "doi": valid_doi,
                    "arxivId": valid_arxiv,
                    "issn": valid_issn,
                    "volume": entry.normalized.volume,
                    "issue": entry.normalized.issue,
                    "pages": entry.normalized.pages,
                    "publisher": entry.normalized.publisher,
                },
            }
        )

    logger.info("normalize_complete", normalized_count=len(normalized))

    # Build the return value.  Warnings from count mismatch are added as a
    # top-level warning if the counts differed; identifier-format warnings are
    # always included when present.
    return_value: dict[str, Any] = {"normalized_references": normalized}

    all_warnings: list[dict] = []
    if len(result.references) != len(raw_references):
        all_warnings.append(
            {
                "code": "normalization_count_mismatch",
                "message": render(
                    "warn.normalization_count_mismatch",
                    locale,
                    returned=str(len(result.references)),
                    expected=str(len(raw_references)),
                ),
                "referenceId": None,
                "details": None,
            }
        )
    all_warnings.extend(validation_warnings)

    if all_warnings:
        return_value["warnings"] = all_warnings

    return return_value
