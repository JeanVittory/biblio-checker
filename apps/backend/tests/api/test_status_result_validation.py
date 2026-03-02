"""
Tests for GET /api/analysis/status — result validation behaviour in the
status controller (app.api.controllers.analysis.status).

Strategy
--------
All tests mock `get_analysis_job_by_id` so no real database is required.
A valid poll_status_token ("tok-abc") and a future poll_status_token_expires_at are injected into
every mocked DB row so that the token/expiry guards pass.  The tests focus
exclusively on how the controller handles the `results` column value from the
DB, specifically:

  - succeeded + valid ResultsV1 payload  → result field is the parsed object
  - succeeded + invalid/legacy payload   → result=null, status 200 (no crash)
  - succeeded + results=None in DB       → result=null, status 200
  - running                              → result=null
  - failed                               → result=null
  - queued                               → result=null

Each test uses httpx.ASGITransport with the FastAPI app, matching the pattern
established in tests/test_verify_authenticity_validation.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

DUMMY_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
VALID_TOKEN = "tok-abc"

# A token that expires one hour in the future guarantees the expiry guard passes.
_FUTURE_EXPIRES_AT = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

STATUS_URL = "/api/analysis/status"


# ---------------------------------------------------------------------------
# Canonical valid ResultsV1 payload (mirrors the spec canonical example)
# ---------------------------------------------------------------------------

VALID_RESULT_PAYLOAD: dict = {
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

# A payload that does NOT conform to ResultsV1 (incompatible band).
INVALID_RESULT_PAYLOAD: dict = {
    **VALID_RESULT_PAYLOAD,
    "references": [
        {
            **VALID_RESULT_PAYLOAD["references"][0],
            "confidenceBand": "very_low",  # incompatible with classification=verified
        }
    ],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_row(
    status: str,
    results: dict | None = None,
    error: str | None = None,
    stage: str | None = None,
) -> dict:
    """Build a minimal DB row dict that satisfies all controller guards."""
    return {
        "id": DUMMY_JOB_ID,
        "status": status,
        "poll_status_token": VALID_TOKEN,
        "poll_status_token_expires_at": _FUTURE_EXPIRES_AT,
        "created_at": "2024-01-01T00:00:00+00:00",
        "completed_at": "2024-01-01T00:01:00+00:00" if status in {"succeeded", "failed"} else None,
        "stage": stage,
        "results": results,
        "error": error,
    }


async def _get(job_id: str = DUMMY_JOB_ID, job_token: str = VALID_TOKEN) -> httpx.Response:
    """Issue GET /api/analysis/status with the given query parameters."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.get(
            STATUS_URL,
            params={"jobId": job_id, "jobToken": job_token},
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_succeeded_with_valid_result_returns_parsed_result():
    """
    When a job has status=succeeded and a valid ResultsV1 payload, the response
    must include the full parsed result object (not null).
    """
    row = _make_row(status="succeeded", results=VALID_RESULT_PAYLOAD)

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    # result must be present and non-null
    assert body["result"] is not None
    assert body["result"]["schemaVersion"] == "1.0"
    assert body["result"]["summary"]["totalReferencesAnalyzed"] == 1


@pytest.mark.anyio
async def test_succeeded_with_invalid_result_returns_null_result_no_crash():
    """
    When a job has status=succeeded but the results payload is invalid (e.g. a
    legacy or malformed document), the controller must degrade gracefully:
    response status must be 200 and result must be null.
    """
    row = _make_row(status="succeeded", results=INVALID_RESULT_PAYLOAD)

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["result"] is None


@pytest.mark.anyio
async def test_succeeded_with_none_results_in_db_returns_null_result():
    """
    When a job has status=succeeded but results=None in the DB row, the
    response must be 200 with result=null.
    """
    row = _make_row(status="succeeded", results=None)

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["result"] is None


@pytest.mark.anyio
async def test_running_job_returns_null_result():
    """A job with status=running must return result=null in the response."""
    row = _make_row(status="running", stage="verifying_references")

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert body["result"] is None


@pytest.mark.anyio
async def test_failed_job_returns_null_result():
    """A job with status=failed must return result=null in the response."""
    row = _make_row(status="failed", error="Pipeline execution failed.")

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["result"] is None


@pytest.mark.anyio
async def test_queued_job_returns_null_result():
    """A job with status=queued must return result=null in the response."""
    row = _make_row(status="queued")

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert body["result"] is None
