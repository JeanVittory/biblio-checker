"""verify_single_reference node — fan-out target for parallel reference verification.

Receives a partial state dict from ``Send()`` (not the full GraphState), queries
all three API sources (OpenAlex, SciELO, arXiv) sequentially, computes similarity
scores for non-exact-match candidates, and returns the reference enriched with
evidence and source error information.

Classification is NOT applied here — it happens in ``classify_results`` (Step 09)
after all fan-out invocations complete (fan-in).
"""

from __future__ import annotations

import dataclasses
from dataclasses import asdict

import httpx
import structlog

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.langgraph.clients.arxiv import ArxivClient
from biblio_checker_worker.langgraph.clients.llm import get_llm
from biblio_checker_worker.langgraph.clients.openalex import OpenAlexClient
from biblio_checker_worker.langgraph.clients.openlibrary import OpenLibraryClient
from biblio_checker_worker.langgraph.clients.scielo import ScieloClient
from biblio_checker_worker.langgraph.i18n import render
from biblio_checker_worker.langgraph.lease import renew_lease_if_needed
from biblio_checker_worker.langgraph.schemas import MatchCandidate
from biblio_checker_worker.langgraph.scoring import (
    author_similarity,
    compute_match_score,
    title_similarity,
)

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.nodes.verify")

_TRANSLATION_CHECK_TITLE_THRESHOLD = 0.5
_TRANSLATION_CHECK_AUTHOR_THRESHOLD = 0.8
_TRANSLATED_TITLE_SCORE = 0.95


def _check_title_translation(title_a: str, title_b: str) -> bool:
    """Ask the LLM whether two titles are the same work in different languages.

    Only called when author similarity is high but title similarity is low,
    suggesting a possible cross-language match (e.g. Spanish translation vs
    English original).

    Returns True if the LLM confirms they are the same work.
    """
    prompt = (
        "Are these two titles the same academic work in different languages? "
        "Answer ONLY 'YES' or 'NO', nothing else.\n\n"
        f'Title A: "{title_a}"\n'
        f'Title B: "{title_b}"'
    )
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()  # type: ignore[union-attr]
        return answer.startswith("YES")
    except Exception:
        logger.warning("translation_check_failed", title_a=title_a, title_b=title_b)
        return False


# ---------------------------------------------------------------------------
# Error message sanitization
# ---------------------------------------------------------------------------


def _safe_error_message(exc: Exception) -> str:
    """Return a sanitised, user-facing error description.

    Prevents raw exception text (which may contain internal URLs or credentials
    hints) from leaking into stored error fields or warnings.
    """
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection_failed"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http_{exc.response.status_code}"
    return "unexpected_error"


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


def verify_single_reference(state: dict) -> dict:
    """Verify one reference against all three API sources.

    Receives partial state from ``Send()`` — NOT the full ``GraphState``.

    Input state shape::

        {
            "job_id": str,
            "reference": {
                "referenceId": str,
                "rawText": str,
                "normalized": {
                    "title": str | None,
                    "authors": list[str],
                    "year": int | None,
                    "venue": str | None,
                    "doi": str | None,
                    "arxivId": str | None,
                    "issn": str | None,
                    "volume": str | None,
                    "issue": str | None,
                    "pages": str | None,
                    "publisher": str | None,
                },
            },
            "warnings": [],
            "verified_references": [],
        }

    Returns::

        {"verified_references": [verified_ref_dict], "warnings": list[dict]}
    """
    reference: dict = state["reference"]
    reference_id: str = reference.get("referenceId", "<unknown>")
    normalized: dict = reference.get("normalized", {})
    locale: str = state.get("locale", "es")

    warnings: list[dict] = list(state.get("warnings", []))

    logger.info(
        "verify_starting",
        reference_id=reference_id,
        has_doi=normalized.get("doi") is not None,
        has_arxiv_id=normalized.get("arxivId") is not None,
        has_title=normalized.get("title") is not None,
        has_issn=normalized.get("issn") is not None,
    )

    settings = get_settings()
    openalex = OpenAlexClient(
        timeout=settings.api_timeout_seconds,
        email=settings.openalex_email,
    )
    scielo = ScieloClient(timeout=settings.api_timeout_seconds)
    arxiv = ArxivClient(timeout=settings.api_timeout_seconds)

    # Detect if the reference is a book (has publisher, no ISSN/volume)
    is_book = (
        normalized.get("publisher") is not None
        and normalized.get("issn") is None
        and normalized.get("volume") is None
    )
    openlibrary: OpenLibraryClient | None = None
    if is_book:
        openlibrary = OpenLibraryClient(timeout=settings.api_timeout_seconds)

    try:
        # Renew worker lease before potentially slow API calls
        renew_lease_if_needed()

        candidates: list[MatchCandidate] = []
        source_errors: dict[str, str] = {}

        sources: list[tuple[str, object]] = [
            ("openalex", openalex),
            ("scielo", scielo),
            ("arxiv", arxiv),
        ]
        if openlibrary is not None:
            sources.append(("openlibrary", openlibrary))

        for source_name, client in sources:
            try:
                results = client.search(  # type: ignore[union-attr]
                    title=normalized.get("title"),
                    authors=normalized.get("authors", []),
                    year=normalized.get("year"),
                    doi=normalized.get("doi"),
                    arxiv_id=normalized.get("arxivId"),
                    issn=normalized.get("issn"),
                    volume=normalized.get("volume"),
                    issue=normalized.get("issue"),
                    pages=normalized.get("pages"),
                    publisher=normalized.get("publisher"),
                )
                candidates.extend(results)
            except Exception as exc:
                logger.warning(
                    "verify_source_failed",
                    source=source_name,
                    reference_id=reference_id,
                    error=str(exc),
                )
                safe_msg = _safe_error_message(exc)
                source_errors[source_name] = safe_msg
                warnings.append(
                    {
                        "code": "source_timeout_partial",
                        "message": render(
                            "warn.source_timeout_partial",
                            locale,
                            source_name=source_name,
                            reason=safe_msg,
                        ),
                        "referenceId": reference_id,
                        "details": None,
                    }
                )

        # Compute raw_score for candidates that are not exact matches
        ref_title = normalized.get("title")
        ref_authors = normalized.get("authors", [])
        ref_year = normalized.get("year")

        scored_candidates: list[MatchCandidate] = []
        for candidate in candidates:
            if candidate.match_type not in ("doi_exact", "identifier_exact"):
                score = compute_match_score(
                    ref_title=ref_title,
                    ref_authors=ref_authors,
                    ref_year=ref_year,
                    candidate_title=candidate.title,
                    candidate_authors=candidate.authors,
                    candidate_year=candidate.year,
                )

                # Translation check: if author matches well but title doesn't,
                # ask the LLM if they are the same work in different languages.
                if (
                    ref_title
                    and candidate.title
                    and title_similarity(ref_title, candidate.title)
                    < _TRANSLATION_CHECK_TITLE_THRESHOLD
                    and author_similarity(ref_authors, candidate.authors)
                    >= _TRANSLATION_CHECK_AUTHOR_THRESHOLD
                ):
                    logger.info(
                        "translation_check_triggered",
                        reference_id=reference_id,
                        ref_title=ref_title,
                        candidate_title=candidate.title,
                    )
                    if _check_title_translation(ref_title, candidate.title):
                        logger.info(
                            "translation_confirmed",
                            reference_id=reference_id,
                        )
                        score = compute_match_score(
                            ref_title=ref_title,
                            ref_authors=ref_authors,
                            ref_year=ref_year,
                            candidate_title=ref_title,  # treat as same title
                            candidate_authors=candidate.authors,
                            candidate_year=candidate.year,
                        )

                candidate = dataclasses.replace(candidate, raw_score=score)
            scored_candidates.append(candidate)

        verified_ref: dict = {
            **reference,  # referenceId, rawText, normalized
            "candidates": [asdict(c) for c in scored_candidates],
            "source_errors": source_errors,
        }

        logger.info(
            "verify_complete",
            reference_id=reference_id,
            candidates_found=len(scored_candidates),
            sources_failed=len(source_errors),
        )

        return {
            "verified_references": [verified_ref],
            "warnings": warnings,
        }

    except Exception as exc:
        logger.exception(
            "verify_reference_failed",
            reference_id=reference_id,
        )
        return {
            "verified_references": [
                {
                    **reference,
                    "candidates": [],
                    "source_errors": {"all": _safe_error_message(exc)},
                    "classification": "processing_error",
                    "confidenceScore": None,
                    "confidenceBand": None,
                    "manualReviewRequired": True,
                    "reasonCode": "reference_processing_failure",
                    "decisionReason": render("class.processing_error", locale),
                    "evidence": [],
                }
            ],
            "warnings": [
                *warnings,
                {
                    "code": "reference_verification_failed",
                    "message": render(
                        "warn.reference_verification_failed",
                        locale,
                        reason=reference_id,
                    ),
                    "referenceId": reference_id,
                    "details": None,
                },
            ],
        }

    finally:
        openalex.close()
        scielo.close()
        arxiv.close()
        if openlibrary is not None:
            openlibrary.close()
