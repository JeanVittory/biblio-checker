"""Tests for ResultsV1.reportLanguage widening to ^(es|pt|en)$ (Step 03).

Verifies that the pattern now accepts 'pt' and 'en' in addition to 'es',
and still rejects unknown locale codes.
"""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from app.schemas.results import ResultsV1

# ---------------------------------------------------------------------------
# Minimal valid ResultsV1 fixture (no references — empty is valid)
# ---------------------------------------------------------------------------

_BASE_RESULTS = {
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


def _make_results(report_language: str) -> dict:
    data = copy.deepcopy(_BASE_RESULTS)
    data["reportLanguage"] = report_language
    return data


class TestReportLanguagePattern:
    def test_accepts_es(self):
        obj = ResultsV1.model_validate(_make_results("es"))
        assert obj.reportLanguage == "es"

    def test_accepts_pt(self):
        obj = ResultsV1.model_validate(_make_results("pt"))
        assert obj.reportLanguage == "pt"

    def test_accepts_en(self):
        obj = ResultsV1.model_validate(_make_results("en"))
        assert obj.reportLanguage == "en"

    def test_rejects_fr(self):
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(_make_results("fr"))

    def test_rejects_es_es(self):
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(_make_results("es-ES"))

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(_make_results(""))

    def test_rejects_zh(self):
        with pytest.raises(ValidationError):
            ResultsV1.model_validate(_make_results("zh"))
