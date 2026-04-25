"""Tests for the classification engine (Step 09).

Covers all decision rules (1-10) and the compatibility matrix enforcement.
"""

from __future__ import annotations

import pytest

from biblio_checker_worker.langgraph.classification import classify_reference
from biblio_checker_worker.langgraph.schemas import MatchCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    *,
    source: str = "openalex",
    external_id: str = "W123",
    title: str | None = "Deep Learning for NLP",
    authors: list[str] | None = None,
    year: int | None = 2020,
    doi: str | None = None,
    url: str | None = "https://openalex.org/W123",
    match_type: str = "title_fuzzy",
    raw_score: float = 0.0,
) -> MatchCandidate:
    return MatchCandidate(
        source=source,
        external_id=external_id,
        title=title,
        authors=authors or ["Smith, Jane"],
        year=year,
        doi=doi,
        url=url,
        match_type=match_type,
        raw_score=raw_score,
    )


def _base_normalized(
    *,
    title: str | None = "Deep Learning for NLP",
    authors: list[str] | None = None,
    year: int | None = 2020,
    venue: str | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
) -> dict:
    return {
        "title": title,
        "authors": authors or ["Smith, Jane"],
        "year": year,
        "venue": venue,
        "doi": doi,
        "arxivId": arxiv_id,
    }


# ---------------------------------------------------------------------------
# Rule 1 — Exact DOI Match → verified
# ---------------------------------------------------------------------------


class TestRule1ExactDOIMatch:
    def test_doi_exact_match_returns_verified(self) -> None:
        normalized = _base_normalized(doi="10.1234/example")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "verified"
        assert result["confidenceBand"] == "very_high"
        assert result["confidenceScore"] == pytest.approx(0.95)
        assert result["manualReviewRequired"] is False
        assert result["reasonCode"] == "exact_doi_match"
        assert "openalex" in result["decisionReason"]

    def test_doi_exact_match_source_name_in_reason(self) -> None:
        normalized = _base_normalized(doi="10.5678/test")
        candidate = _make_candidate(
            source="scielo",
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.5678/test",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "verified"
        assert "scielo" in result["decisionReason"]


# ---------------------------------------------------------------------------
# Rule 2 — Exact Identifier Match → verified
# ---------------------------------------------------------------------------


class TestRule2ExactIdentifierMatch:
    def test_identifier_exact_match_returns_verified(self) -> None:
        normalized = _base_normalized(arxiv_id="2301.12345")
        candidate = _make_candidate(
            source="arxiv",
            match_type="identifier_exact",
            raw_score=1.0,
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "verified"
        assert result["confidenceBand"] == "very_high"
        assert result["confidenceScore"] == pytest.approx(0.93)
        assert result["manualReviewRequired"] is False
        assert result["reasonCode"] == "exact_identifier_match"
        assert "arXiv" in result["decisionReason"]


# ---------------------------------------------------------------------------
# Rule 3 — DOI Conflict → suspicious
# ---------------------------------------------------------------------------


class TestRule3DOIConflict:
    def test_doi_found_but_title_too_different_returns_suspicious(self) -> None:
        normalized = _base_normalized(
            title="Deep Learning for NLP",
            year=2020,
            doi="10.1234/example",
        )
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
            # Completely different title → similarity < 0.5
            title="Renaissance Painting Techniques in the 15th Century",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "suspicious"
        assert result["confidenceBand"] == "high"
        assert result["manualReviewRequired"] is True
        assert result["reasonCode"] == "strong_doi_conflict"

    def test_doi_found_but_year_conflict_returns_suspicious(self) -> None:
        normalized = _base_normalized(
            title="Deep Learning for NLP",
            year=2020,
            doi="10.1234/example",
        )
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
            title="Deep Learning for NLP",
            year=2015,  # differs by 5 > 2
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "suspicious"
        assert result["reasonCode"] == "strong_doi_conflict"


# ---------------------------------------------------------------------------
# Rule 4 — Cross-Source Metadata Conflict → suspicious
# ---------------------------------------------------------------------------


class TestRule4CrossSourceMetadataConflict:
    def test_two_sources_conflicting_year_returns_suspicious(self) -> None:
        normalized = _base_normalized(title="Deep Learning for NLP")
        c1 = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.90,
            title="Deep Learning for NLP",
            year=2018,
            doi="10.1111/aaa",
        )
        c2 = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.88,
            title="Deep Learning for NLP",
            year=2024,  # differs by 6 > 2
            doi="10.2222/bbb",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["classification"] == "suspicious"
        assert result["reasonCode"] == "cross_source_metadata_conflict"
        assert result["manualReviewRequired"] is True

    def test_two_sources_same_metadata_does_not_trigger_conflict(self) -> None:
        normalized = _base_normalized(title="Deep Learning for NLP")
        c1 = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.90,
            title="Deep Learning for NLP",
            year=2020,
        )
        c2 = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.87,
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        # No conflict → should fall through to Rule 5 (strong metadata match)
        assert result["classification"] != "suspicious"


# ---------------------------------------------------------------------------
# Rule 5 — Strong Metadata Match → likely_verified
# ---------------------------------------------------------------------------


class TestRule5StrongMetadataMatch:
    def test_score_above_0_85_returns_likely_verified(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.92)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "likely_verified"
        assert result["confidenceBand"] == "high"  # >= 0.90
        assert result["manualReviewRequired"] is False
        assert result["reasonCode"] == "strong_metadata_match"

    def test_score_exactly_0_85_returns_likely_verified_medium_band(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.85)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "likely_verified"
        assert result["confidenceBand"] == "medium"  # 0.85 < 0.90

    def test_dominant_candidate_above_0_85_triggers_rule5_not_rule6(self) -> None:
        """Two candidates: scores 0.90 and 0.60 — top candidate dominates (> 0.15 gap)."""
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.90, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.60, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["classification"] == "likely_verified"


# ---------------------------------------------------------------------------
# Rule 5b — Single Moderate Match → ambiguous
# ---------------------------------------------------------------------------


class TestRule5bSingleModerateMatch:
    def test_single_candidate_0_65_returns_ambiguous_medium(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.65)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "ambiguous"
        assert result["confidenceBand"] == "medium"
        assert result["manualReviewRequired"] is True
        assert result["reasonCode"] == "single_moderate_match"

    def test_single_candidate_0_55_returns_ambiguous_low(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.55)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "ambiguous"
        assert result["confidenceBand"] == "low"  # 0.55 < 0.65

    def test_single_candidate_below_0_50_does_not_trigger_5b(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.30)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        # Should fall through to rule 7 or 8
        assert result["classification"] == "not_found"


# ---------------------------------------------------------------------------
# Rule 6 — Multiple Plausible Candidates → ambiguous
# ---------------------------------------------------------------------------


class TestRule6MultiplePlausibleCandidates:
    def test_two_candidates_within_0_15_returns_ambiguous(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.75, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.72, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["classification"] == "ambiguous"
        assert result["reasonCode"] == "multiple_plausible_candidates"
        assert result["manualReviewRequired"] is True

    def test_ambiguous_confidence_band_medium_when_score_above_0_65(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.75, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.70, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["confidenceBand"] == "medium"

    def test_ambiguous_confidence_band_low_when_scores_below_0_65(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.60, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.55, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["confidenceBand"] == "low"


# ---------------------------------------------------------------------------
# Rule 7 — Insufficient Metadata → not_found
# ---------------------------------------------------------------------------


class TestRule7InsufficientMetadata:
    def test_no_title_no_doi_no_arxiv_returns_not_found(self) -> None:
        normalized = _base_normalized(title=None, doi=None, arxiv_id=None)
        result = classify_reference(
            normalized=normalized,
            candidates=[],
            source_errors={},
        )
        assert result["classification"] == "not_found"
        assert result["reasonCode"] == "insufficient_metadata"
        assert result["confidenceBand"] == "very_low"
        assert result["manualReviewRequired"] is True


# ---------------------------------------------------------------------------
# Rule 8 — No Match in Any Source → not_found
# ---------------------------------------------------------------------------


class TestRule8NoMatchAnySource:
    def test_no_candidates_returns_not_found(self) -> None:
        normalized = _base_normalized()
        result = classify_reference(
            normalized=normalized,
            candidates=[],
            source_errors={},
        )
        assert result["classification"] == "not_found"
        assert result["reasonCode"] == "no_match_any_source"
        assert result["confidenceBand"] == "low"  # no errors → "low"

    def test_no_match_with_errors_returns_not_found_very_low(self) -> None:
        normalized = _base_normalized()
        result = classify_reference(
            normalized=normalized,
            candidates=[],
            source_errors={"openalex": "timeout"},
        )
        # source_errors non-empty but candidates empty → source_timeout_partial takes precedence
        assert result["classification"] == "not_found"
        assert result["reasonCode"] == "source_timeout_partial"
        assert result["confidenceBand"] == "very_low"

    def test_all_candidates_below_0_50_returns_not_found(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.30)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "not_found"
        assert result["reasonCode"] == "no_match_any_source"


# ---------------------------------------------------------------------------
# Rule 9 — Source Timeout with Partial Evidence
# ---------------------------------------------------------------------------


class TestRule9SourceTimeoutPartialEvidence:
    def test_all_sources_errored_no_candidates_returns_source_timeout_partial(
        self,
    ) -> None:
        normalized = _base_normalized()
        result = classify_reference(
            normalized=normalized,
            candidates=[],
            source_errors={
                "openalex": "timeout",
                "scielo": "timeout",
                "arxiv": "timeout",
            },
        )
        assert result["classification"] == "not_found"
        assert result["reasonCode"] == "source_timeout_partial"
        assert result["confidenceBand"] == "very_low"

    def test_one_source_errored_but_other_has_strong_match_uses_available_evidence(
        self,
    ) -> None:
        """One source errors; another provides a strong match → Rule 5 applies."""
        normalized = _base_normalized()
        candidate = _make_candidate(
            source="openalex", match_type="title_fuzzy", raw_score=0.92
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={"scielo": "timeout"},
        )
        # Evidence from openalex is strong → likely_verified, not source_timeout_partial
        assert result["classification"] == "likely_verified"


# ---------------------------------------------------------------------------
# Evidence assembly
# ---------------------------------------------------------------------------


class TestEvidenceAssembly:
    def test_candidates_above_0_50_included_in_evidence(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.80, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.30, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        sources_in_evidence = {e["source"] for e in result["evidence"]}
        assert "openalex" in sources_in_evidence
        assert "scielo" not in sources_in_evidence  # score < 0.50

    def test_exact_matches_always_included_in_evidence(self) -> None:
        normalized = _base_normalized(doi="10.1234/exact")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=0.0,  # raw_score 0 but should be included (exact match)
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["matchType"] == "doi_exact"

    def test_low_score_non_exact_excluded_from_evidence(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.20)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["evidence"] == []


# ---------------------------------------------------------------------------
# Compatibility matrix
# ---------------------------------------------------------------------------


class TestCompatibilityMatrix:
    """Verify output passes the ReferenceResult Pydantic compatibility validator."""

    def _validate_result(self, result: dict, ref_id: str = "ref-001") -> None:
        from biblio_checker_worker.langgraph.schemas import ReferenceResult

        ReferenceResult(
            referenceId=ref_id,
            rawText="Some raw reference text for testing purposes",
            normalized={
                "title": "Test",
                "authors": [],
                "year": None,
                "venue": None,
                "doi": None,
                "arxivId": None,
            },
            **result,
        )

    def test_verified_result_passes_validator(self) -> None:
        normalized = _base_normalized(doi="10.1234/test")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        self._validate_result(result)

    def test_likely_verified_result_passes_validator(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.90)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        self._validate_result(result)

    def test_ambiguous_result_passes_validator(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.70, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.68, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        self._validate_result(result)

    def test_not_found_result_passes_validator(self) -> None:
        normalized = _base_normalized()
        result = classify_reference(
            normalized=normalized,
            candidates=[],
            source_errors={},
        )
        self._validate_result(result)

    def test_suspicious_result_passes_validator(self) -> None:
        normalized = _base_normalized(
            doi="10.1234/conflict", title="Deep Learning for NLP"
        )
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/conflict",
            title="Unrelated paper about medieval art",  # low similarity → conflict
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        self._validate_result(result)

    def test_single_moderate_match_result_passes_validator(self) -> None:
        """Rule 5b: single_moderate_match reason code must be in the ReasonCode enum."""
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.65)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["reasonCode"] == "single_moderate_match"
        self._validate_result(result)


# ---------------------------------------------------------------------------
# Phase A — Enriched decisionReason (Step 02)
# ---------------------------------------------------------------------------


class TestRule1EnrichedDecisionReason:
    """Rule 1 (exact DOI match): decisionReason must embed match-specific data."""

    def test_reason_contains_doi_value(self) -> None:
        normalized = _base_normalized(doi="10.1234/test")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "10.1234/test" in result["decisionReason"]

    def test_reason_contains_matched_title(self) -> None:
        normalized = _base_normalized(doi="10.1234/test")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "Deep Learning for NLP" in result["decisionReason"]

    def test_reason_contains_source_name(self) -> None:
        normalized = _base_normalized(doi="10.1234/test")
        candidate = _make_candidate(
            source="openalex",
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "openalex" in result["decisionReason"]

    def test_reason_contains_year_when_available(self) -> None:
        normalized = _base_normalized(doi="10.1234/test", year=2020)
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "2020" in result["decisionReason"]

    def test_reason_omits_year_when_candidate_year_is_null(self) -> None:
        normalized = _base_normalized(doi="10.1234/test", year=2020)
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title="Deep Learning for NLP",
            year=None,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        # Year parenthetical must not appear — "2020" from the reference year
        # must not be present since it should only come from the candidate year
        assert "(2020)" not in result["decisionReason"]

    def test_reason_omits_title_when_candidate_title_is_null(self) -> None:
        normalized = _base_normalized(doi="10.1234/test")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/test",
            title=None,
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        # No title snippet means no quoted title segment in the message
        assert "'" not in result["decisionReason"]


class TestRule2EnrichedDecisionReason:
    """Rule 2 (exact arXiv identifier match): decisionReason must embed match-specific data."""

    def test_reason_contains_arxiv_id(self) -> None:
        # normalized year=2020 and candidate year=2020: within tolerance
        normalized = _base_normalized(arxiv_id="2301.12345", year=2020)
        candidate = _make_candidate(
            source="arxiv",
            match_type="identifier_exact",
            raw_score=1.0,
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "2301.12345" in result["decisionReason"]

    def test_reason_contains_matched_title(self) -> None:
        normalized = _base_normalized(arxiv_id="2301.12345", year=2020)
        candidate = _make_candidate(
            source="arxiv",
            match_type="identifier_exact",
            raw_score=1.0,
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "Deep Learning for NLP" in result["decisionReason"]

    def test_reason_contains_year_when_available(self) -> None:
        normalized = _base_normalized(arxiv_id="2301.12345", year=2020)
        candidate = _make_candidate(
            source="arxiv",
            match_type="identifier_exact",
            raw_score=1.0,
            title="Deep Learning for NLP",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "2020" in result["decisionReason"]

    def test_reason_omits_year_when_candidate_year_is_null(self) -> None:
        # When candidate year is None, year parenthetical must not appear
        normalized = _base_normalized(arxiv_id="2301.12345", year=2020)
        candidate = _make_candidate(
            source="arxiv",
            match_type="identifier_exact",
            raw_score=1.0,
            title="Deep Learning for NLP",
            year=None,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "(2020)" not in result["decisionReason"]

    def test_reason_omits_title_when_candidate_title_is_null(self) -> None:
        # candidate title None; year consistent so Rule 2 fires
        normalized = _base_normalized(arxiv_id="2301.12345", year=2020)
        candidate = _make_candidate(
            source="arxiv",
            match_type="identifier_exact",
            raw_score=1.0,
            title=None,
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "'" not in result["decisionReason"]


class TestRule3EnrichedDecisionReason:
    """Rule 3 (DOI conflict): decisionReason must name both matched and reference titles."""

    def test_title_conflict_reason_contains_both_titles(self) -> None:
        """Title-only conflict: matched title and reference title both appear."""
        normalized = _base_normalized(
            title="Deep Learning for NLP",
            year=2020,
            doi="10.1234/example",
        )
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
            title="Renaissance Painting Techniques in the 15th Century",
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert (
            "Renaissance Painting Techniques in the 15th Century"
            in result["decisionReason"]
        )
        assert "Deep Learning for NLP" in result["decisionReason"]

    def test_year_conflict_only_reason_reflects_year_divergence(self) -> None:
        """Year-only conflict: matched year and reference year both appear."""
        normalized = _base_normalized(
            title="Deep Learning for NLP",
            year=2020,
            doi="10.1234/example",
        )
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
            title="Deep Learning for NLP",
            year=2015,  # year differs by 5
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        # Both years must appear in the message to reflect the divergence
        assert "2015" in result["decisionReason"]
        assert "2020" in result["decisionReason"]

    def test_title_and_year_conflict_reason_contains_both_fields(self) -> None:
        """Title+year conflict: all four data points appear."""
        normalized = _base_normalized(
            title="Deep Learning for NLP",
            year=2020,
            doi="10.1234/example",
        )
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/example",
            title="Renaissance Painting Techniques in the 15th Century",
            year=2010,  # year differs by 10
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert (
            "Renaissance Painting Techniques in the 15th Century"
            in result["decisionReason"]
        )
        assert "Deep Learning for NLP" in result["decisionReason"]
        assert "2010" in result["decisionReason"]
        assert "2020" in result["decisionReason"]


class TestRule4EnrichedDecisionReason:
    """Rule 4 (cross-source conflict): decisionReason must name conflicting sources."""

    def test_reason_names_both_conflicting_sources(self) -> None:
        normalized = _base_normalized(title="Deep Learning for NLP")
        c1 = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.90,
            title="Deep Learning for NLP",
            year=2018,
            doi="10.1111/aaa",
        )
        c2 = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.88,
            title="Deep Learning for NLP",
            year=2024,
            doi="10.2222/bbb",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert "openalex" in result["decisionReason"]
        assert "scielo" in result["decisionReason"]

    def test_reason_describes_year_conflict(self) -> None:
        """When only years conflict, the message names both years."""
        normalized = _base_normalized(title="Deep Learning for NLP")
        c1 = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.90,
            title="Deep Learning for NLP",
            year=2018,
            doi=None,
        )
        c2 = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.88,
            title="Deep Learning for NLP",
            year=2024,
            doi=None,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert "2018" in result["decisionReason"]
        assert "2024" in result["decisionReason"]

    def test_reason_describes_doi_conflict(self) -> None:
        """When only DOIs conflict, the message mentions DOI divergence."""
        normalized = _base_normalized(title="Deep Learning for NLP")
        c1 = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.90,
            title="Deep Learning for NLP",
            year=2020,
            doi="10.1111/aaa",
        )
        c2 = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.88,
            title="Deep Learning for NLP",
            year=2020,
            doi="10.2222/bbb",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert (
            "DOI" in result["decisionReason"]
            or "doi" in result["decisionReason"].lower()
        )

    def test_reason_describes_year_and_doi_conflict(self) -> None:
        """When both years and DOIs conflict, the message reflects both."""
        normalized = _base_normalized(title="Deep Learning for NLP")
        c1 = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.90,
            title="Deep Learning for NLP",
            year=2018,
            doi="10.1111/aaa",
        )
        c2 = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.88,
            title="Deep Learning for NLP",
            year=2024,
            doi="10.2222/bbb",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        # "los años y DOIs difieren" covers both
        reason = result["decisionReason"]
        assert ("años" in reason or "year" in reason.lower()) and (
            "DOI" in reason or "doi" in reason.lower()
        )


class TestRules5And5bEnrichedDecisionReason:
    """Rules 5 and 5b: decisionReason must contain score percentage and candidate title."""

    def test_rule5_reason_contains_score_as_percentage(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.92)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "92%" in result["decisionReason"]

    def test_rule5_reason_contains_candidate_title(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(
            match_type="title_fuzzy",
            raw_score=0.92,
            title="Deep Learning for NLP",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "Deep Learning for NLP" in result["decisionReason"]

    def test_rule5_reason_contains_source_name(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(
            source="openalex",
            match_type="title_fuzzy",
            raw_score=0.92,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "openalex" in result["decisionReason"]

    def test_rule5b_reason_contains_score_as_percentage(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.65)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["reasonCode"] == "single_moderate_match"
        assert "65%" in result["decisionReason"]

    def test_rule5b_reason_contains_candidate_title(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(
            match_type="title_fuzzy",
            raw_score=0.65,
            title="Deep Learning for NLP",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["reasonCode"] == "single_moderate_match"
        assert "Deep Learning for NLP" in result["decisionReason"]

    def test_rule5b_reason_contains_source_name(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(
            source="scielo",
            match_type="title_fuzzy",
            raw_score=0.65,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["reasonCode"] == "single_moderate_match"
        assert "scielo" in result["decisionReason"]


class TestRule6EnrichedDecisionReason:
    """Rule 6: decisionReason must contain count, top-2 titles, sources, and scores (Branch A)
    or use single-candidate format (Branch B)."""

    def test_rule6a_reason_contains_candidate_count(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.75, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.72, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["reasonCode"] == "multiple_plausible_candidates"
        assert "2" in result["decisionReason"]

    def test_rule6a_reason_contains_top_two_sources(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex",
            raw_score=0.75,
            match_type="title_fuzzy",
            title="Deep Learning for NLP",
        )
        c2 = _make_candidate(
            source="scielo",
            raw_score=0.72,
            match_type="title_fuzzy",
            title="Deep Learning for NLP",
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert "openalex" in result["decisionReason"]
        assert "scielo" in result["decisionReason"]

    def test_rule6a_reason_contains_both_scores_as_percentages(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex", raw_score=0.75, match_type="title_fuzzy"
        )
        c2 = _make_candidate(source="scielo", raw_score=0.72, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert "75%" in result["decisionReason"]
        assert "72%" in result["decisionReason"]

    def test_rule6b_dominant_candidate_uses_single_candidate_format(self) -> None:
        """Branch B: dominant candidate (score gap > 0.15, score >= 0.85) → Rule 5 format."""
        normalized = _base_normalized()
        c1 = _make_candidate(
            source="openalex",
            raw_score=0.90,
            match_type="title_fuzzy",
            title="Deep Learning for NLP",
        )
        c2 = _make_candidate(source="scielo", raw_score=0.60, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        assert result["classification"] == "likely_verified"
        assert result["reasonCode"] == "strong_metadata_match"
        assert "90%" in result["decisionReason"]
        assert "openalex" in result["decisionReason"]


class TestTitleTruncationInDecisionReason:
    """Title truncation: exactly 80 chars → no truncation; 81 chars → 77 + '...'."""

    def test_title_exactly_80_chars_is_not_truncated(self) -> None:
        title_80 = "A" * 80
        assert len(title_80) == 80
        normalized = _base_normalized(doi="10.1234/trunc")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/trunc",
            title=title_80,
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert title_80 in result["decisionReason"]
        assert "..." not in result["decisionReason"]

    def test_title_81_chars_is_truncated_to_77_plus_ellipsis(self) -> None:
        title_81 = "B" * 81
        expected_snippet = "B" * 77 + "..."
        normalized = _base_normalized(doi="10.1234/trunc81")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/trunc81",
            title=title_81,
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert expected_snippet in result["decisionReason"]
        assert title_81 not in result["decisionReason"]

    def test_null_title_omitted_gracefully_in_doi_rules(self) -> None:
        """When candidate title is None, the decisionReason must not embed 'None'.

        Note: a null candidate title causes title_similarity to return 0.0, which
        fails Rule 1's consistency check (title_sim >= 0.5). Rule 3 fires instead.
        The spec requires that null titles are omitted gracefully from all rule
        messages — this test verifies that property for the rule that fires.
        """
        normalized = _base_normalized(doi="10.1234/null-title")
        candidate = _make_candidate(
            match_type="doi_exact",
            raw_score=1.0,
            doi="10.1234/null-title",
            title=None,
            year=2020,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "None" not in result["decisionReason"]
        assert len(result["decisionReason"]) >= 1

    def test_null_title_omitted_gracefully_in_rule5(self) -> None:
        """When candidate title is None, Rule 5 must not embed 'None' in the message."""
        normalized = _base_normalized()
        candidate = _make_candidate(
            match_type="title_fuzzy",
            raw_score=0.92,
            title=None,
        )
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert result["classification"] == "likely_verified"
        assert "None" not in result["decisionReason"]
        assert len(result["decisionReason"]) >= 1


class TestScoreFormattingInDecisionReason:
    """Score formatting: float 0.0–1.0 must appear as integer percentage."""

    def test_score_0_92_formats_as_92_percent(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.92)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        assert "92%" in result["decisionReason"]

    def test_score_1_0_formats_as_100_percent(self) -> None:
        normalized = _base_normalized()
        c1 = _make_candidate(source="openalex", raw_score=1.0, match_type="title_fuzzy")
        c2 = _make_candidate(source="scielo", raw_score=0.90, match_type="title_fuzzy")
        result = classify_reference(
            normalized=normalized,
            candidates=[c1, c2],
            source_errors={},
        )
        # Rule 6B: dominant candidate with score 1.0 → "100%"
        assert "100%" in result["decisionReason"]

    def test_score_0_5_formats_as_50_percent(self) -> None:
        normalized = _base_normalized()
        candidate = _make_candidate(match_type="title_fuzzy", raw_score=0.50)
        result = classify_reference(
            normalized=normalized,
            candidates=[candidate],
            source_errors={},
        )
        # Single candidate at 0.50 → Rule 5b
        assert result["reasonCode"] == "single_moderate_match"
        assert "50%" in result["decisionReason"]
