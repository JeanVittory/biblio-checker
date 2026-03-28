"""Classification engine for bibliographic reference verification.

Applies priority-ordered deterministic rules to assign a classification
(verified, likely_verified, ambiguous, not_found, suspicious) to each
reference based on evidence collected from API lookups.

Classification logic is LLM-free — pure Python decision rules.
"""
from __future__ import annotations

from biblio_checker_worker.langgraph.schemas import MatchCandidate
from biblio_checker_worker.langgraph.scoring import title_similarity


# ---------------------------------------------------------------------------
# Evidence assembly
# ---------------------------------------------------------------------------

def _build_evidence(candidates: list[MatchCandidate]) -> list[dict]:
    """Return evidence items for candidates with meaningful scores or exact matches."""
    evidence = []
    for candidate in candidates:
        if candidate.raw_score >= 0.50 or candidate.match_type in (
            "doi_exact",
            "identifier_exact",
        ):
            evidence.append(
                {
                    "source": candidate.source,
                    "matchType": candidate.match_type,
                    "score": candidate.raw_score,
                    "matchedRecord": {
                        "externalId": candidate.external_id,
                        "title": candidate.title,
                        "year": candidate.year,
                        "doi": candidate.doi,
                        "url": candidate.url,
                    },
                }
            )
    return evidence


# ---------------------------------------------------------------------------
# Main classification function
# ---------------------------------------------------------------------------

def classify_reference(
    *,
    normalized: dict,
    candidates: list[MatchCandidate],
    source_errors: dict[str, str],
) -> dict:
    """Classify a reference based on evidence from API lookups.

    Args:
        normalized: The normalized reference metadata with keys:
            title, authors, year, venue, doi, arxivId
        candidates: All MatchCandidate objects collected from all sources.
        source_errors: Map of source name -> error message for sources
            that failed or timed out.

    Returns:
        dict with keys: classification, confidenceScore, confidenceBand,
            manualReviewRequired, reasonCode, decisionReason, evidence
    """
    doi = normalized.get("doi")
    arxiv_id = normalized.get("arxivId")
    title = normalized.get("title")

    evidence = _build_evidence(candidates)

    # --- Rule 1: Exact DOI Match → verified ----------------------------------
    if doi is not None:
        for c in candidates:
            if c.match_type == "doi_exact":
                # Verify candidate metadata is consistent with reference
                title_sim = title_similarity(title, c.title)
                year_diff = (
                    abs((normalized.get("year") or 0) - (c.year or 0))
                    if normalized.get("year") is not None and c.year is not None
                    else None
                )
                consistent = (title_sim >= 0.5) and (
                    year_diff is None or year_diff <= 2
                )
                if consistent:
                    return {
                        "classification": "verified",
                        "confidenceScore": 0.95,
                        "confidenceBand": "very_high",
                        "manualReviewRequired": False,
                        "reasonCode": "exact_doi_match",
                        "decisionReason": (
                            f"El DOI coincide exactamente con un registro canónico en {c.source}."
                        ),
                        "evidence": evidence,
                    }

    # --- Rule 2: Exact Identifier Match → verified ---------------------------
    if arxiv_id is not None:
        for c in candidates:
            if c.match_type == "identifier_exact":
                title_sim = title_similarity(title, c.title)
                year_diff = (
                    abs((normalized.get("year") or 0) - (c.year or 0))
                    if normalized.get("year") is not None and c.year is not None
                    else None
                )
                consistent = (title_sim >= 0.5) and (
                    year_diff is None or year_diff <= 2
                )
                if consistent:
                    return {
                        "classification": "verified",
                        "confidenceScore": 0.93,
                        "confidenceBand": "very_high",
                        "manualReviewRequired": False,
                        "reasonCode": "exact_identifier_match",
                        "decisionReason": (
                            "El identificador arXiv coincide exactamente con un registro en arXiv."
                        ),
                        "evidence": evidence,
                    }

    # --- Rule 3: DOI Conflict → suspicious -----------------------------------
    if doi is not None:
        for c in candidates:
            if c.match_type == "doi_exact":
                title_sim = title_similarity(title, c.title)
                year_diff = (
                    abs((normalized.get("year") or 0) - (c.year or 0))
                    if normalized.get("year") is not None and c.year is not None
                    else None
                )
                conflicting = (title_sim < 0.5) or (
                    year_diff is not None and year_diff > 2
                )
                if conflicting:
                    return {
                        "classification": "suspicious",
                        "confidenceScore": 0.90,
                        "confidenceBand": "high",
                        "manualReviewRequired": True,
                        "reasonCode": "strong_doi_conflict",
                        "decisionReason": (
                            "El DOI citado apunta a un trabajo incompatible con el título o año "
                            "reportados. Esto puede indicar una referencia fabricada."
                        ),
                        "evidence": evidence,
                    }

    # --- Rule 4: Cross-Source Metadata Conflict → suspicious -----------------
    # Collect candidates from distinct sources that have high title similarity
    high_sim_by_source: dict[str, list[MatchCandidate]] = {}
    for c in candidates:
        if title_similarity(title, c.title) >= 0.85:
            high_sim_by_source.setdefault(c.source, []).append(c)

    if len(high_sim_by_source) >= 2:
        source_list = list(high_sim_by_source.values())
        # Check for conflicting metadata between the best candidates of different sources
        conflict_found = False
        for i in range(len(source_list)):
            best_i = max(source_list[i], key=lambda c: c.raw_score)
            for j in range(i + 1, len(source_list)):
                best_j = max(source_list[j], key=lambda c: c.raw_score)
                # Conflict if years differ by > 2 or DOIs differ (and both are set)
                year_conflict = (
                    best_i.year is not None
                    and best_j.year is not None
                    and abs(best_i.year - best_j.year) > 2
                )
                doi_conflict = (
                    best_i.doi is not None
                    and best_j.doi is not None
                    and best_i.doi != best_j.doi
                )
                if year_conflict or doi_conflict:
                    conflict_found = True
                    break
            if conflict_found:
                break

        if conflict_found:
            return {
                "classification": "suspicious",
                "confidenceScore": 0.85,
                "confidenceBand": "high",
                "manualReviewRequired": True,
                "reasonCode": "cross_source_metadata_conflict",
                "decisionReason": (
                    "Múltiples fuentes encontraron trabajos similares pero con metadatos "
                    "contradictorios entre sí."
                ),
                "evidence": evidence,
            }

    # --- Rule 5: Strong Metadata Match → likely_verified ---------------------
    # No DOI/identifier available, but at least one candidate >= 0.85
    scored_candidates = [c for c in candidates if c.raw_score >= 0.85]
    if scored_candidates and doi is None and arxiv_id is None:
        best = max(scored_candidates, key=lambda c: c.raw_score)
        best_score = best.raw_score
        confidence_band = "high" if best_score >= 0.90 else "medium"
        return {
            "classification": "likely_verified",
            "confidenceScore": best_score,
            "confidenceBand": confidence_band,
            "manualReviewRequired": False,
            "reasonCode": "strong_metadata_match",
            "decisionReason": (
                f"Se encontró una coincidencia fuerte por título y autores en {best.source}, "
                "aunque sin identificador canónico."
            ),
            "evidence": evidence,
        }

    # Gather all candidates with score >= 0.50 for Rules 5b and 6
    plausible = [c for c in candidates if c.raw_score >= 0.50]

    # --- Rule 5b: Single Moderate Match → ambiguous --------------------------
    if len(plausible) == 1 and doi is None and arxiv_id is None:
        best = plausible[0]
        best_score = best.raw_score
        confidence_band = "medium" if best_score >= 0.65 else "low"
        return {
            "classification": "ambiguous",
            "confidenceScore": best_score,
            "confidenceBand": confidence_band,
            "manualReviewRequired": True,
            "reasonCode": "single_moderate_match",
            "decisionReason": (
                "Se encontró un candidato con coincidencia moderada, pero no suficiente para "
                "confirmar la referencia."
            ),
            "evidence": evidence,
        }

    # --- Rule 6: Multiple Plausible Candidates → ambiguous -------------------
    if len(plausible) >= 2:
        sorted_plausible = sorted(plausible, key=lambda c: c.raw_score, reverse=True)
        top_score = sorted_plausible[0].raw_score
        second_score = sorted_plausible[1].raw_score
        # Top two are within 0.15 of each other — no single dominant candidate
        if top_score - second_score <= 0.15:
            confidence_band = "medium" if top_score >= 0.65 else "low"
            return {
                "classification": "ambiguous",
                "confidenceScore": top_score,
                "confidenceBand": confidence_band,
                "manualReviewRequired": True,
                "reasonCode": "multiple_plausible_candidates",
                "decisionReason": (
                    "Se encontraron múltiples candidatos plausibles pero ninguno es lo "
                    "suficientemente concluyente."
                ),
                "evidence": evidence,
            }
        # One candidate clearly dominates — fall through to strong match check
        best = sorted_plausible[0]
        best_score = best.raw_score
        if best_score >= 0.85:
            confidence_band = "high" if best_score >= 0.90 else "medium"
            return {
                "classification": "likely_verified",
                "confidenceScore": best_score,
                "confidenceBand": confidence_band,
                "manualReviewRequired": False,
                "reasonCode": "strong_metadata_match",
                "decisionReason": (
                    f"Se encontró una coincidencia fuerte por título y autores en {best.source}, "
                    "aunque sin identificador canónico."
                ),
                "evidence": evidence,
            }

    # --- Rule 7: Insufficient Metadata → not_found ---------------------------
    if title is None and doi is None and arxiv_id is None:
        return {
            "classification": "not_found",
            "confidenceScore": 0.10,
            "confidenceBand": "very_low",
            "manualReviewRequired": True,
            "reasonCode": "insufficient_metadata",
            "decisionReason": (
                "La referencia no contiene metadatos suficientes (título, DOI o identificador) "
                "para realizar una búsqueda confiable."
            ),
            "evidence": evidence,
        }

    # --- Rule 9: Source Timeout with all sources failed → not_found ----------
    # (Rule 9 re-runs rules 1-8 on available evidence; if we reach here with only
    # errors and no candidates, produce the timeout-specific not_found result.)
    if source_errors and not candidates:
        return {
            "classification": "not_found",
            "confidenceScore": 0.10,
            "confidenceBand": "very_low",
            "manualReviewRequired": True,
            "reasonCode": "source_timeout_partial",
            "decisionReason": (
                "Algunas fuentes no respondieron a tiempo. Los resultados pueden ser incompletos."
            ),
            "evidence": evidence,
        }

    # --- Rule 8: No Match in Any Source → not_found --------------------------
    confidence_band = "low" if not source_errors else "very_low"
    return {
        "classification": "not_found",
        "confidenceScore": 0.15,
        "confidenceBand": confidence_band,
        "manualReviewRequired": True,
        "reasonCode": "no_match_any_source",
        "decisionReason": (
            "No se encontraron coincidencias en ninguna fuente consultada "
            "(OpenAlex, SciELO, arXiv)."
        ),
        "evidence": evidence,
    }
