"""ai_adjudicate node — LLM-as-Judge for uncertain bibliographic references.

This node sits between ``analyze_cross_patterns`` and ``assemble_report``.
It reads ``classified_references`` from state, filters to uncertain references
(``manualReviewRequired == True`` and ``classification != "processing_error"``),
sends them in a single batched LLM call, applies the results, and writes back
the enriched list.

Key behaviors:
- Feature-flag gated: passes through if ``ai_adjudication_enabled`` is False
- Sorts eligible refs by ``confidenceScore`` ascending (most uncertain first)
- Caps the batch at ``ai_adjudication_max_references``
- Validates every suggestion against the compatibility matrix
- Content plausibility check guards ``ai_analysis`` before writing to ``decisionReason``
- NEVER raises — all errors degrade gracefully
"""

from __future__ import annotations

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.langgraph.clients.llm import get_llm
from biblio_checker_worker.langgraph.prompts.adjudicate import (
    ADJUDICATE_SYSTEM_PROMPT,
    AdjudicationBatchOutput,
    AdjudicationResult,
    _sanitize,
    build_adjudication_user_prompt,
)
from biblio_checker_worker.langgraph.schemas import (
    _ALLOWED_BANDS,
    _REQUIRED_MANUAL_REVIEW,
    Classification,
    ConfidenceBand,
)
from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger(
    "biblio_checker_worker.langgraph.nodes.ai_adjudicate"
)

# ---------------------------------------------------------------------------
# Confidence band derivation
# ---------------------------------------------------------------------------

_BAND_THRESHOLDS: dict[Classification, list[tuple[float, ConfidenceBand]]] = {
    Classification.VERIFIED: [
        (0.90, ConfidenceBand.VERY_HIGH),
        (0.0, ConfidenceBand.HIGH),
    ],
    Classification.LIKELY_VERIFIED: [
        (0.80, ConfidenceBand.HIGH),
        (0.0, ConfidenceBand.MEDIUM),
    ],
    Classification.AMBIGUOUS: [
        (0.50, ConfidenceBand.MEDIUM),
        (0.0, ConfidenceBand.LOW),
    ],
    Classification.NOT_FOUND: [
        (0.20, ConfidenceBand.LOW),
        (0.0, ConfidenceBand.VERY_LOW),
    ],
    Classification.SUSPICIOUS: [
        (0.90, ConfidenceBand.VERY_HIGH),
        (0.80, ConfidenceBand.HIGH),
        (0.0, ConfidenceBand.MEDIUM),
    ],
}


def _derive_confidence_band(
    classification: Classification, score: float
) -> ConfidenceBand | None:
    """Derive the confidence band from classification + score using the spec thresholds.

    Returns ``None`` for ``processing_error`` (no band applies).
    """
    thresholds = _BAND_THRESHOLDS.get(classification)
    if thresholds is None:
        return None
    for min_score, band in thresholds:
        if score >= min_score:
            return band
    # Fallback — should never reach here since last threshold is always 0.0
    return thresholds[-1][1]


def _band_is_valid(classification: Classification, band: ConfidenceBand | None) -> bool:
    """Return True if *band* is in the allowed set for *classification*."""
    allowed = _ALLOWED_BANDS.get(classification, frozenset())
    return band in allowed


# ---------------------------------------------------------------------------
# Content plausibility check
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[str] = [
    "ignore",
    "override",
    "system:",
    "[inst]",
    "ignorar",
    "anular",
    "sistema:",
]

_AUTHORITY_FRAMING_PATTERNS: list[str] = [
    "verificado por",
    "según crossref",
    "según datacite",
    "confirmado externamente",
    "verified by",
    "confirmed by",
    "esta referencia es confiable",
    "no hay preocupaciones",
]


def _passes_plausibility_check(ai_analysis: str) -> bool:
    """Return True if *ai_analysis* passes the content plausibility check.

    Checks for injection artifacts and authority-framing language (both
    Spanish and English, case-insensitive).
    """
    lower = ai_analysis.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            return False
    for pattern in _AUTHORITY_FRAMING_PATTERNS:
        if pattern in lower:
            return False
    return True


# ---------------------------------------------------------------------------
# Response application
# ---------------------------------------------------------------------------

_AI_ANALYSIS_MAX_CHARS = 500


def _apply_adjudication_result(
    ref: dict,
    result: AdjudicationResult,
) -> dict:
    """Apply a single ``AdjudicationResult`` to the corresponding reference dict.

    Returns a new dict (does not mutate *ref*).

    Steps per the spec:
    1. Derive confidence band from suggested classification + score
    2. Validate against compatibility matrix; reject if invalid
    3. Apply classification/score/band if valid
    4. Apply ai_analysis with plausibility check and truncation
    5. Append sanitized fabrication_indicators as bullet list
    6. Recompute manualReviewRequired
    7. Preserve reasonCode always
    """
    updated = dict(ref)

    old_classification = ref.get("classification", "")

    # --- Step 1 & 2: classification validation ---
    suggested_cls_str = str(result.suggested_classification)

    # LLM must never suggest processing_error
    if suggested_cls_str == Classification.PROCESSING_ERROR:
        logger.warning(
            "ai_adjudicate_suggestion_rejected",
            reference_id=result.reference_id,
            reason="processing_error_suggested",
            suggested_classification=suggested_cls_str,
            suggested_confidence=result.suggested_confidence_score,
        )
    else:
        try:
            suggested_cls = Classification(suggested_cls_str)
        except ValueError:
            logger.warning(
                "ai_adjudicate_suggestion_rejected",
                reference_id=result.reference_id,
                reason="unknown_classification",
                suggested_classification=suggested_cls_str,
                suggested_confidence=result.suggested_confidence_score,
            )
        else:
            band = _derive_confidence_band(
                suggested_cls, result.suggested_confidence_score
            )
            if _band_is_valid(suggested_cls, band):
                updated["classification"] = suggested_cls_str
                updated["confidenceScore"] = result.suggested_confidence_score
                updated["confidenceBand"] = band.value if band is not None else None
            else:
                logger.warning(
                    "ai_adjudicate_suggestion_rejected",
                    reference_id=result.reference_id,
                    reason="invalid_band_combination",
                    suggested_classification=suggested_cls_str,
                    suggested_confidence=result.suggested_confidence_score,
                    derived_band=band,
                )

    # --- Step 3: ai_analysis truncation ---
    ai_text = result.ai_analysis
    if len(ai_text) > _AI_ANALYSIS_MAX_CHARS:
        ai_text = ai_text[: _AI_ANALYSIS_MAX_CHARS - 3] + "..."

    # --- Step 4: content plausibility check ---
    if _passes_plausibility_check(ai_text):
        # --- Step 5: sanitize and append fabrication_indicators ---
        sanitized_indicators = [
            _sanitize(ind)
            for ind in result.fabrication_indicators
            if _sanitize(ind).strip()
        ]

        decision_reason = ai_text
        if sanitized_indicators:
            bullet_list = "\n".join(f"- {ind}" for ind in sanitized_indicators)
            decision_reason = f"{ai_text}\n\nIndicadores de fabricación:\n{bullet_list}"

        updated["decisionReason"] = decision_reason
    else:
        logger.warning(
            "ai_analysis_plausibility_rejected",
            reference_id=result.reference_id,
            reason="authority_framing_or_injection_detected",
        )
        # Preserve original decisionReason — do NOT overwrite

    # --- Step 6: recompute manualReviewRequired ---
    final_cls_str = updated.get("classification", "")
    try:
        final_cls = Classification(final_cls_str)
        updated["manualReviewRequired"] = final_cls in _REQUIRED_MANUAL_REVIEW
    except ValueError:
        pass  # If unknown, leave as-is

    # --- Step 7: reasonCode is never overwritten ---
    # ref["reasonCode"] is preserved because we only set the fields we intend to change.

    new_classification = updated.get("classification", "")
    logger.debug(
        "ai_adjudicate_result_applied",
        reference_id=result.reference_id,
        old_classification=old_classification,
        new_classification=new_classification,
        classification_changed=old_classification != new_classification,
    )

    return updated


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


def ai_adjudicate(state: GraphState) -> dict:
    """LLM-as-Judge node for uncertain bibliographic references.

    Reads ``classified_references`` and optionally ``cross_reference_analysis``
    from state. Filters to eligible references, calls the LLM, applies results,
    and returns ``{"classified_references": enriched_list}``.

    All error paths degrade gracefully — the node never raises.
    """
    settings = get_settings()
    classified_references: list[dict] = state.get(  # type: ignore[call-overload]
        "classified_references", []
    )

    # --- Feature flag check ---
    if not settings.ai_adjudication_enabled:
        return {"classified_references": classified_references}

    cross_reference_analysis: dict = state.get(  # type: ignore[call-overload]
        "cross_reference_analysis", {}
    )

    # --- Reference filtering ---
    eligible: list[dict] = [
        ref
        for ref in classified_references
        if ref.get("manualReviewRequired") is True
        and ref.get("classification") != Classification.PROCESSING_ERROR
    ]

    total_count = len(classified_references)
    eligible_count = len(eligible)

    # --- Short-circuit if no eligible references ---
    if not eligible:
        logger.info(
            "ai_adjudicate_skipped",
            reason="no_eligible_references",
        )
        return {"classified_references": classified_references}

    # --- Priority sorting: lowest confidenceScore first (most uncertain) ---
    eligible_sorted = sorted(
        eligible,
        key=lambda r: r.get("confidenceScore") or 0.0,
    )

    max_refs = settings.ai_adjudication_max_references
    capped = len(eligible_sorted) > max_refs
    if capped:
        eligible_sorted = eligible_sorted[:max_refs]

    logger.info(
        "ai_adjudicate_starting",
        eligible_count=eligible_count,
        total_count=total_count,
        capped=capped,
    )

    # Build a lookup for fast merge-back
    # Using referenceId as the key
    eligible_ids: set[str] = {r.get("referenceId", "") for r in eligible_sorted}

    # --- LLM invocation ---
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(AdjudicationBatchOutput)

        user_prompt = build_adjudication_user_prompt(
            references=eligible_sorted,
            cross_reference_analysis=cross_reference_analysis,
        )
        messages = [
            SystemMessage(content=ADJUDICATE_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        logger.info(
            "ai_adjudicate_llm_invoked",
            reference_count=len(eligible_sorted),
        )

        batch_output: AdjudicationBatchOutput = structured_llm.invoke(messages)

    except Exception as exc:
        exc_type = type(exc).__name__
        is_timeout = "Timeout" in exc_type or "timeout" in str(exc).lower()
        event = (
            "ai_adjudicate_llm_timeout" if is_timeout else "ai_adjudicate_parse_error"
        )
        warning_code = (
            "ai_adjudication_timeout" if is_timeout else "ai_adjudication_parse_error"
        )

        logger.error(event, error=str(exc), exc_info=True)

        warning = {
            "code": warning_code,
            "message": (
                "El servicio de adjudicación con IA no estuvo disponible. "
                "Las clasificaciones determinísticas se preservan."
            ),
            "referenceId": None,
            "details": None,
        }
        return {
            "classified_references": classified_references,
            "warnings": [warning],
        }

    # --- Empty response short-circuit ---
    if not batch_output.adjudications:
        logger.info("ai_adjudicate_empty_response")
        return {"classified_references": classified_references}

    # --- Response application ---
    # Build index from referenceId → adjudication result
    adjudication_by_id: dict[str, AdjudicationResult] = {}
    for adj_result in batch_output.adjudications:
        if adj_result.reference_id not in eligible_ids:
            logger.warning(
                "ai_adjudicate_unknown_reference_id",
                reference_id=adj_result.reference_id,
            )
            continue
        adjudication_by_id[adj_result.reference_id] = adj_result

    # Apply adjudications and merge back into the full list (preserving order)
    adjudicated_count = 0
    classifications_changed = 0
    classifications_preserved = 0

    updated_by_id: dict[str, dict] = {}
    for ref in eligible_sorted:
        ref_id = ref.get("referenceId", "")
        adj = adjudication_by_id.get(ref_id)
        if adj is None:
            # LLM returned fewer adjudications than sent — keep deterministic
            updated_by_id[ref_id] = ref
            classifications_preserved += 1
            continue

        old_cls = ref.get("classification", "")
        updated_ref = _apply_adjudication_result(ref, adj)
        new_cls = updated_ref.get("classification", "")

        updated_by_id[ref_id] = updated_ref
        adjudicated_count += 1
        if old_cls != new_cls:
            classifications_changed += 1
        else:
            classifications_preserved += 1

    # Merge back: replace eligible refs in place, keep non-eligible unchanged
    merged: list[dict] = []
    for ref in classified_references:
        ref_id = ref.get("referenceId", "")
        if ref_id in updated_by_id:
            merged.append(updated_by_id[ref_id])
        else:
            merged.append(ref)

    logger.info(
        "ai_adjudicate_complete",
        adjudicated_count=adjudicated_count,
        classifications_changed=classifications_changed,
        classifications_preserved=classifications_preserved,
    )

    return {"classified_references": merged}
