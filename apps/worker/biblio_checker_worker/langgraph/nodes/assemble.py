from __future__ import annotations

import structlog

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.langgraph.lease import renew_lease_if_needed
from biblio_checker_worker.langgraph.schemas import Classification, ResultsV1
from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.nodes.assemble")


def assemble_report(state: GraphState) -> dict:
    """Build and validate the final ResultsV1 payload.

    Reads ``classified_references``, ``total_references_detected``, and
    ``warnings`` from graph state. Assembles the complete ResultsV1 structure,
    validates it against the Pydantic model, and returns it as a plain dict
    ready for the persist stage.

    Calls ``renew_lease_if_needed()`` before Pydantic validation to prevent
    job-lease expiry on documents with large reference lists.

    Args:
        state: The current LangGraph state after ``classify_results`` has run.

    Returns:
        A partial state update dict containing ``{"results_v1": dict}``.

    Raises:
        pydantic.ValidationError: If the assembled payload violates any
            ResultsV1 invariant. The exception propagates as a transient
            ``StageError`` via ``run_langgraph_stage``.
    """
    classified_references: list[dict] = state["classified_references"]
    total_references_detected: int = state["total_references_detected"]
    warnings: list[dict] = state["warnings"]

    logger.info(
        "assemble_starting",
        references_count=len(classified_references),
        warnings_count=len(warnings),
    )

    # Renew the job lease before potentially expensive Pydantic validation
    # so the job is not reclaimed by another worker while we finish.
    renew_lease_if_needed()

    settings = get_settings()

    # Build ReferenceResult entries from classified references.
    references: list[dict] = [
        {
            "referenceId": ref["referenceId"],
            "rawText": ref["rawText"],
            "normalized": ref["normalized"],
            "classification": ref["classification"],
            "confidenceScore": ref["confidenceScore"],
            "confidenceBand": ref["confidenceBand"],
            "manualReviewRequired": ref["manualReviewRequired"],
            "reasonCode": ref["reasonCode"],
            "decisionReason": ref["decisionReason"],
            "evidence": ref["evidence"],
        }
        for ref in classified_references
    ]

    # Compute per-classification counts by iterating the full Classification
    # enum so every key is always present (zero-valued when absent).
    counts: dict[str, int] = {c.value: 0 for c in Classification}
    for ref in references:
        counts[ref["classification"]] += 1

    payload = {
        "schemaVersion": "1.0",
        "reportLanguage": "es",
        "pipeline": {
            "name": settings.pipeline_name,
            "version": settings.pipeline_version,
        },
        "summary": {
            "totalReferencesDetected": total_references_detected,
            "totalReferencesAnalyzed": len(references),
            "countsByClassification": counts,
        },
        "references": references,
        "warnings": warnings,
    }

    try:
        validated = ResultsV1(**payload)
    except Exception:
        logger.error(
            "assemble_validation_failed",
            references_count=len(references),
            total_references_detected=total_references_detected,
        )
        raise

    logger.info(
        "assemble_validation_passed",
        total_references_detected=total_references_detected,
        total_references_analyzed=len(references),
        counts=counts,
    )

    return {"results_v1": validated.model_dump()}
