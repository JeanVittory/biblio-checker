"""Tests for GET /api/analysis/shared/{shareToken} — public read endpoint.

All tests mock `get_analysis_job_by_share_token` so no real database is required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app

SHARED_BASE = "/api/analysis/shared"
DUMMY_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
VALID_TOKEN = "validtoken123456789012345678901"  # 31 chars (within 64 limit)

_FUTURE_EXPIRES = (datetime.now(UTC) + timedelta(days=6)).isoformat()
_PAST_EXPIRES = (datetime.now(UTC) - timedelta(hours=1)).isoformat()


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
            "rawText": "Example reference",
            "normalized": {
                "title": "Real Title",
                "authors": ["Author A"],
                "year": 2021,
                "venue": "Journal X",
                "doi": "10.1234/abcd.2021.001",
                "arxivId": None,
            },
            "classification": "verified",
            "confidenceScore": 0.91,
            "confidenceBand": "very_high",
            "manualReviewRequired": False,
            "reasonCode": "exact_doi_match",
            "decisionReason": "DOI matches exactly.",
            "evidence": [
                {
                    "source": "openalex",
                    "matchType": "exact_doi_match",
                    "score": 0.95,
                    "matchedRecord": {
                        "externalId": "W1234567890",
                        "title": "Real Title",
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

INVALID_RESULT_PAYLOAD: dict = {
    **VALID_RESULT_PAYLOAD,
    "references": [
        {
            **VALID_RESULT_PAYLOAD["references"][0],
            "confidenceBand": "very_low",  # incompatible with classification=verified
        }
    ],
}


def _make_row(
    status: str = "succeeded",
    share_expires: str = _FUTURE_EXPIRES,
    result_json: dict | None = None,
) -> dict:
    return {
        "id": DUMMY_JOB_ID,
        "status": status,
        "stage": None,
        "result_json": result_json,
        "error_code": None,
        "error_detail": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "completed_at": "2024-01-01T00:01:00+00:00" if status == "succeeded" else None,
        "share_token": VALID_TOKEN,
        "share_token_expires_at": share_expires,
    }


async def _get(token: str = VALID_TOKEN) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.get(f"{SHARED_BASE}/{token}")


# ---------------------------------------------------------------------------
# Token length guard
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_token_longer_than_64_chars_returns_404():
    long_token = "x" * 65
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=None),
    ) as mock:
        resp = await _get(token=long_token)

    assert resp.status_code == 404
    # Must not even reach the DB
    mock.assert_not_called()


@pytest.mark.anyio
async def test_token_exactly_64_chars_reaches_db():
    token_64 = "x" * 64
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=None),
    ) as mock:
        resp = await _get(token=token_64)

    assert resp.status_code == 404
    mock.assert_called_once_with(token_64)


# ---------------------------------------------------------------------------
# Not-found / error cases — all return identical 404
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_nonexistent_token_returns_404():
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=None),
    ):
        resp = await _get()

    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "not_found"
    assert body["success"] is False


@pytest.mark.anyio
async def test_expired_token_returns_404():
    row = _make_row(share_expires=_PAST_EXPIRES)
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


@pytest.mark.anyio
async def test_non_succeeded_job_returns_404():
    for status in ("queued", "running", "failed"):
        row = _make_row(status=status)
        with patch(
            "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
            new=AsyncMock(return_value=row),
        ):
            resp = await _get()

        assert resp.status_code == 404, f"expected 404 for status={status}"
        assert resp.json()["error"] == "not_found"


@pytest.mark.anyio
async def test_repo_error_returns_404():
    from app.services.analysis_jobs_repo import AnalysisJobsRepoError

    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(side_effect=AnalysisJobsRepoError(code="db_error")),
    ):
        resp = await _get()

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_valid_token_returns_200_with_results():
    row = _make_row(result_json=VALID_RESULT_PAYLOAD)
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["jobId"] == DUMMY_JOB_ID
    assert body["status"] == "succeeded"
    assert body["result"] is not None
    assert body["result"]["schemaVersion"] == "1.0"
    assert body["fileName"] is None  # v1 always null
    assert "expiresAt" in body
    assert "completedAt" in body


@pytest.mark.anyio
async def test_valid_token_with_invalid_result_returns_null_result():
    row = _make_row(result_json=INVALID_RESULT_PAYLOAD)
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["result"] is None


@pytest.mark.anyio
async def test_valid_token_with_null_result_returns_null_result():
    row = _make_row(result_json=None)
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["result"] is None


@pytest.mark.anyio
async def test_filename_is_always_null():
    """fileName MUST be null in v1 (security: never derived from path)."""
    row = _make_row(result_json=VALID_RESULT_PAYLOAD)
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    assert resp.json()["fileName"] is None


@pytest.mark.anyio
async def test_expires_at_matches_db_value():
    row = _make_row()
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    # expiresAt in the response must be derived from the DB value
    expires_at = datetime.fromisoformat(resp.json()["expiresAt"])
    expected = datetime.fromisoformat(_FUTURE_EXPIRES)
    assert abs((expires_at - expected).total_seconds()) < 1


@pytest.mark.anyio
async def test_no_auth_header_required():
    """Public endpoint must work without any authentication header."""
    row = _make_row(result_json=VALID_RESULT_PAYLOAD)
    transport = httpx.ASGITransport(app=app)
    with patch(
        "app.api.controllers.analysis.shared.get_analysis_job_by_share_token",
        new=AsyncMock(return_value=row),
    ):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                f"{SHARED_BASE}/{VALID_TOKEN}",
                # No Authorization or any other auth header
            )

    assert resp.status_code == 200
