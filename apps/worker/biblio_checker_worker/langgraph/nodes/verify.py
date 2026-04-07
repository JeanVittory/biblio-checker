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
from biblio_checker_worker.langgraph.clients.openalex import OpenAlexClient
from biblio_checker_worker.langgraph.clients.scielo import ScieloClient
from biblio_checker_worker.langgraph.schemas import MatchCandidate
from biblio_checker_worker.langgraph.scoring import compute_match_score

from biblio_checker_worker.langgraph.lease import renew_lease_if_needed


logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.nodes.verify")


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

    try:
        # Renew worker lease before potentially slow API calls
        renew_lease_if_needed()

        candidates: list[MatchCandidate] = []
        source_errors: dict[str, str] = {}

        for source_name, client in [
            ("openalex", openalex),
            ("scielo", scielo),
            ("arxiv", arxiv),
        ]:
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
                        "message": (
                            f"La fuente {source_name} no respondió correctamente: {safe_msg}"
                        ),
                        "referenceId": reference_id,
                        "details": None,
                    }
                )

        # Compute raw_score for candidates that are not exact matches
        scored_candidates: list[MatchCandidate] = []
        for candidate in candidates:
            if candidate.match_type not in ("doi_exact", "identifier_exact"):
                score = compute_match_score(
                    ref_title=normalized.get("title"),
                    ref_authors=normalized.get("authors", []),
                    ref_year=normalized.get("year"),
                    candidate_title=candidate.title,
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
                    "decisionReason": "Ocurrió un error interno al procesar esta referencia.",
                    "evidence": [],
                }
            ],
            "warnings": [
                *warnings,
                {
                    "code": "reference_verification_failed",
                    "message": (
                        f"La verificación de la referencia {reference_id} falló completamente."
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
