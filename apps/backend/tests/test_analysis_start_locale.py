"""Tests for locale field on VerifyAuthenticityRequest (Step 03).

Covers:
- Accepted locale values: es, pt, en
- Default locale when field omitted: es
- Rejection of unsupported locale: fr
- Rejection of region-suffix locale: es-ES
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.analysis import VerifyAuthenticityRequest

# ---------------------------------------------------------------------------
# Minimal valid payload factory (no locale key — uses default)
# ---------------------------------------------------------------------------

_BASE = {
    "document": {
        "fileName": "dummy.pdf",
        "mimeType": "application/pdf",
        "sourceType": "pdf",
    },
    "extractMode": "backend_extract_references",
    "requestId": "4806aa68-ed88-4205-ae86-cc085eb463fd",
    "storage": {
        "bucket": "uploads",
        "path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/dummy.pdf",
        "provider": "supabase",
    },
    "integrity": {
        "sha256": "a" * 64,
    },
}


def _make(**overrides) -> dict:
    import copy

    data = copy.deepcopy(_BASE)
    data.update(overrides)
    return data


class TestLocaleField:
    def test_accepts_es(self):
        req = VerifyAuthenticityRequest.model_validate(_make(locale="es"))
        assert req.locale == "es"

    def test_accepts_pt(self):
        req = VerifyAuthenticityRequest.model_validate(_make(locale="pt"))
        assert req.locale == "pt"

    def test_accepts_en(self):
        req = VerifyAuthenticityRequest.model_validate(_make(locale="en"))
        assert req.locale == "en"

    def test_defaults_to_es_when_omitted(self):
        req = VerifyAuthenticityRequest.model_validate(_make())
        assert req.locale == "es"

    def test_rejects_unsupported_locale(self):
        with pytest.raises(ValidationError):
            VerifyAuthenticityRequest.model_validate(_make(locale="fr"))

    def test_rejects_region_suffix(self):
        with pytest.raises(ValidationError):
            VerifyAuthenticityRequest.model_validate(_make(locale="es-ES"))

    def test_rejects_pt_br(self):
        with pytest.raises(ValidationError):
            VerifyAuthenticityRequest.model_validate(_make(locale="pt-BR"))

    def test_rejects_empty_string(self):
        with pytest.raises(ValidationError):
            VerifyAuthenticityRequest.model_validate(_make(locale=""))
