"""Unit tests for the assemble_report node (Step 11)."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(
    pipeline_name: str = "biblio-checker",
    pipeline_version: str = "0.1.0",
) -> Any:
    """Return a minimal Settings-like object for monkeypatching get_settings."""
    s = MagicMock()
    s.pipeline_name = pipeline_name
    s.pipeline_version = pipeline_version
    return s


def _verified_ref(
    ref_id: str = "ref-1",
    classification: str = "verified",
    confidence_band: str | None = "very_high",
    confidence_score: float | None = 0.98,
    manual_review: bool = False,
    reason_code: str = "exact_doi_match",
) -> dict:
    """Return a classified reference dict accepted by assemble_report."""
    return {
        "referenceId": ref_id,
        "rawText": f"Raw text for {ref_id}",
        "normalized": {
            "title": f"Title {ref_id}",
            "authors": ["Author A"],
            "year": 2023,
            "venue": "Journal X",
            "doi": f"10.1234/{ref_id}",
            "arxivId": None,
        },
        "classification": classification,
        "confidenceScore": confidence_score,
        "confidenceBand": confidence_band,
        "manualReviewRequired": manual_review,
        "reasonCode": reason_code,
        "decisionReason": f"Decision reason for {ref_id}",
        "evidence": [
            {
                "source": "openalex",
                "matchType": "doi_exact",
                "score": 1.0,
                "matchedRecord": {
                    "externalId": "W123",
                    "title": f"Title {ref_id}",
                    "year": 2023,
                    "doi": f"10.1234/{ref_id}",
                    "url": "https://openalex.org/W123",
                },
            }
        ],
    }


def _processing_error_ref(ref_id: str = "ref-err") -> dict:
    """Return a pre-classified processing_error reference."""
    return {
        "referenceId": ref_id,
        "rawText": f"Unparseable reference {ref_id}",
        "normalized": {
            "title": None,
            "authors": [],
            "year": None,
            "venue": None,
            "doi": None,
            "arxivId": None,
        },
        "classification": "processing_error",
        "confidenceScore": None,
        "confidenceBand": None,
        "manualReviewRequired": True,
        "reasonCode": "reference_processing_failure",
        "decisionReason": "Reference could not be processed due to an internal error.",
        "evidence": [],
    }


def _make_state(
    classified: list[dict],
    total_detected: int | None = None,
    warnings: list[dict] | None = None,
) -> dict:
    """Build a minimal GraphState dict for assemble_report tests."""
    total = total_detected if total_detected is not None else len(classified)
    return {
        "job_id": "job-uuid-001",
        "source_type": "pdf",
        "file_bytes": b"",
        "raw_text": "",
        "raw_references": [],
        "total_references_detected": total,
        "normalized_references": [],
        "verified_references": [],
        "classified_references": classified,
        "warnings": warnings or [],
        "results_v1": {},
    }


def _invoke(
    state: dict,
    settings: Any | None = None,
    *,
    mock_renew: MagicMock | None = None,
) -> dict:
    """Call assemble_report with mocked get_settings and renew_lease_if_needed."""
    from biblio_checker_worker.langgraph.nodes.assemble import (
        assemble_report,  # noqa: PLC0415
    )

    mock_settings = settings or _make_settings()
    _renew = mock_renew if mock_renew is not None else MagicMock(return_value=None)
    with (
        patch(
            "biblio_checker_worker.langgraph.nodes.assemble.get_settings",
            return_value=mock_settings,
        ),
        patch(
            "biblio_checker_worker.langgraph.nodes.assemble.renew_lease_if_needed",
            _renew,
        ),
    ):
        return assemble_report(state)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAssembleReport:
    """Tests for the assemble_report graph node."""

    # ------------------------------------------------------------------
    # Normal assembly — mixed classifications
    # ------------------------------------------------------------------

    def test_normal_assembly_mixed_classifications(self) -> None:
        """Returns valid ResultsV1 with correct per-classification counts."""
        classified = [
            _verified_ref("ref-1", "verified", "very_high", 0.98, False, "exact_doi_match"),
            _verified_ref(
                "ref-2", "likely_verified", "high", 0.75, False, "strong_metadata_match"
            ),
            _verified_ref(
                "ref-3", "not_found", "very_low", 0.1, True, "no_match_any_source"
            ),
        ]
        state = _make_state(classified, total_detected=3)

        result = _invoke(state)

        assert "results_v1" in result
        rv1 = result["results_v1"]
        assert rv1["schemaVersion"] == "1.0"
        assert rv1["reportLanguage"] == "es"
        assert rv1["pipeline"]["name"] == "biblio-checker"
        assert rv1["pipeline"]["version"] == "0.1.0"
        assert rv1["summary"]["totalReferencesDetected"] == 3
        assert rv1["summary"]["totalReferencesAnalyzed"] == 3
        counts = rv1["summary"]["countsByClassification"]
        assert counts["verified"] == 1
        assert counts["likely_verified"] == 1
        assert counts["not_found"] == 1
        assert counts["ambiguous"] == 0
        assert counts["suspicious"] == 0
        assert counts["processing_error"] == 0
        assert len(rv1["references"]) == 3

    def test_return_dict_has_only_results_v1_key(self) -> None:
        """Node must return a partial state update dict with only results_v1."""
        state = _make_state([], total_detected=0)
        result = _invoke(state)
        assert list(result.keys()) == ["results_v1"]

    # ------------------------------------------------------------------
    # Zero references
    # ------------------------------------------------------------------

    def test_zero_references_produces_valid_empty_result(self) -> None:
        """Zero classified refs must produce a valid ResultsV1 with empty lists."""
        state = _make_state([], total_detected=0)

        result = _invoke(state)

        rv1 = result["results_v1"]
        assert rv1["summary"]["totalReferencesDetected"] == 0
        assert rv1["summary"]["totalReferencesAnalyzed"] == 0
        assert rv1["references"] == []
        counts = rv1["summary"]["countsByClassification"]
        for key in (
            "verified",
            "likely_verified",
            "ambiguous",
            "not_found",
            "suspicious",
            "processing_error",
        ):
            assert counts[key] == 0, f"Expected {key}=0, got {counts[key]}"

    # ------------------------------------------------------------------
    # processing_error references pass through unchanged
    # ------------------------------------------------------------------

    def test_processing_error_mixed_in_passes_validation(self) -> None:
        """Pre-classified processing_error refs must pass Pydantic validation."""
        classified = [
            _verified_ref("ref-1", "verified", "high", 0.9, False, "strong_metadata_match"),
            _processing_error_ref("ref-err"),
        ]
        state = _make_state(classified, total_detected=2)

        result = _invoke(state)

        rv1 = result["results_v1"]
        assert rv1["summary"]["totalReferencesAnalyzed"] == 2
        counts = rv1["summary"]["countsByClassification"]
        assert counts["verified"] == 1
        assert counts["processing_error"] == 1

        err_refs = [r for r in rv1["references"] if r["classification"] == "processing_error"]
        assert len(err_refs) == 1
        err = err_refs[0]
        assert err["referenceId"] == "ref-err"
        assert err["confidenceScore"] is None
        assert err["confidenceBand"] is None
        assert err["manualReviewRequired"] is True

    def test_all_processing_error_is_valid(self) -> None:
        """A ResultsV1 consisting entirely of processing_error refs must be valid."""
        classified = [_processing_error_ref("ref-1"), _processing_error_ref("ref-2")]
        state = _make_state(classified, total_detected=2)

        result = _invoke(state)

        rv1 = result["results_v1"]
        assert rv1["summary"]["countsByClassification"]["processing_error"] == 2
        assert rv1["summary"]["totalReferencesAnalyzed"] == 2

    # ------------------------------------------------------------------
    # Pydantic validation failure propagates
    # ------------------------------------------------------------------

    def test_duplicate_reference_id_raises_validation_error(self) -> None:
        """Duplicate referenceId values must cause ValidationError to propagate."""
        from pydantic import ValidationError  # noqa: PLC0415

        classified = [
            _verified_ref("dup-id", "verified", "very_high", 0.99, False, "exact_doi_match"),
            _verified_ref("dup-id", "verified", "very_high", 0.99, False, "exact_doi_match"),
        ]
        state = _make_state(classified, total_detected=2)

        with pytest.raises(ValidationError):
            _invoke(state)

    def test_analyzed_exceeds_detected_raises_validation_error(self) -> None:
        """totalReferencesAnalyzed > totalReferencesDetected must raise ValidationError."""
        from pydantic import ValidationError  # noqa: PLC0415

        classified = [
            _verified_ref("ref-1", "verified", "very_high", 0.98, False, "exact_doi_match"),
            _verified_ref(
                "ref-2", "verified", "high", 0.90, False, "strong_metadata_match"
            ),
        ]
        # Only 1 detected, but 2 classified — invariant 3 violated.
        state = _make_state(classified, total_detected=1)

        with pytest.raises(ValidationError):
            _invoke(state)

    # ------------------------------------------------------------------
    # Lease renewal
    # ------------------------------------------------------------------

    def test_renew_lease_called_once_per_invocation(self) -> None:
        """renew_lease_if_needed must be called exactly once per assemble_report call."""
        state = _make_state([], total_detected=0)

        mock_renew = MagicMock(return_value=None)
        _invoke(state, mock_renew=mock_renew)

        mock_renew.assert_called_once()

    # ------------------------------------------------------------------
    # Warnings are forwarded verbatim
    # ------------------------------------------------------------------

    def test_warnings_included_in_payload(self) -> None:
        """Accumulated warnings must appear verbatim in the ResultsV1 payload."""
        warnings = [
            {
                "code": "source_timeout",
                "message": "OpenAlex timed out for ref-1",
                "referenceId": "ref-1",
                "details": {"source": "openalex"},
            }
        ]
        classified = [
            _verified_ref("ref-1", "verified", "high", 0.88, False, "strong_metadata_match"),
        ]
        state = _make_state(classified, total_detected=1, warnings=warnings)

        result = _invoke(state)

        rv1 = result["results_v1"]
        assert len(rv1["warnings"]) == 1
        assert rv1["warnings"][0]["code"] == "source_timeout"
        assert rv1["warnings"][0]["referenceId"] == "ref-1"

    def test_no_warnings_produces_empty_list(self) -> None:
        """When no warnings are accumulated the ResultsV1 warnings list is empty."""
        state = _make_state([], total_detected=0, warnings=[])
        result = _invoke(state)
        assert result["results_v1"]["warnings"] == []

    # ------------------------------------------------------------------
    # Pipeline metadata from settings
    # ------------------------------------------------------------------

    def test_pipeline_metadata_from_settings(self) -> None:
        """pipeline.name and pipeline.version must come from get_settings()."""
        custom = _make_settings(pipeline_name="custom-pipe", pipeline_version="9.9.9")
        state = _make_state([], total_detected=0)

        result = _invoke(state, settings=custom)

        rv1 = result["results_v1"]
        assert rv1["pipeline"]["name"] == "custom-pipe"
        assert rv1["pipeline"]["version"] == "9.9.9"

    # ------------------------------------------------------------------
    # detected > analyzed is valid
    # ------------------------------------------------------------------

    def test_detected_greater_than_analyzed_is_valid(self) -> None:
        """Some refs may fail normalization; detected > analyzed is permitted."""
        classified = [
            _verified_ref("ref-1", "verified", "very_high", 0.99, False, "exact_doi_match"),
        ]
        # 5 detected but only 1 survived normalization/verification.
        state = _make_state(classified, total_detected=5)

        result = _invoke(state)

        rv1 = result["results_v1"]
        assert rv1["summary"]["totalReferencesDetected"] == 5
        assert rv1["summary"]["totalReferencesAnalyzed"] == 1
