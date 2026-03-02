from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app

DUMMY_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
VALID_TOKEN = "tok-abc"
STATUS_URL = "/api/analysis/status"


def _future_expires_at_str(*, with_tz: bool, with_z: bool = False) -> str:
    future = datetime.now(UTC) + timedelta(hours=1)
    if not with_tz:
        return future.replace(tzinfo=None).isoformat()
    s = future.isoformat()
    return s.replace("+00:00", "Z") if with_z else s


def _make_row(
    *,
    poll_status_token_expires_at: object,
    created_at: object = "2024-01-01T00:00:00+00:00",
    completed_at: object = None,
) -> dict:
    return {
        "id": DUMMY_JOB_ID,
        "status": "running",
        "poll_status_token": VALID_TOKEN,
        "poll_status_token_expires_at": poll_status_token_expires_at,
        "created_at": created_at,
        "completed_at": completed_at,
        "stage": "created",
        "results": None,
        "error": None,
    }


async def _get(
    job_id: str = DUMMY_JOB_ID,
    job_token: str = VALID_TOKEN,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.get(
            STATUS_URL,
            params={"jobId": job_id, "jobToken": job_token},
        )


@pytest.mark.anyio
async def test_token_expires_at_accepts_naive_datetime():
    future_naive = datetime.now(UTC) + timedelta(hours=1)
    future_naive = future_naive.replace(tzinfo=None)
    row = _make_row(poll_status_token_expires_at=future_naive)

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_token_expires_at_accepts_iso_string_without_tz_assumes_utc():
    row = _make_row(poll_status_token_expires_at=_future_expires_at_str(with_tz=False))

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200


@pytest.mark.anyio
async def test_token_expires_at_invalid_type_returns_401():
    row = _make_row(poll_status_token_expires_at=123)

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 401
    assert resp.json() == {"error": "Invalid or expired token"}


@pytest.mark.anyio
async def test_created_at_invalid_returns_502():
    row = _make_row(
        poll_status_token_expires_at=_future_expires_at_str(with_tz=True),
        created_at=None,
    )

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 502
    assert resp.json() == {"error": "Service temporarily unavailable"}


@pytest.mark.anyio
async def test_completed_at_none_returns_null_completedAt():
    row = _make_row(
        poll_status_token_expires_at=_future_expires_at_str(with_tz=True),
        completed_at=None,
    )

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
    body = resp.json()
    assert body["completedAt"] is None


@pytest.mark.anyio
async def test_completed_at_invalid_string_returns_502():
    row = _make_row(
        poll_status_token_expires_at=_future_expires_at_str(with_tz=True),
        completed_at="not-a-date",
    )

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 502
    assert resp.json() == {"error": "Service temporarily unavailable"}


@pytest.mark.anyio
async def test_iso_strings_with_Z_suffix_are_accepted():
    row = _make_row(
        poll_status_token_expires_at=_future_expires_at_str(with_tz=True, with_z=True),
        created_at="2024-01-01T00:00:00Z",
        completed_at="2024-01-01T00:01:00Z",
    )

    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _get()

    assert resp.status_code == 200
