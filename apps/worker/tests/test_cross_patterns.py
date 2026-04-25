"""Tests for the analyze_cross_patterns node (Phase C, Steps 06 + 07).

Covers:
- Feature-flag gating
- Deterministic checks: venue cluster, DOI prefix cluster, self-citation anomaly,
  temporal impossibility
- Edge cases: empty refs, small ref lists, null fields
- LLM phase: conditional invocation, post-validation, graceful error handling
- Output structure conformance
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from biblio_checker_worker.langgraph.nodes.cross_patterns import (
    CrossPatternAnalysis,
    PatternInterpretation,
    _check_self_citation_anomaly,
    _check_suspicious_venue_cluster,
    _check_temporal_impossibility,
    _check_unregistered_doi_prefix_cluster,
    _extract_doi_prefix,
    _extract_last_name,
    _normalize_venue,
    analyze_cross_patterns,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(
    ref_id: str,
    classification: str = "not_found",
    venue: str | None = None,
    doi: str | None = None,
    authors: list[str] | None = None,
    year: int | None = None,
) -> dict:
    return {
        "referenceId": ref_id,
        "rawText": f"Raw text for {ref_id}",
        "normalized": {
            "title": f"Title {ref_id}",
            "authors": authors or [],
            "year": year,
            "venue": venue,
            "doi": doi,
            "arxivId": None,
        },
        "classification": classification,
        "confidenceScore": 0.1,
        "confidenceBand": "very_low",
        "manualReviewRequired": True,
        "reasonCode": "no_match_any_source",
        "decisionReason": "No match found.",
        "evidence": [],
    }


def _make_state(refs: list[dict]) -> dict:
    return {"classified_references": refs}


# ---------------------------------------------------------------------------
# Unit: _normalize_venue
# ---------------------------------------------------------------------------


class TestNormalizeVenue:
    def test_lowercase(self) -> None:
        assert _normalize_venue("Nature") == "nature"

    def test_strips_whitespace(self) -> None:
        assert _normalize_venue("  Nature  ") == "nature"

    def test_removes_periods(self) -> None:
        assert _normalize_venue("Rev. Lit.") == "rev lit"

    def test_removes_commas(self) -> None:
        assert _normalize_venue("Science, Nature") == "science nature"

    def test_collapses_spaces(self) -> None:
        assert _normalize_venue("Rev  Lit   Hispánica") == "rev lit hispánica"

    def test_full_normalization(self) -> None:
        # Three different venue strings that each normalize differently
        assert _normalize_venue("Rev. Lit. Hispánica") == "rev lit hispánica"
        assert (
            _normalize_venue("Revista de Literatura Hispánica")
            == "revista de literatura hispánica"
        )
        assert _normalize_venue("Rev Lit Hisp") == "rev lit hisp"
        # All three are different strings — NOT a cluster
        assert _normalize_venue("Rev. Lit. Hispánica") != _normalize_venue(
            "Revista de Literatura Hispánica"
        )


# ---------------------------------------------------------------------------
# Unit: _extract_doi_prefix
# ---------------------------------------------------------------------------


class TestExtractDoiPrefix:
    def test_standard_doi(self) -> None:
        assert _extract_doi_prefix("10.1234/some-article") == "10.1234"

    def test_longer_registrant_code(self) -> None:
        assert _extract_doi_prefix("10.12345/paper") == "10.12345"

    def test_no_slash_returns_none(self) -> None:
        assert _extract_doi_prefix("10.1234") is None

    def test_invalid_prefix_returns_none(self) -> None:
        assert _extract_doi_prefix("20.1234/invalid") is None

    def test_empty_string_returns_none(self) -> None:
        assert _extract_doi_prefix("") is None

    def test_with_whitespace(self) -> None:
        assert _extract_doi_prefix("  10.5678/article  ") == "10.5678"


# ---------------------------------------------------------------------------
# Unit: _extract_last_name
# ---------------------------------------------------------------------------


class TestExtractLastName:
    def test_single_name(self) -> None:
        assert _extract_last_name("García") == "garcía"

    def test_full_name(self) -> None:
        assert _extract_last_name("Juan García") == "garcía"

    def test_name_with_comma(self) -> None:
        assert _extract_last_name("García, Juan") == "juan"

    def test_empty_string(self) -> None:
        assert _extract_last_name("") is None

    def test_whitespace_only(self) -> None:
        assert _extract_last_name("   ") is None


# ---------------------------------------------------------------------------
# Deterministic check: Suspicious Venue Cluster
# ---------------------------------------------------------------------------


class TestSuspiciousVenueCluster:
    def test_three_not_found_same_venue_flagged(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", venue="Fake Journal"),
            _make_ref("r2", classification="not_found", venue="Fake Journal"),
            _make_ref("r3", classification="not_found", venue="Fake Journal"),
        ]
        flags = _check_suspicious_venue_cluster(refs)
        assert len(flags) == 1
        flag = flags[0]
        assert flag["type"] == "suspicious_venue_cluster"
        assert flag["venue"] == "fake journal"
        assert set(flag["reference_ids"]) == {"r1", "r2", "r3"}
        assert flag["count"] == 3

    def test_two_not_found_same_venue_not_flagged(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", venue="Fake Journal"),
            _make_ref("r2", classification="not_found", venue="Fake Journal"),
        ]
        flags = _check_suspicious_venue_cluster(refs)
        assert flags == []

    def test_verified_refs_excluded(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", venue="Fake Journal"),
            _make_ref("r2", classification="not_found", venue="Fake Journal"),
            _make_ref("r3", classification="verified", venue="Fake Journal"),
            _make_ref("r4", classification="verified", venue="Fake Journal"),
        ]
        # Only 2 not_found with same venue — not enough
        flags = _check_suspicious_venue_cluster(refs)
        assert flags == []

    def test_null_venue_skipped(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", venue="Fake Journal"),
            _make_ref("r2", classification="not_found", venue="Fake Journal"),
            _make_ref("r3", classification="not_found", venue=None),
        ]
        flags = _check_suspicious_venue_cluster(refs)
        assert flags == []

    def test_venue_normalization_matches(self) -> None:
        # Periods and commas removed, lowercased
        refs = [
            _make_ref("r1", classification="not_found", venue="Rev. Science"),
            _make_ref("r2", classification="not_found", venue="Rev Science"),
            _make_ref("r3", classification="not_found", venue="rev science"),
        ]
        flags = _check_suspicious_venue_cluster(refs)
        assert len(flags) == 1
        assert flags[0]["venue"] == "rev science"

    def test_all_verified_no_venue_flags(self) -> None:
        refs = [
            _make_ref("r1", classification="verified", venue="Nature"),
            _make_ref("r2", classification="verified", venue="Nature"),
            _make_ref("r3", classification="verified", venue="Nature"),
        ]
        flags = _check_suspicious_venue_cluster(refs)
        assert flags == []


# ---------------------------------------------------------------------------
# Deterministic check: Unregistered DOI Prefix Cluster
# ---------------------------------------------------------------------------


class TestUnregisteredDoiPrefixCluster:
    def test_two_unverified_same_prefix_no_verified_flagged(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/paper1"),
            _make_ref("r2", classification="not_found", doi="10.9999/paper2"),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert len(flags) == 1
        flag = flags[0]
        assert flag["type"] == "unregistered_doi_prefix"
        assert flag["doi_prefix"] == "10.9999"
        assert set(flag["reference_ids"]) == {"r1", "r2"}

    def test_one_unverified_not_flagged(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/paper1"),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert flags == []

    def test_verified_ref_with_same_prefix_prevents_flag(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/paper1"),
            _make_ref("r2", classification="not_found", doi="10.9999/paper2"),
            _make_ref("r3", classification="verified", doi="10.9999/legitimate"),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert flags == []

    def test_likely_verified_with_same_prefix_prevents_flag(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/paper1"),
            _make_ref("r2", classification="suspicious", doi="10.9999/paper2"),
            _make_ref("r3", classification="likely_verified", doi="10.9999/real"),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert flags == []

    def test_suspicious_refs_included(self) -> None:
        refs = [
            _make_ref("r1", classification="suspicious", doi="10.7777/paper1"),
            _make_ref("r2", classification="suspicious", doi="10.7777/paper2"),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert len(flags) == 1
        assert flags[0]["doi_prefix"] == "10.7777"

    def test_null_doi_skipped(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/paper1"),
            _make_ref("r2", classification="not_found", doi=None),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert flags == []

    def test_different_prefixes_not_clustered(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.1111/paper1"),
            _make_ref("r2", classification="not_found", doi="10.2222/paper2"),
        ]
        flags = _check_unregistered_doi_prefix_cluster(refs)
        assert flags == []


# ---------------------------------------------------------------------------
# Deterministic check: Self-Citation Anomaly
# ---------------------------------------------------------------------------


class TestSelfCitationAnomaly:
    def test_author_above_40_percent_flagged(self) -> None:
        # 5 out of 10 refs (50%) have García as last name
        refs = [_make_ref(f"r{i}", authors=["Author García"]) for i in range(5)] + [
            _make_ref(f"r{i + 5}", authors=["John Smith"]) for i in range(5)
        ]
        flags = _check_self_citation_anomaly(refs)
        assert any(
            f["type"] == "self_citation_anomaly" and f["dominant_author"] == "garcía"
            for f in flags
        )

    def test_author_exactly_40_percent_not_flagged(self) -> None:
        # Exactly 40% should NOT be flagged (condition is > 40%)
        refs = [_make_ref(f"r{i}", authors=["Author García"]) for i in range(4)] + [
            _make_ref(f"r{i + 4}", authors=["Other Smith"]) for i in range(6)
        ]
        flags = _check_self_citation_anomaly(refs)
        assert not any(f.get("dominant_author") == "garcía" for f in flags)

    def test_empty_refs_no_flags(self) -> None:
        flags = _check_self_citation_anomaly([])
        assert flags == []

    def test_no_authors_no_flags(self) -> None:
        refs = [_make_ref("r1", authors=[]), _make_ref("r2", authors=[])]
        flags = _check_self_citation_anomaly(refs)
        assert flags == []

    def test_percentage_field_rounded(self) -> None:
        refs = [_make_ref(f"r{i}", authors=["Juan García"]) for i in range(5)] + [
            _make_ref(f"r{i + 5}", authors=["Other Name"]) for i in range(5)
        ]
        flags = _check_self_citation_anomaly(refs)
        garcia_flags = [f for f in flags if f.get("dominant_author") == "garcía"]
        assert garcia_flags[0]["percentage"] == 50

    def test_reference_ids_listed(self) -> None:
        refs = [
            _make_ref("r1", authors=["Juan García"]),
            _make_ref("r2", authors=["Juan García"]),
            _make_ref("r3", authors=["Juan García"]),
            _make_ref("r4", authors=["Other Name"]),
            _make_ref("r5", authors=["Other Name"]),
        ]
        flags = _check_self_citation_anomaly(refs)
        garcia_flags = [f for f in flags if f.get("dominant_author") == "garcía"]
        assert set(garcia_flags[0]["reference_ids"]) == {"r1", "r2", "r3"}


# ---------------------------------------------------------------------------
# Deterministic check: Temporal Impossibility
# ---------------------------------------------------------------------------


class TestTemporalImpossibility:
    def test_future_year_flagged(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        flags = _check_temporal_impossibility(refs, current_year=2026)
        assert len(flags) == 1
        flag = flags[0]
        assert flag["type"] == "temporal_impossibility"
        assert flag["reference_id"] == "r1"
        assert flag["year"] == 2099
        assert flag["reason"] == "future_year"

    def test_current_year_not_flagged(self) -> None:
        refs = [_make_ref("r1", year=2026)]
        flags = _check_temporal_impossibility(refs, current_year=2026)
        assert flags == []

    def test_past_year_not_flagged(self) -> None:
        refs = [_make_ref("r1", year=2020)]
        flags = _check_temporal_impossibility(refs, current_year=2026)
        assert flags == []

    def test_null_year_skipped(self) -> None:
        refs = [_make_ref("r1", year=None)]
        flags = _check_temporal_impossibility(refs, current_year=2026)
        assert flags == []

    def test_multiple_future_years(self) -> None:
        refs = [
            _make_ref("r1", year=2027),
            _make_ref("r2", year=2025),
            _make_ref("r3", year=2030),
        ]
        flags = _check_temporal_impossibility(refs, current_year=2026)
        flagged_ids = {f["reference_id"] for f in flags}
        assert flagged_ids == {"r1", "r3"}

    def test_current_year_injectable(self) -> None:
        # When current_year=2020, year=2021 is future
        refs = [_make_ref("r1", year=2021)]
        flags = _check_temporal_impossibility(refs, current_year=2020)
        assert len(flags) == 1


# ---------------------------------------------------------------------------
# Node: analyze_cross_patterns (integration tests)
# ---------------------------------------------------------------------------


class TestAnalyzeCrossPatterns:
    def test_disabled_flag_returns_empty(self) -> None:
        state = _make_state([_make_ref("r1")])
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=False,
                cross_pattern_llm_enabled=True,
            )
            result = analyze_cross_patterns(state)

        assert result == {"cross_reference_analysis": {}}

    def test_empty_refs_produces_empty_flags(self) -> None:
        state = _make_state([])
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        analysis = result["cross_reference_analysis"]
        assert analysis["flags"] == []
        assert analysis["total_flags"] == 0
        assert analysis["analyzed_references"] == 0
        assert "llm_analysis" not in analysis

    def test_output_structure(self) -> None:
        refs = [_make_ref(f"r{i}") for i in range(5)]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        analysis = result["cross_reference_analysis"]
        assert "flags" in analysis
        assert "total_flags" in analysis
        assert "analyzed_references" in analysis
        assert analysis["analyzed_references"] == 5

    def test_venue_cluster_detected_by_node(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", venue="Phantom Journal"),
            _make_ref("r2", classification="not_found", venue="Phantom Journal"),
            _make_ref("r3", classification="not_found", venue="Phantom Journal"),
        ]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        analysis = result["cross_reference_analysis"]
        assert analysis["total_flags"] == 1
        assert analysis["flags"][0]["type"] == "suspicious_venue_cluster"

    def test_temporal_flag_detected_by_node(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        analysis = result["cross_reference_analysis"]
        assert analysis["total_flags"] == 1
        assert analysis["flags"][0]["type"] == "temporal_impossibility"

    def test_one_ref_skips_venue_and_doi_cluster(self) -> None:
        # Only temporal check can produce a flag with 1 ref
        refs = [
            _make_ref("r1", classification="not_found", venue="Fake", doi="10.9999/x")
        ]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        flags = result["cross_reference_analysis"]["flags"]
        flag_types = [f["type"] for f in flags]
        assert "suspicious_venue_cluster" not in flag_types
        assert "unregistered_doi_prefix" not in flag_types

    def test_two_refs_skips_venue_cluster_only(self) -> None:
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/x1"),
            _make_ref("r2", classification="not_found", doi="10.9999/x2"),
        ]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        flags = result["cross_reference_analysis"]["flags"]
        flag_types = [f["type"] for f in flags]
        assert "suspicious_venue_cluster" not in flag_types
        assert "unregistered_doi_prefix" in flag_types

    def test_reference_can_appear_in_multiple_flags(self) -> None:
        # r1 has a future year AND is part of a DOI prefix cluster
        refs = [
            _make_ref("r1", classification="not_found", doi="10.9999/x1", year=2099),
            _make_ref("r2", classification="not_found", doi="10.9999/x2"),
        ]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            result = analyze_cross_patterns(state, current_year=2026)

        flags = result["cross_reference_analysis"]["flags"]
        flag_types = [f["type"] for f in flags]
        assert "temporal_impossibility" in flag_types
        assert "unregistered_doi_prefix" in flag_types
        # r1 appears in both flags
        doi_flag = next(f for f in flags if f["type"] == "unregistered_doi_prefix")
        temporal_flag = next(f for f in flags if f["type"] == "temporal_impossibility")
        assert "r1" in doi_flag["reference_ids"]
        assert temporal_flag["reference_id"] == "r1"

    def test_llm_skipped_when_no_flags(self) -> None:
        refs = [_make_ref("r1", classification="verified")]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=True,
            )
            with patch(
                "biblio_checker_worker.langgraph.nodes.cross_patterns.get_llm"
            ) as mock_get_llm:
                result = analyze_cross_patterns(state, current_year=2026)
                mock_get_llm.assert_not_called()

        assert "llm_analysis" not in result["cross_reference_analysis"]

    def test_llm_skipped_when_disabled(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=False,
            )
            with patch(
                "biblio_checker_worker.langgraph.nodes.cross_patterns.get_llm"
            ) as mock_get_llm:
                result = analyze_cross_patterns(state, current_year=2026)
                mock_get_llm.assert_not_called()

        assert "llm_analysis" not in result["cross_reference_analysis"]

    def test_llm_called_when_flags_exist_and_enabled(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        state = _make_state(refs)

        mock_analysis = CrossPatternAnalysis(
            overall_assessment="Hay un problema temporal.",
            risk_level="medium",
            pattern_interpretations=[
                PatternInterpretation(
                    flag_type="temporal_impossibility",
                    interpretation="Año futuro sospechoso.",
                    severity="medium",
                )
            ],
            references_of_concern=["r1"],
        )

        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=True,
            )
            with patch(
                "biblio_checker_worker.langgraph.nodes.cross_patterns.get_llm"
            ) as mock_get_llm:
                mock_llm = MagicMock()
                mock_structured = MagicMock()
                mock_structured.invoke.return_value = mock_analysis
                mock_llm.with_structured_output.return_value = mock_structured
                mock_get_llm.return_value = mock_llm

                result = analyze_cross_patterns(state, current_year=2026)

        analysis = result["cross_reference_analysis"]
        assert "llm_analysis" in analysis
        llm_analysis = analysis["llm_analysis"]
        assert llm_analysis["risk_level"] == "medium"
        assert llm_analysis["overall_assessment"] == "Hay un problema temporal."
        assert llm_analysis["references_of_concern"] == ["r1"]
        assert len(llm_analysis["pattern_interpretations"]) == 1


# ---------------------------------------------------------------------------
# LLM Post-Validation
# ---------------------------------------------------------------------------


class TestLlmPostValidation:
    def _run_with_mock_analysis(
        self,
        refs: list[dict],
        mock_analysis: CrossPatternAnalysis,
        current_year: int = 2026,
    ) -> dict:
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=True,
            )
            with patch(
                "biblio_checker_worker.langgraph.nodes.cross_patterns.get_llm"
            ) as mock_get_llm:
                mock_llm = MagicMock()
                mock_structured = MagicMock()
                mock_structured.invoke.return_value = mock_analysis
                mock_llm.with_structured_output.return_value = mock_structured
                mock_get_llm.return_value = mock_llm
                result = analyze_cross_patterns(state, current_year=current_year)
        return result["cross_reference_analysis"]

    def test_invalid_references_of_concern_discarded(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        mock_analysis = CrossPatternAnalysis(
            overall_assessment="Assessment.",
            risk_level="high",
            pattern_interpretations=[],
            references_of_concern=["r1", "nonexistent_id"],
        )
        analysis = self._run_with_mock_analysis(refs, mock_analysis)
        assert analysis["llm_analysis"]["references_of_concern"] == ["r1"]

    def test_invalid_flag_type_in_interpretations_discarded(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        mock_analysis = CrossPatternAnalysis(
            overall_assessment="Assessment.",
            risk_level="medium",
            pattern_interpretations=[
                PatternInterpretation(
                    flag_type="temporal_impossibility",
                    interpretation="Valid flag type.",
                    severity="high",
                ),
                PatternInterpretation(
                    flag_type="made_up_flag_type",
                    interpretation="Invalid flag type — should be discarded.",
                    severity="low",
                ),
            ],
            references_of_concern=[],
        )
        analysis = self._run_with_mock_analysis(refs, mock_analysis)
        interps = analysis["llm_analysis"]["pattern_interpretations"]
        assert len(interps) == 1
        assert interps[0]["flag_type"] == "temporal_impossibility"

    def test_llm_error_produces_no_llm_analysis_key(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=True,
            )
            with patch(
                "biblio_checker_worker.langgraph.nodes.cross_patterns.get_llm"
            ) as mock_get_llm:
                mock_get_llm.side_effect = RuntimeError("LLM unavailable")
                result = analyze_cross_patterns(state, current_year=2026)

        analysis = result["cross_reference_analysis"]
        # Deterministic checks still ran
        assert analysis["total_flags"] == 1
        # LLM enrichment absent
        assert "llm_analysis" not in analysis

    def test_node_never_raises_on_llm_error(self) -> None:
        refs = [_make_ref("r1", year=2099)]
        state = _make_state(refs)
        with patch(
            "biblio_checker_worker.langgraph.nodes.cross_patterns.get_settings"
        ) as mock_settings:
            mock_settings.return_value = MagicMock(
                cross_pattern_analysis_enabled=True,
                cross_pattern_llm_enabled=True,
            )
            with patch(
                "biblio_checker_worker.langgraph.nodes.cross_patterns.get_llm"
            ) as mock_get_llm:
                mock_get_llm.side_effect = Exception("Catastrophic failure")
                # Must not raise
                result = analyze_cross_patterns(state, current_year=2026)

        assert "cross_reference_analysis" in result
