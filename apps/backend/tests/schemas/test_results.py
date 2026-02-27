"""
Tests for the ResultsV1 Pydantic model (app.schemas.results).

Coverage:
  - Valid fixtures for each classification variant (happy path).
  - Valid edge-cases: empty references list, non-empty warnings.
  - Invalid cases that must raise pydantic.ValidationError:
      * incompatible (classification, confidenceBand) pairs
      * processing_error with non-null confidenceBand
      * processing_error with non-null confidenceScore
      * ambiguous with manualReviewRequired=False
      * references.length != totalReferencesAnalyzed
      * sum(countsByClassification) != totalReferencesAnalyzed
      * totalReferencesAnalyzed > totalReferencesDetected
      * duplicate referenceId
      * schemaVersion != "1.0"
      * unknown root-level field (extra="forbid")
"""

import copy

import pytest
from pydantic import ValidationError

from app.schemas.results import ResultsV1

# ---------------------------------------------------------------------------
# Canonical fixtures
# ---------------------------------------------------------------------------

VALID_VERIFIED = {
    "schemaVersion": "1.0",
    "reportLanguage": "es",
    "pipeline": {"name": "reference_verification_pipeline", "version": "v1"},
    "summary": {
        "totalReferencesDetected": 1,
        "totalReferencesAnalyzed": 1,
        "countsByClassification": {
            "verified": 1,
            "likely_verified": 0,
            "ambiguous": 0,
            "not_found": 0,
            "suspicious": 0,
            "processing_error": 0,
        },
    },
    "references": [
        {
            "referenceId": "ref-001",
            "rawText": "Ejemplo con DOI exacto",
            "normalized": {
                "title": "Título real",
                "authors": ["Autor A"],
                "year": 2021,
                "venue": "Revista X",
                "doi": "10.1234/abcd.2021.001",
                "arxivId": None,
            },
            "classification": "verified",
            "confidenceScore": 0.91,
            "confidenceBand": "very_high",
            "manualReviewRequired": False,
            "reasonCode": "exact_doi_match",
            "decisionReason": "El DOI coincide exactamente con un registro canónico.",
            "evidence": [
                {
                    "source": "openalex",
                    "matchType": "exact_doi_match",
                    "score": 0.95,
                    "matchedRecord": {
                        "externalId": "W1234567890",
                        "title": "Título real",
                        "year": 2021,
                        "doi": "10.1234/abcd.2021.001",
                        "url": "https://openalex.org/W1234567890",
                    },
                }
            ],
        }
    ],
    "warnings": [],
}

VALID_PROCESSING_ERROR = {
    "schemaVersion": "1.0",
    "reportLanguage": "es",
    "pipeline": {"name": "reference_verification_pipeline", "version": "v1"},
    "summary": {
        "totalReferencesDetected": 1,
        "totalReferencesAnalyzed": 1,
        "countsByClassification": {
            "verified": 0,
            "likely_verified": 0,
            "ambiguous": 0,
            "not_found": 0,
            "suspicious": 0,
            "processing_error": 1,
        },
    },
    "references": [
        {
            "referenceId": "ref-001",
            "rawText": "Referencia que falló al procesarse",
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
            "decisionReason": "Ocurrió un error interno al procesar esta referencia.",
            "evidence": [],
        }
    ],
    "warnings": [],
}


def _make_ref(
    ref_id: str = "ref-001",
    classification: str = "likely_verified",
    confidence_band: str | None = "medium",
    confidence_score: float | None = 0.65,
    manual_review: bool = False,
    reason_code: str = "strong_metadata_match",
) -> dict:
    """Build a minimal ReferenceResult dict for use in helper fixtures."""
    return {
        "referenceId": ref_id,
        "rawText": "Some raw text",
        "normalized": {
            "title": "Some Title",
            "authors": ["Author B"],
            "year": 2020,
            "venue": "Some Venue",
            "doi": None,
            "arxivId": None,
        },
        "classification": classification,
        "confidenceScore": confidence_score,
        "confidenceBand": confidence_band,
        "manualReviewRequired": manual_review,
        "reasonCode": reason_code,
        "decisionReason": "Reason text.",
        "evidence": [],
    }


def _make_result(refs: list[dict], counts_override: dict | None = None) -> dict:
    """Build a minimal ResultsV1 dict whose summary is consistent with refs."""
    totals: dict[str, int] = {
        "verified": 0,
        "likely_verified": 0,
        "ambiguous": 0,
        "not_found": 0,
        "suspicious": 0,
        "processing_error": 0,
    }
    for r in refs:
        totals[r["classification"]] += 1

    if counts_override:
        totals.update(counts_override)

    return {
        "schemaVersion": "1.0",
        "reportLanguage": "es",
        "pipeline": {"name": "reference_verification_pipeline", "version": "v1"},
        "summary": {
            "totalReferencesDetected": len(refs),
            "totalReferencesAnalyzed": len(refs),
            "countsByClassification": totals,
        },
        "references": refs,
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Valid cases — must parse without error
# ---------------------------------------------------------------------------


class TestValidCases:
    def test_verified_very_high(self):
        """verified + very_high + manualReviewRequired=False must parse."""
        result = ResultsV1.model_validate(VALID_VERIFIED)
        ref = result.references[0]
        assert ref.classification == "verified"
        assert str(ref.confidenceBand) == "very_high"
        assert ref.manualReviewRequired is False

    def test_likely_verified_medium(self):
        """likely_verified + medium + manualReviewRequired=False must parse."""
        data = _make_result(
            [
                _make_ref(
                    classification="likely_verified",
                    confidence_band="medium",
                    confidence_score=0.65,
                    manual_review=False,
                    reason_code="strong_metadata_match",
                )
            ]
        )
        result = ResultsV1.model_validate(data)
        assert result.references[0].classification == "likely_verified"

    def test_ambiguous_low_manual_review_true(self):
        """ambiguous + low + manualReviewRequired=True must parse."""
        data = _make_result(
            [
                _make_ref(
                    classification="ambiguous",
                    confidence_band="low",
                    confidence_score=0.4,
                    manual_review=True,
                    reason_code="multiple_plausible_candidates",
                )
            ]
        )
        result = ResultsV1.model_validate(data)
        assert result.references[0].classification == "ambiguous"
        assert result.references[0].manualReviewRequired is True

    def test_not_found_very_low_manual_review_true(self):
        """not_found + very_low + manualReviewRequired=True must parse."""
        data = _make_result(
            [
                _make_ref(
                    classification="not_found",
                    confidence_band="very_low",
                    confidence_score=0.05,
                    manual_review=True,
                    reason_code="no_match_any_source",
                )
            ]
        )
        result = ResultsV1.model_validate(data)
        assert result.references[0].classification == "not_found"

    def test_suspicious_high_manual_review_true(self):
        """suspicious + high + manualReviewRequired=True must parse."""
        data = _make_result(
            [
                _make_ref(
                    classification="suspicious",
                    confidence_band="high",
                    confidence_score=0.75,
                    manual_review=True,
                    reason_code="strong_doi_conflict",
                )
            ]
        )
        result = ResultsV1.model_validate(data)
        assert result.references[0].classification == "suspicious"

    def test_processing_error_null_band_null_score(self):
        """processing_error + confidenceBand=null + confidenceScore=null must parse."""
        result = ResultsV1.model_validate(VALID_PROCESSING_ERROR)
        ref = result.references[0]
        assert ref.classification == "processing_error"
        assert ref.confidenceBand is None
        assert ref.confidenceScore is None
        assert ref.manualReviewRequired is True

    def test_empty_references_list(self):
        """A report with zero references (totalReferencesAnalyzed=0) must parse."""
        data = {
            "schemaVersion": "1.0",
            "reportLanguage": "es",
            "pipeline": {"name": "reference_verification_pipeline", "version": "v1"},
            "summary": {
                "totalReferencesDetected": 0,
                "totalReferencesAnalyzed": 0,
                "countsByClassification": {
                    "verified": 0,
                    "likely_verified": 0,
                    "ambiguous": 0,
                    "not_found": 0,
                    "suspicious": 0,
                    "processing_error": 0,
                },
            },
            "references": [],
            "warnings": [],
        }
        result = ResultsV1.model_validate(data)
        assert result.references == []
        assert result.summary.totalReferencesAnalyzed == 0

    def test_non_empty_warnings_list(self):
        """A report with a non-empty warnings[] array must parse."""
        data = copy.deepcopy(VALID_VERIFIED)
        data["warnings"] = [
            {
                "code": "source_timeout",
                "message": "OpenAlex timed out for ref-001.",
                "referenceId": "ref-001",
                "details": {"timeoutMs": 5000},
            }
        ]
        result = ResultsV1.model_validate(data)
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "source_timeout"


# ---------------------------------------------------------------------------
# Invalid cases — must raise ValidationError
# ---------------------------------------------------------------------------


class TestInvalidCases:
    def test_verified_with_very_low_band_raises(self):
        """verified + very_low is incompatible: must raise ValidationError."""
        data = copy.deepcopy(VALID_VERIFIED)
        data["references"][0]["confidenceBand"] = "very_low"
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_not_found_with_very_high_band_raises(self):
        """not_found + very_high is incompatible: must raise ValidationError."""
        data = _make_result(
            [
                _make_ref(
                    classification="not_found",
                    confidence_band="very_high",
                    confidence_score=0.9,
                    manual_review=True,
                    reason_code="no_match_any_source",
                )
            ]
        )
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_processing_error_with_non_null_band_raises(self):
        """processing_error + confidenceBand='low' (not null) must raise ValidationError."""
        data = copy.deepcopy(VALID_PROCESSING_ERROR)
        data["references"][0]["confidenceBand"] = "low"
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_processing_error_with_non_null_score_raises(self):
        """processing_error + confidenceScore=0.5 (not null) must raise ValidationError."""
        data = copy.deepcopy(VALID_PROCESSING_ERROR)
        data["references"][0]["confidenceScore"] = 0.5
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_ambiguous_with_manual_review_false_raises(self):
        """ambiguous + manualReviewRequired=False must raise ValidationError (must be True)."""
        data = _make_result(
            [
                _make_ref(
                    classification="ambiguous",
                    confidence_band="low",
                    confidence_score=0.4,
                    manual_review=False,  # invalid: must be True for ambiguous
                    reason_code="multiple_plausible_candidates",
                )
            ]
        )
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_references_length_differs_from_total_analyzed_raises(self):
        """references.length != totalReferencesAnalyzed violates cross-field invariant."""
        data = copy.deepcopy(VALID_VERIFIED)
        # Claim 2 analyzed but only 1 reference object present.
        data["summary"]["totalReferencesAnalyzed"] = 2
        data["summary"]["totalReferencesDetected"] = 2
        # Keep countsByClassification sum consistent with the new totalReferencesAnalyzed
        # so only the references-length invariant fails.
        data["summary"]["countsByClassification"]["verified"] = 2
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_counts_sum_differs_from_total_analyzed_raises(self):
        """sum(countsByClassification) != totalReferencesAnalyzed must raise ValidationError."""
        data = copy.deepcopy(VALID_VERIFIED)
        # totalReferencesAnalyzed=1, references has 1 entry, but counts sum to 2.
        data["summary"]["countsByClassification"]["verified"] = 2
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_analyzed_greater_than_detected_raises(self):
        """totalReferencesAnalyzed > totalReferencesDetected must raise ValidationError."""
        data = copy.deepcopy(VALID_VERIFIED)
        # Set detected=0 while analyzed=1 (from the single reference).
        data["summary"]["totalReferencesDetected"] = 0
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_duplicate_reference_id_raises(self):
        """Duplicate referenceId values must raise ValidationError."""
        ref_a = _make_ref(
            ref_id="ref-001",
            classification="verified",
            confidence_band="very_high",
            confidence_score=0.91,
            manual_review=False,
            reason_code="exact_doi_match",
        )
        ref_b = _make_ref(
            ref_id="ref-001",  # duplicate ID
            classification="verified",
            confidence_band="high",
            confidence_score=0.85,
            manual_review=False,
            reason_code="exact_doi_match",
        )
        data = {
            "schemaVersion": "1.0",
            "reportLanguage": "es",
            "pipeline": {"name": "reference_verification_pipeline", "version": "v1"},
            "summary": {
                "totalReferencesDetected": 2,
                "totalReferencesAnalyzed": 2,
                "countsByClassification": {
                    "verified": 2,
                    "likely_verified": 0,
                    "ambiguous": 0,
                    "not_found": 0,
                    "suspicious": 0,
                    "processing_error": 0,
                },
            },
            "references": [ref_a, ref_b],
            "warnings": [],
        }
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_wrong_schema_version_raises(self):
        """schemaVersion != '1.0' must raise ValidationError."""
        data = copy.deepcopy(VALID_VERIFIED)
        data["schemaVersion"] = "2.0"
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)

    def test_unknown_root_field_raises(self):
        """An unknown field at the root level must raise ValidationError (extra='forbid')."""
        data = copy.deepcopy(VALID_VERIFIED)
        data["unknownField"] = "should-not-be-here"
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(data)
