"""classify_results node — fan-in classification step.

Reads the accumulated ``verified_references`` list (populated by N parallel
``verify_single_reference`` Send() invocations), applies the classification
engine to each reference, and writes the enriched list to
``classified_references``.

``classified_references`` is a plain field with NO reducer so it is written
once after fan-in — using ``verified_references`` here would trigger the
``operator.add`` reducer and produce 2N items.
"""

from __future__ import annotations

import structlog

from biblio_checker_worker.langgraph.classification import classify_reference
from biblio_checker_worker.langgraph.i18n import render
from biblio_checker_worker.langgraph.schemas import MatchCandidate
from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.nodes.classify")


def _candidates_from_dicts(candidate_dicts: list[dict]) -> list[MatchCandidate]:
    """Reconstruct MatchCandidate instances from serialised dicts."""
    candidates = []
    for d in candidate_dicts:
        try:
            candidates.append(
                MatchCandidate(
                    source=d["source"],
                    external_id=d["external_id"],
                    title=d.get("title"),
                    authors=d.get("authors", []),
                    year=d.get("year"),
                    doi=d.get("doi"),
                    url=d.get("url"),
                    match_type=d["match_type"],
                    raw_score=d.get("raw_score", 0.0),
                )
            )
        except Exception:
            logger.warning("classify_candidate_parse_error", candidate=d)
    return candidates


def classify_results(state: GraphState) -> dict:
    """Classify each verified reference and return the enriched list.

    Reads ``state["verified_references"]`` (accumulated fan-in results),
    applies ``classify_reference()`` to each entry, and returns
    ``{"classified_references": enriched_list}``.

    This node MUST write to ``classified_references``, NOT back to
    ``verified_references``, to avoid the operator.add reducer duplicating data.
    """
    verified_references: list[dict] = state.get("verified_references", [])  # type: ignore[attr-defined]

    logger.info(
        "classify_results_starting",
        reference_count=len(verified_references),
    )

    enriched: list[dict] = []

    for ref in verified_references:
        reference_id = ref.get("referenceId", "<unknown>")

        # References that already carry a processing_error classification were
        # set by verify_single_reference and should pass through unchanged.
        if ref.get("classification") == "processing_error":
            enriched.append(ref)
            continue

        normalized: dict = ref.get("normalized", {})
        candidate_dicts: list[dict] = ref.get("candidates", [])
        source_errors: dict[str, str] = ref.get("source_errors", {})

        candidates = _candidates_from_dicts(candidate_dicts)

        locale: str = state.get("locale", "es")  # type: ignore[attr-defined]

        try:
            classification_result = classify_reference(
                normalized=normalized,
                candidates=candidates,
                source_errors=source_errors,
                locale=locale,
            )
        except Exception:
            logger.exception(
                "classify_reference_failed",
                reference_id=reference_id,
            )
            classification_result = {
                "classification": "processing_error",
                "confidenceScore": None,
                "confidenceBand": None,
                "manualReviewRequired": True,
                "reasonCode": "reference_processing_failure",
                "decisionReason": render("class.processing_error", locale),
                "evidence": [],
            }

        enriched_ref = {
            **ref,
            **classification_result,
        }
        enriched.append(enriched_ref)

        logger.debug(
            "classify_reference_done",
            reference_id=reference_id,
            classification=classification_result["classification"],
            reason_code=classification_result["reasonCode"],
        )

    logger.info(
        "classify_results_complete",
        classified_count=len(enriched),
    )

    return {"classified_references": enriched}
