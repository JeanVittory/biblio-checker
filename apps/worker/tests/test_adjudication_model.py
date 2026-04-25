"""Tests for the adjudication data model (Phase B, Spec 10 §2.1 + §2.2).

Covers:
- AdjudicationResult field validation (required fields, constraints)
- AdjudicationBatchOutput validation
- Confidence band derivation via _derive_confidence_band
- _band_is_valid compatibility matrix checks
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from biblio_checker_worker.langgraph.nodes.ai_adjudicate import (
    _band_is_valid,
    _derive_confidence_band,
)
from biblio_checker_worker.langgraph.prompts.adjudicate import (
    AdjudicationBatchOutput,
    AdjudicationResult,
)
from biblio_checker_worker.langgraph.schemas import (
    _ALLOWED_BANDS,
    Classification,
    ConfidenceBand,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_result(**overrides) -> dict:
    """Return a dict of fields for a valid AdjudicationResult."""
    base = {
        "reference_id": "ref-001",
        "ai_analysis": "La referencia no encontró candidatos en ninguna fuente.",
        "suggested_classification": "not_found",
        "suggested_confidence_score": 0.3,
        "fabrication_indicators": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# AdjudicationResult — valid construction
# ---------------------------------------------------------------------------


class TestAdjudicationResultValid:
    def test_all_fields_populated_validates_successfully(self) -> None:
        data = _valid_result(
            reference_id="ref-001",
            ai_analysis="Análisis detallado de la referencia.",
            suggested_classification="suspicious",
            suggested_confidence_score=0.85,
            fabrication_indicators=["El DOI no existe en CrossRef."],
        )
        result = AdjudicationResult(**data)
        assert result.reference_id == "ref-001"
        assert result.suggested_classification == "suspicious"
        assert result.suggested_confidence_score == pytest.approx(0.85)
        assert result.fabrication_indicators == ["El DOI no existe en CrossRef."]

    def test_minimal_fields_validates_successfully(self) -> None:
        data = _valid_result(fabrication_indicators=[])
        result = AdjudicationResult(**data)
        assert result.fabrication_indicators == []

    def test_all_valid_classifications_accepted(self) -> None:
        valid_classes = [
            "verified",
            "likely_verified",
            "ambiguous",
            "not_found",
            "suspicious",
        ]
        for cls in valid_classes:
            result = AdjudicationResult(**_valid_result(suggested_classification=cls))
            assert result.suggested_classification == cls

    def test_confidence_score_boundary_zero(self) -> None:
        result = AdjudicationResult(**_valid_result(suggested_confidence_score=0.0))
        assert result.suggested_confidence_score == pytest.approx(0.0)

    def test_confidence_score_boundary_one(self) -> None:
        result = AdjudicationResult(**_valid_result(suggested_confidence_score=1.0))
        assert result.suggested_confidence_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# AdjudicationResult — suggested_classification rejects invalid values
# ---------------------------------------------------------------------------


class TestAdjudicationResultSuggestedClassification:
    def test_processing_error_rejected(self) -> None:
        """Spec 03 §5: LLM must never suggest processing_error."""
        with pytest.raises(ValidationError):
            AdjudicationResult(
                **_valid_result(suggested_classification="processing_error")
            )

    def test_unknown_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(suggested_classification="unknown"))

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(suggested_classification=""))

    def test_arbitrary_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(suggested_classification="fake_class"))

    def test_uppercase_variant_rejected(self) -> None:
        # Pattern is lowercase only
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(suggested_classification="Verified"))


# ---------------------------------------------------------------------------
# AdjudicationResult — ai_analysis min_length=1
# ---------------------------------------------------------------------------


class TestAdjudicationResultAiAnalysis:
    def test_empty_string_rejected(self) -> None:
        """Spec 03 §5: ai_analysis must not be empty."""
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(ai_analysis=""))

    def test_single_char_accepted(self) -> None:
        result = AdjudicationResult(**_valid_result(ai_analysis="X"))
        assert result.ai_analysis == "X"

    def test_long_string_accepted_at_schema_level(self) -> None:
        """Spec 03 §2: No max-length on schema — truncation is done in the node."""
        long_text = "A" * 1000
        result = AdjudicationResult(**_valid_result(ai_analysis=long_text))
        assert len(result.ai_analysis) == 1000

    def test_501_chars_accepted_at_schema_level(self) -> None:
        text_501 = "B" * 501
        result = AdjudicationResult(**_valid_result(ai_analysis=text_501))
        assert len(result.ai_analysis) == 501


# ---------------------------------------------------------------------------
# AdjudicationResult — fabrication_indicators constraints
# ---------------------------------------------------------------------------


class TestAdjudicationResultFabricationIndicators:
    def test_empty_list_valid(self) -> None:
        result = AdjudicationResult(**_valid_result(fabrication_indicators=[]))
        assert result.fabrication_indicators == []

    def test_ten_items_valid(self) -> None:
        indicators = [f"Indicator {i}" for i in range(10)]
        result = AdjudicationResult(**_valid_result(fabrication_indicators=indicators))
        assert len(result.fabrication_indicators) == 10

    def test_eleven_items_rejected(self) -> None:
        """Spec 03 §1: fabrication_indicators limited to 10 items."""
        indicators = [f"Indicator {i}" for i in range(11)]
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(fabrication_indicators=indicators))

    def test_item_min_length_one_enforced(self) -> None:
        """Spec 03 §1: each item must be 1–200 characters."""
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(fabrication_indicators=[""]))

    def test_item_max_length_200_enforced(self) -> None:
        """Spec 03 §1: each item must be 1–200 characters."""
        too_long = "X" * 201
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(fabrication_indicators=[too_long]))

    def test_item_exactly_200_chars_valid(self) -> None:
        exact = "Y" * 200
        result = AdjudicationResult(**_valid_result(fabrication_indicators=[exact]))
        assert len(result.fabrication_indicators[0]) == 200

    def test_item_exactly_1_char_valid(self) -> None:
        result = AdjudicationResult(**_valid_result(fabrication_indicators=["Z"]))
        assert result.fabrication_indicators == ["Z"]


# ---------------------------------------------------------------------------
# AdjudicationResult — reference_id required and non-empty
# ---------------------------------------------------------------------------


class TestAdjudicationResultReferenceId:
    def test_non_empty_reference_id_valid(self) -> None:
        result = AdjudicationResult(**_valid_result(reference_id="ref-xyz"))
        assert result.reference_id == "ref-xyz"

    def test_empty_reference_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AdjudicationResult(**_valid_result(reference_id=""))

    def test_reference_id_required(self) -> None:
        data = _valid_result()
        del data["reference_id"]
        with pytest.raises(ValidationError):
            AdjudicationResult(**data)


# ---------------------------------------------------------------------------
# AdjudicationBatchOutput
# ---------------------------------------------------------------------------


class TestAdjudicationBatchOutput:
    def test_empty_adjudications_list_valid(self) -> None:
        """Spec 03 §2: empty list is valid (LLM may return no adjudications)."""
        output = AdjudicationBatchOutput(adjudications=[])
        assert output.adjudications == []

    def test_single_result_valid(self) -> None:
        result = AdjudicationResult(**_valid_result())
        output = AdjudicationBatchOutput(adjudications=[result])
        assert len(output.adjudications) == 1

    def test_multiple_results_valid(self) -> None:
        results = [
            AdjudicationResult(**_valid_result(reference_id=f"ref-{i}"))
            for i in range(5)
        ]
        output = AdjudicationBatchOutput(adjudications=results)
        assert len(output.adjudications) == 5

    def test_default_factory_produces_empty_list(self) -> None:
        output = AdjudicationBatchOutput()
        assert output.adjudications == []


# ---------------------------------------------------------------------------
# Confidence band derivation (Spec 03 §4 + Spec 10 §2.2)
# ---------------------------------------------------------------------------


class TestDerivConfidenceBand:
    """_derive_confidence_band applies spec thresholds exactly."""

    def test_verified_095_yields_very_high(self) -> None:
        band = _derive_confidence_band(Classification.VERIFIED, 0.95)
        assert band == ConfidenceBand.VERY_HIGH

    def test_verified_090_yields_very_high(self) -> None:
        band = _derive_confidence_band(Classification.VERIFIED, 0.90)
        assert band == ConfidenceBand.VERY_HIGH

    def test_verified_085_yields_high(self) -> None:
        """Score 0.85 is below 0.90 threshold → else branch → high."""
        band = _derive_confidence_band(Classification.VERIFIED, 0.85)
        assert band == ConfidenceBand.HIGH

    def test_verified_040_yields_high(self) -> None:
        """Spec 03 edge case: 0.40 maps to high (else branch). high IS in allowed set for verified → accepted."""
        band = _derive_confidence_band(Classification.VERIFIED, 0.40)
        assert band == ConfidenceBand.HIGH

    def test_verified_000_yields_high(self) -> None:
        band = _derive_confidence_band(Classification.VERIFIED, 0.0)
        assert band == ConfidenceBand.HIGH

    def test_likely_verified_080_yields_high(self) -> None:
        band = _derive_confidence_band(Classification.LIKELY_VERIFIED, 0.80)
        assert band == ConfidenceBand.HIGH

    def test_likely_verified_060_yields_medium(self) -> None:
        band = _derive_confidence_band(Classification.LIKELY_VERIFIED, 0.60)
        assert band == ConfidenceBand.MEDIUM

    def test_likely_verified_079_yields_medium(self) -> None:
        band = _derive_confidence_band(Classification.LIKELY_VERIFIED, 0.79)
        assert band == ConfidenceBand.MEDIUM

    def test_ambiguous_050_yields_medium(self) -> None:
        band = _derive_confidence_band(Classification.AMBIGUOUS, 0.50)
        assert band == ConfidenceBand.MEDIUM

    def test_ambiguous_049_yields_low(self) -> None:
        band = _derive_confidence_band(Classification.AMBIGUOUS, 0.49)
        assert band == ConfidenceBand.LOW

    def test_ambiguous_030_yields_low(self) -> None:
        band = _derive_confidence_band(Classification.AMBIGUOUS, 0.30)
        assert band == ConfidenceBand.LOW

    def test_not_found_020_yields_low(self) -> None:
        band = _derive_confidence_band(Classification.NOT_FOUND, 0.20)
        assert band == ConfidenceBand.LOW

    def test_not_found_080_yields_low(self) -> None:
        """Spec 10 §2.2: score 0.80 for not_found → >=0.20 → low. low IS in allowed set → accepted."""
        band = _derive_confidence_band(Classification.NOT_FOUND, 0.80)
        assert band == ConfidenceBand.LOW

    def test_not_found_019_yields_very_low(self) -> None:
        band = _derive_confidence_band(Classification.NOT_FOUND, 0.19)
        assert band == ConfidenceBand.VERY_LOW

    def test_not_found_010_yields_very_low(self) -> None:
        band = _derive_confidence_band(Classification.NOT_FOUND, 0.10)
        assert band == ConfidenceBand.VERY_LOW

    def test_suspicious_090_yields_very_high(self) -> None:
        band = _derive_confidence_band(Classification.SUSPICIOUS, 0.90)
        assert band == ConfidenceBand.VERY_HIGH

    def test_suspicious_080_yields_high(self) -> None:
        band = _derive_confidence_band(Classification.SUSPICIOUS, 0.80)
        assert band == ConfidenceBand.HIGH

    def test_suspicious_079_yields_medium(self) -> None:
        band = _derive_confidence_band(Classification.SUSPICIOUS, 0.79)
        assert band == ConfidenceBand.MEDIUM

    def test_suspicious_000_yields_medium(self) -> None:
        band = _derive_confidence_band(Classification.SUSPICIOUS, 0.0)
        assert band == ConfidenceBand.MEDIUM

    def test_processing_error_yields_none(self) -> None:
        """No band applies to processing_error."""
        band = _derive_confidence_band(Classification.PROCESSING_ERROR, 0.5)
        assert band is None


# ---------------------------------------------------------------------------
# Band validity checks against _ALLOWED_BANDS (Spec 10 §2.2)
# ---------------------------------------------------------------------------


class TestBandValidity:
    """Verify that bands derived from the thresholds are always valid per the matrix.

    Spec 10 §2.2 note: rejections via derivation do NOT occur because every else-branch
    maps to a band that IS in the allowed set. Rejections only occur when
    suggested_classification is processing_error.
    """

    def test_verified_high_is_valid(self) -> None:
        assert _band_is_valid(Classification.VERIFIED, ConfidenceBand.HIGH) is True

    def test_verified_very_high_is_valid(self) -> None:
        assert _band_is_valid(Classification.VERIFIED, ConfidenceBand.VERY_HIGH) is True

    def test_verified_medium_is_invalid(self) -> None:
        assert _band_is_valid(Classification.VERIFIED, ConfidenceBand.MEDIUM) is False

    def test_verified_low_is_invalid(self) -> None:
        assert _band_is_valid(Classification.VERIFIED, ConfidenceBand.LOW) is False

    def test_likely_verified_medium_is_valid(self) -> None:
        assert (
            _band_is_valid(Classification.LIKELY_VERIFIED, ConfidenceBand.MEDIUM)
            is True
        )

    def test_likely_verified_high_is_valid(self) -> None:
        assert (
            _band_is_valid(Classification.LIKELY_VERIFIED, ConfidenceBand.HIGH) is True
        )

    def test_likely_verified_very_high_is_invalid(self) -> None:
        assert (
            _band_is_valid(Classification.LIKELY_VERIFIED, ConfidenceBand.VERY_HIGH)
            is False
        )

    def test_ambiguous_low_is_valid(self) -> None:
        assert _band_is_valid(Classification.AMBIGUOUS, ConfidenceBand.LOW) is True

    def test_ambiguous_medium_is_valid(self) -> None:
        assert _band_is_valid(Classification.AMBIGUOUS, ConfidenceBand.MEDIUM) is True

    def test_ambiguous_high_is_invalid(self) -> None:
        assert _band_is_valid(Classification.AMBIGUOUS, ConfidenceBand.HIGH) is False

    def test_not_found_very_low_is_valid(self) -> None:
        assert _band_is_valid(Classification.NOT_FOUND, ConfidenceBand.VERY_LOW) is True

    def test_not_found_low_is_valid(self) -> None:
        assert _band_is_valid(Classification.NOT_FOUND, ConfidenceBand.LOW) is True

    def test_not_found_medium_is_invalid(self) -> None:
        assert _band_is_valid(Classification.NOT_FOUND, ConfidenceBand.MEDIUM) is False

    def test_suspicious_medium_is_valid(self) -> None:
        assert _band_is_valid(Classification.SUSPICIOUS, ConfidenceBand.MEDIUM) is True

    def test_suspicious_high_is_valid(self) -> None:
        assert _band_is_valid(Classification.SUSPICIOUS, ConfidenceBand.HIGH) is True

    def test_suspicious_very_high_is_valid(self) -> None:
        assert (
            _band_is_valid(Classification.SUSPICIOUS, ConfidenceBand.VERY_HIGH) is True
        )

    def test_suspicious_low_is_invalid(self) -> None:
        assert _band_is_valid(Classification.SUSPICIOUS, ConfidenceBand.LOW) is False

    def test_none_band_is_invalid_for_verified(self) -> None:
        assert _band_is_valid(Classification.VERIFIED, None) is False

    def test_none_band_is_valid_for_processing_error(self) -> None:
        """_ALLOWED_BANDS for processing_error contains frozenset({None})."""
        assert _band_is_valid(Classification.PROCESSING_ERROR, None) is True

    def test_all_derived_bands_are_valid_for_their_classification(self) -> None:
        """For every classification/score pair, the derived band must be valid per the matrix.

        This is the key property from Spec 10 §2.2: derivation never produces a
        band that fails the compatibility matrix.
        """
        test_cases: list[tuple[Classification, float]] = [
            (Classification.VERIFIED, 0.95),
            (Classification.VERIFIED, 0.85),
            (Classification.VERIFIED, 0.40),
            (Classification.LIKELY_VERIFIED, 0.80),
            (Classification.LIKELY_VERIFIED, 0.60),
            (Classification.AMBIGUOUS, 0.50),
            (Classification.AMBIGUOUS, 0.30),
            (Classification.NOT_FOUND, 0.20),
            (Classification.NOT_FOUND, 0.10),
            (Classification.NOT_FOUND, 0.80),
            (Classification.SUSPICIOUS, 0.90),
            (Classification.SUSPICIOUS, 0.80),
            (Classification.SUSPICIOUS, 0.79),
        ]
        for cls, score in test_cases:
            band = _derive_confidence_band(cls, score)
            assert _band_is_valid(cls, band), (
                f"Expected derived band {band!r} to be valid for {cls!r} at score {score}"
            )

    def test_allowed_bands_covers_all_classifications(self) -> None:
        """Every Classification value must appear in _ALLOWED_BANDS."""
        for cls in Classification:
            assert cls in _ALLOWED_BANDS, f"{cls!r} missing from _ALLOWED_BANDS"
