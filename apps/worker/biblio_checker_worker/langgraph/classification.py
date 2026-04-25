"""Classification engine for bibliographic reference verification.

Applies priority-ordered deterministic rules to assign a classification
(verified, likely_verified, ambiguous, not_found, suspicious) to each
reference based on evidence collected from API lookups.

Classification logic is LLM-free — pure Python decision rules.
"""

from __future__ import annotations

# Ensure catalog is loaded (side-effect import).
import biblio_checker_worker.langgraph.i18n_catalog.classification as _  # noqa: F401
from biblio_checker_worker.langgraph.i18n import render
from biblio_checker_worker.langgraph.schemas import MatchCandidate
from biblio_checker_worker.langgraph.scoring import title_similarity

# ---------------------------------------------------------------------------
# Message-building helpers
# ---------------------------------------------------------------------------


def _truncate_title(title: str | None, max_len: int = 80) -> str | None:
    """Return title truncated to max_len characters (with ellipsis if needed).

    Returns None if title is None.
    """
    if title is None:
        return None
    if len(title) > max_len:
        return title[:77] + "..."
    return title


def _score_pct(score: float) -> str:
    """Convert a 0.0–1.0 float score to an integer percentage string."""
    return f"{int(score * 100)}%"


def _single_candidate_reason(
    score: float,
    title: str | None,
    source: str,
    *,
    suffix_key: str,
    locale: str,
) -> str:
    """Build the standard single-candidate decisionReason string.

    Used by Rule 5 and Rule 6 Branch B.
    ``suffix_key`` is an i18n catalog key resolved via ``render()``.
    """
    title_snippet = _truncate_title(title)
    score_str = _score_pct(score)
    suffix = render(suffix_key, locale)
    if title_snippet is not None:
        return render(
            "class.match.single.with_title",
            locale,
            score=score_str,
            title=title_snippet,
            source=source,
            suffix=suffix,
        )
    return render(
        "class.match.single.no_title",
        locale,
        score=score_str,
        source=source,
        suffix=suffix,
    )


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
    locale: str = "es",
) -> dict:
    """Classify a reference based on evidence from API lookups.

    Args:
        normalized: The normalized reference metadata with keys:
            title, authors, year, venue, doi, arxivId
        candidates: All MatchCandidate objects collected from all sources.
        source_errors: Map of source name -> error message for sources
            that failed or timed out.
        locale: BCP-47 locale code for rendered strings. Defaults to ``"es"``.

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
                    _title_snip = _truncate_title(c.title)
                    _src = c.source
                    if _title_snip is not None and c.year is not None:
                        _r1_reason = render(
                            "class.doi_match.single.with_title_and_year",
                            locale,
                            doi=doi,
                            title=_title_snip,
                            year=str(c.year),
                            source=_src,
                        )
                    elif _title_snip is not None:
                        _r1_reason = render(
                            "class.doi_match.single.with_title_no_year",
                            locale,
                            doi=doi,
                            title=_title_snip,
                            source=_src,
                        )
                    elif c.year is not None:
                        _r1_reason = render(
                            "class.doi_match.single.no_title_with_year",
                            locale,
                            doi=doi,
                            year=str(c.year),
                            source=_src,
                        )
                    else:
                        _r1_reason = render(
                            "class.doi_match.single.no_title",
                            locale,
                            doi=doi,
                            source=_src,
                        )
                    return {
                        "classification": "verified",
                        "confidenceScore": 0.95,
                        "confidenceBand": "very_high",
                        "manualReviewRequired": False,
                        "reasonCode": "exact_doi_match",
                        "decisionReason": _r1_reason,
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
                    _title_snip = _truncate_title(c.title)
                    if _title_snip is not None and c.year is not None:
                        _r2_reason = render(
                            "class.arxiv_match.with_title_and_year",
                            locale,
                            arxiv_id=arxiv_id,
                            title=_title_snip,
                            year=str(c.year),
                        )
                    elif _title_snip is not None:
                        _r2_reason = render(
                            "class.arxiv_match.with_title_no_year",
                            locale,
                            arxiv_id=arxiv_id,
                            title=_title_snip,
                        )
                    elif c.year is not None:
                        _r2_reason = render(
                            "class.arxiv_match.no_title_with_year",
                            locale,
                            arxiv_id=arxiv_id,
                            year=str(c.year),
                        )
                    else:
                        _r2_reason = render(
                            "class.arxiv_match.no_title",
                            locale,
                            arxiv_id=arxiv_id,
                        )
                    return {
                        "classification": "verified",
                        "confidenceScore": 0.93,
                        "confidenceBand": "very_high",
                        "manualReviewRequired": False,
                        "reasonCode": "exact_identifier_match",
                        "decisionReason": _r2_reason,
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
                    _matched_snip = _truncate_title(c.title)
                    _ref_snip = _truncate_title(normalized.get("title"))
                    _matched_year = c.year
                    _ref_year = normalized.get("year")
                    _title_conflict = title_sim < 0.5
                    _year_conflict = year_diff is not None and year_diff > 2

                    _src = c.source
                    if _title_conflict and _year_conflict:
                        if _matched_snip is not None and _ref_snip is not None:
                            _m_yr_sfx = (
                                f" ({_matched_year})"
                                if _matched_year is not None
                                else ""
                            )
                            _r_yr_sfx = (
                                f" ({_ref_year})" if _ref_year is not None else ""
                            )
                            _r3_reason = render(
                                "class.doi_conflict.both_titles_both_years",
                                locale,
                                doi=doi,
                                matched_title=_matched_snip,
                                matched_year_suffix=_m_yr_sfx,
                                source=_src,
                                ref_title=_ref_snip,
                                ref_year_suffix=_r_yr_sfx,
                            )
                        else:
                            _r3_reason = render(
                                "class.doi_conflict.both_titles_both_years.no_snippets",
                                locale,
                                doi=doi,
                                source=_src,
                            )
                    elif _title_conflict:
                        if _matched_snip is not None and _ref_snip is not None:
                            _r3_reason = render(
                                "class.doi_conflict.title_only.both_snippets",
                                locale,
                                doi=doi,
                                matched_title=_matched_snip,
                                source=_src,
                                ref_title=_ref_snip,
                            )
                        else:
                            _r3_reason = render(
                                "class.doi_conflict.title_only.no_snippets",
                                locale,
                                doi=doi,
                                source=_src,
                            )
                    else:
                        # year conflict only
                        if _matched_year is not None and _ref_year is not None:
                            _r3_reason = render(
                                "class.doi_conflict.year_only.both_years",
                                locale,
                                doi=doi,
                                matched_year=str(_matched_year),
                                source=_src,
                                ref_year=str(_ref_year),
                            )
                        else:
                            _r3_reason = render(
                                "class.doi_conflict.year_only.no_years",
                                locale,
                                doi=doi,
                                source=_src,
                            )
                    return {
                        "classification": "suspicious",
                        "confidenceScore": 0.90,
                        "confidenceBand": "high",
                        "manualReviewRequired": True,
                        "reasonCode": "strong_doi_conflict",
                        "decisionReason": _r3_reason,
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
        # Check for conflicting metadata between best candidates of different sources
        conflict_found = False
        _conflict_best_i: MatchCandidate | None = None
        _conflict_best_j: MatchCandidate | None = None
        _conflict_year: bool = False
        _conflict_doi: bool = False
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
                    _conflict_best_i = best_i
                    _conflict_best_j = best_j
                    _conflict_year = year_conflict
                    _conflict_doi = doi_conflict
                    break
            if conflict_found:
                break

        _ci = _conflict_best_i
        _cj = _conflict_best_j
        if conflict_found and _ci is not None and _cj is not None:
            _source_a = _ci.source
            _source_b = _cj.source
            if _conflict_year and _conflict_doi:
                _conflict_detail = render(
                    "class.cross_source_conflict.detail.years_and_dois", locale
                )
            elif _conflict_year:
                _conflict_detail = render(
                    "class.cross_source_conflict.detail.years",
                    locale,
                    year_a=str(_ci.year),
                    year_b=str(_cj.year),
                )
            else:
                _conflict_detail = render(
                    "class.cross_source_conflict.detail.dois", locale
                )
            return {
                "classification": "suspicious",
                "confidenceScore": 0.85,
                "confidenceBand": "high",
                "manualReviewRequired": True,
                "reasonCode": "cross_source_metadata_conflict",
                "decisionReason": render(
                    "class.cross_source_conflict",
                    locale,
                    source_a=_source_a,
                    source_b=_source_b,
                    conflict_detail=_conflict_detail,
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
            "decisionReason": _single_candidate_reason(
                best_score,
                best.title,
                best.source,
                suffix_key="class.strong_metadata.suffix",
                locale=locale,
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
            "decisionReason": _single_candidate_reason(
                best_score,
                best.title,
                best.source,
                suffix_key="class.weak_metadata.suffix",
                locale=locale,
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
            _top1 = sorted_plausible[0]
            _top2 = sorted_plausible[1]
            _t1_snip = _truncate_title(_top1.title) or render(
                "class.no_title_placeholder", locale
            )
            _t2_snip = _truncate_title(_top2.title) or render(
                "class.no_title_placeholder", locale
            )
            _r6a_reason = render(
                "class.ambiguous_multi",
                locale,
                count=str(len(plausible)),
                title1=_t1_snip,
                score1=_score_pct(top_score),
                source1=_top1.source,
                title2=_t2_snip,
                score2=_score_pct(second_score),
                source2=_top2.source,
            )
            return {
                "classification": "ambiguous",
                "confidenceScore": top_score,
                "confidenceBand": confidence_band,
                "manualReviewRequired": True,
                "reasonCode": "multiple_plausible_candidates",
                "decisionReason": _r6a_reason,
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
                "decisionReason": _single_candidate_reason(
                    best_score,
                    best.title,
                    best.source,
                    suffix_key="class.strong_metadata.suffix",
                    locale=locale,
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
            "decisionReason": render("class.insufficient_metadata", locale),
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
            "decisionReason": render("class.source_timeout_not_found", locale),
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
        "decisionReason": render("class.not_found", locale),
        "evidence": evidence,
    }
