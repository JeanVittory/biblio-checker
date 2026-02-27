from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Classification(StrEnum):
    VERIFIED = "verified"
    LIKELY_VERIFIED = "likely_verified"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    SUSPICIOUS = "suspicious"
    PROCESSING_ERROR = "processing_error"


class ConfidenceBand(StrEnum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class ReasonCode(StrEnum):
    EXACT_DOI_MATCH = "exact_doi_match"
    EXACT_IDENTIFIER_MATCH = "exact_identifier_match"
    STRONG_METADATA_MATCH = "strong_metadata_match"
    MULTIPLE_PLAUSIBLE_CANDIDATES = "multiple_plausible_candidates"
    INSUFFICIENT_METADATA = "insufficient_metadata"
    NO_MATCH_ANY_SOURCE = "no_match_any_source"
    STRONG_DOI_CONFLICT = "strong_doi_conflict"
    CROSS_SOURCE_METADATA_CONFLICT = "cross_source_metadata_conflict"
    SOURCE_TIMEOUT_PARTIAL = "source_timeout_partial"
    REFERENCE_PROCESSING_FAILURE = "reference_processing_failure"


# ---------------------------------------------------------------------------
# Compatibility matrix
# ---------------------------------------------------------------------------

_ALLOWED_BANDS: dict[Classification, frozenset[ConfidenceBand | None]] = {
    Classification.VERIFIED:        frozenset({ConfidenceBand.HIGH, ConfidenceBand.VERY_HIGH}),
    Classification.LIKELY_VERIFIED: frozenset({ConfidenceBand.MEDIUM, ConfidenceBand.HIGH}),
    Classification.AMBIGUOUS:       frozenset({ConfidenceBand.LOW, ConfidenceBand.MEDIUM}),
    Classification.NOT_FOUND:       frozenset({ConfidenceBand.VERY_LOW, ConfidenceBand.LOW}),
    Classification.SUSPICIOUS:      frozenset({ConfidenceBand.MEDIUM, ConfidenceBand.HIGH, ConfidenceBand.VERY_HIGH}),
    Classification.PROCESSING_ERROR: frozenset({None}),
}

_REQUIRED_MANUAL_REVIEW: frozenset[Classification] = frozenset({
    Classification.AMBIGUOUS,
    Classification.NOT_FOUND,
    Classification.SUSPICIOUS,
    Classification.PROCESSING_ERROR,
})


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class NormalizedReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None
    authors: list[str]
    year: int | None
    venue: str | None
    doi: str | None
    arxivId: str | None


class MatchedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    externalId: str = Field(..., min_length=1)
    title: str | None
    year: int | None
    doi: str | None
    url: str | None


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(..., min_length=1)
    matchType: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=1.0)
    matchedRecord: MatchedRecord


class Warning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    referenceId: str | None
    details: dict[str, Any] | None


class CountsByClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: int = Field(..., ge=0)
    likely_verified: int = Field(..., ge=0)
    ambiguous: int = Field(..., ge=0)
    not_found: int = Field(..., ge=0)
    suspicious: int = Field(..., ge=0)
    processing_error: int = Field(..., ge=0)


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    totalReferencesDetected: int = Field(..., ge=0)
    totalReferencesAnalyzed: int = Field(..., ge=0)
    countsByClassification: CountsByClassification


class Pipeline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)


class ReferenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referenceId: str = Field(..., min_length=1)
    rawText: str = Field(..., min_length=1)
    normalized: NormalizedReference
    classification: Classification
    confidenceScore: float | None = Field(default=None, ge=0.0, le=1.0)
    confidenceBand: ConfidenceBand | None
    manualReviewRequired: bool
    reasonCode: ReasonCode
    decisionReason: str = Field(..., min_length=1)
    evidence: list[EvidenceItem]

    @model_validator(mode="after")
    def validate_compatibility_matrix(self) -> "ReferenceResult":
        allowed = _ALLOWED_BANDS[self.classification]
        if self.confidenceBand not in allowed:
            raise ValueError(
                f"classification='{self.classification}' is incompatible with "
                f"confidenceBand='{self.confidenceBand}'. "
                f"Allowed: {sorted(str(b) for b in allowed if b is not None) or ['null']}"
            )

        expected_manual = self.classification in _REQUIRED_MANUAL_REVIEW
        if self.manualReviewRequired != expected_manual:
            raise ValueError(
                f"classification='{self.classification}' requires "
                f"manualReviewRequired={expected_manual}, got {self.manualReviewRequired}"
            )

        if self.classification == Classification.PROCESSING_ERROR:
            if self.confidenceScore is not None:
                raise ValueError(
                    "classification='processing_error' requires confidenceScore=null"
                )

        return self


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------

class ResultsV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str = Field(..., pattern=r"^1\.0$")
    reportLanguage: str = Field(..., pattern=r"^es$")
    pipeline: Pipeline
    summary: Summary
    references: list[ReferenceResult]
    warnings: list[Warning]

    @model_validator(mode="after")
    def validate_cross_field_invariants(self) -> "ResultsV1":
        n = len(self.references)
        analyzed = self.summary.totalReferencesAnalyzed
        detected = self.summary.totalReferencesDetected

        # Invariant 1: references.length == totalReferencesAnalyzed
        if n != analyzed:
            raise ValueError(
                f"references length ({n}) must equal "
                f"summary.totalReferencesAnalyzed ({analyzed})"
            )

        # Invariant 2: sum(countsByClassification) == totalReferencesAnalyzed
        counts = self.summary.countsByClassification
        total_counts = (
            counts.verified
            + counts.likely_verified
            + counts.ambiguous
            + counts.not_found
            + counts.suspicious
            + counts.processing_error
        )
        if total_counts != analyzed:
            raise ValueError(
                f"sum of countsByClassification ({total_counts}) must equal "
                f"summary.totalReferencesAnalyzed ({analyzed})"
            )

        # Invariant 3: totalReferencesAnalyzed <= totalReferencesDetected
        if analyzed > detected:
            raise ValueError(
                f"summary.totalReferencesAnalyzed ({analyzed}) must be <= "
                f"summary.totalReferencesDetected ({detected})"
            )

        # Invariant 4: referenceId values must be unique
        ids = [ref.referenceId for ref in self.references]
        if len(ids) != len(set(ids)):
            raise ValueError("referenceId values must be unique within references[]")

        return self
