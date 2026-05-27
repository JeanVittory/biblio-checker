"""Integration tests for the ``service_offline`` problem code.

When Supabase is paused / unreachable, the backend should respond with HTTP
503 and ``code == "service_offline"`` instead of the generic 502 mapping.
Covers both the text-mode and file-mode entry points.
"""

from __future__ import annotations

import copy
import hashlib
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from postgrest.exceptions import APIError

from app.main import app

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TEXT_URL = "/api/analysis/start-text"
FILE_URL = "/api/analysis/start"

VALID_TEXT_PAYLOAD: dict = {
    "requestId": "4806aa68-ed88-4205-ae86-cc085eb463fd",
    "reference": {
        "rawText": "Smith, J. (2021). A study on climate change. Nature, 123, 456-478."
    },
    "locale": "es",
}

DUMMY_CONTENT = b"dummy"
DUMMY_SHA256 = hashlib.sha256(DUMMY_CONTENT).hexdigest()

VALID_FILE_PAYLOAD: dict = {
    "requestId": "4806aa68-ed88-4205-ae86-cc085eb463fd",
    "extractMode": "backend_extract_references",
    "document": {
        "sourceType": "pdf",
        "fileName": "dummy.pdf",
        "mimeType": "application/pdf",
    },
    "storage": {
        "provider": "supabase",
        "bucket": "uploads",
        "path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/dummy.pdf",
    },
    "integrity": {"sha256": DUMMY_SHA256},
}


async def _post(url: str, payload: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.post(url, json=payload)


# ---------------------------------------------------------------------------
# Text mode — DB connectivity failures map to 503 / service_offline
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_text_connect_error_returns_service_offline():
    from app.services.analysis_jobs_repo import AnalysisJobsRepoError

    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(
            side_effect=AnalysisJobsRepoError(
                code="service_offline",
                detail="ConnectError: Connection refused",
            )
        ),
    ):
        resp = await _post(TEXT_URL, VALID_TEXT_PAYLOAD)

    assert resp.status_code == 503
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "service_offline"
    assert body["title"] == "Service temporarily unavailable"


@pytest.mark.anyio
async def test_text_data_error_does_not_become_service_offline():
    """No-regression: real data errors keep their existing more specific code."""
    from app.services.analysis_jobs_repo import AnalysisJobsRepoError

    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(
            side_effect=AnalysisJobsRepoError(
                code="analysis_job_create_failed",
                detail="duplicate key value violates unique constraint",
            )
        ),
    ):
        resp = await _post(TEXT_URL, VALID_TEXT_PAYLOAD)

    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "analysis_job_create_failed"


@pytest.mark.anyio
async def test_text_classifier_routes_real_connect_error():
    """End-to-end check: an httpx.ConnectError raised by the repo internals
    must be classified as ``service_offline`` by ``analysis_jobs_repo``.
    """

    async def _fake_create_job(_row):
        # Trigger the same exception path that supabase-py would raise when
        # the upstream DB is unreachable; let the repo classify it.
        from app.services.analysis_jobs_repo import create_analysis_job  # noqa: F401

        raise httpx.ConnectError("All connection attempts failed")

    # Patch the lowest-level supabase call so the real repo's except branch runs.
    class _RaisingClient:
        def table(self, _name):
            raise httpx.ConnectError("All connection attempts failed")

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=_RaisingClient(),
    ):
        resp = await _post(TEXT_URL, VALID_TEXT_PAYLOAD)

    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "service_offline"


# ---------------------------------------------------------------------------
# File mode — Storage connectivity failures map to 503 / service_offline
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_file_storage_504_returns_service_offline():
    from app.services.supabase_storage import SupabaseStorageError

    with patch(
        "app.api.controllers.analysis.start.download_object_bytes",
        new=AsyncMock(
            side_effect=SupabaseStorageError(
                code="service_offline",
                detail="Storage request failed with status 504.",
            )
        ),
    ):
        resp = await _post(FILE_URL, copy.deepcopy(VALID_FILE_PAYLOAD))

    assert resp.status_code == 503
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "service_offline"


@pytest.mark.anyio
async def test_file_storage_generic_failure_does_not_become_service_offline():
    """No-regression: non-connectivity storage errors keep their specific code."""
    from app.services.supabase_storage import SupabaseStorageError

    with patch(
        "app.api.controllers.analysis.start.download_object_bytes",
        new=AsyncMock(
            side_effect=SupabaseStorageError(
                code="storage_download_failed",
                detail="Storage request failed with status 400.",
            )
        ),
    ):
        resp = await _post(FILE_URL, copy.deepcopy(VALID_FILE_PAYLOAD))

    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "storage_download_failed"


# ---------------------------------------------------------------------------
# Repo classifier — APIError with upstream status routes to service_offline
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_text_apierror_503_classified_as_service_offline():
    """Lower-level: when supabase-py wraps the failure in APIError(code='503'),
    the repo's classifier must promote it to ``service_offline``.
    """

    class _ApiErrorClient:
        def table(self, _name):
            return self

        def insert(self, _row):
            return self

        def execute(self):
            raise APIError(
                {"message": "Bad Gateway", "code": "503", "details": "", "hint": ""}
            )

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=_ApiErrorClient(),
    ):
        resp = await _post(TEXT_URL, VALID_TEXT_PAYLOAD)

    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "service_offline"


@pytest.mark.anyio
async def test_text_apierror_data_error_keeps_generic_code():
    """No-regression: APIError with a non-upstream code stays as
    ``analysis_job_create_failed`` and does NOT flip to ``service_offline``.
    """

    class _DataErrorClient:
        def table(self, _name):
            return self

        def insert(self, _row):
            return self

        def execute(self):
            raise APIError(
                {
                    "message": "duplicate key value violates unique constraint",
                    "code": "23505",
                    "details": "",
                    "hint": "",
                }
            )

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=_DataErrorClient(),
    ):
        resp = await _post(TEXT_URL, VALID_TEXT_PAYLOAD)

    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "analysis_job_create_failed"
