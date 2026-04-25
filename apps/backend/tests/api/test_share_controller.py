"""Tests for POST /api/analysis/share — share token generation endpoint.

All tests mock `get_analysis_job_by_id` and `update_share_token` so no real
database is required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app

SHARE_URL = "/api/analysis/share"
DUMMY_JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
VALID_TOKEN = "tok-abc"
_FUTURE_POLL_EXPIRES = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
_PAST_POLL_EXPIRES = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
_FUTURE_SHARE_EXPIRES = (datetime.now(UTC) + timedelta(days=6)).isoformat()
_PAST_SHARE_EXPIRES = (datetime.now(UTC) - timedelta(days=1)).isoformat()


def _make_row(
    status: str = "succeeded",
    poll_expires: str = _FUTURE_POLL_EXPIRES,
    share_token: str | None = None,
    share_expires: str | None = None,
) -> dict:
    return {
        "id": DUMMY_JOB_ID,
        "status": status,
        "poll_status_token": VALID_TOKEN,
        "poll_status_token_expires_at": poll_expires,
        "created_at": "2024-01-01T00:00:00+00:00",
        "completed_at": "2024-01-01T00:01:00+00:00" if status == "succeeded" else None,
        "stage": None,
        "result_json": None,
        "error_detail": None,
        "share_token": share_token,
        "share_token_expires_at": share_expires,
    }


async def _post(
    job_id: str = DUMMY_JOB_ID, job_token: str = VALID_TOKEN
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.post(
            SHARE_URL,
            json={"jobId": job_id, "jobToken": job_token},
        )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_job_not_found_returns_401():
    with patch(
        "app.api.controllers.analysis.share.get_analysis_job_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = await _post()

    assert resp.status_code == 401


@pytest.mark.anyio
async def test_wrong_token_returns_401():
    row = _make_row()
    with patch(
        "app.api.controllers.analysis.share.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _post(job_token="wrong-token")

    assert resp.status_code == 401


@pytest.mark.anyio
async def test_expired_poll_token_returns_401():
    row = _make_row(poll_expires=_PAST_POLL_EXPIRES)
    with patch(
        "app.api.controllers.analysis.share.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _post()

    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_queued_job_returns_409():
    row = _make_row(status="queued")
    with patch(
        "app.api.controllers.analysis.share.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _post()

    assert resp.status_code == 409
    body = resp.json()
    assert body["error"] == "job_not_completed"


@pytest.mark.anyio
async def test_running_job_returns_409():
    row = _make_row(status="running")
    with patch(
        "app.api.controllers.analysis.share.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _post()

    assert resp.status_code == 409
    body = resp.json()
    assert body["error"] == "job_not_completed"


@pytest.mark.anyio
async def test_failed_job_returns_409():
    row = _make_row(status="failed")
    with patch(
        "app.api.controllers.analysis.share.get_analysis_job_by_id",
        new=AsyncMock(return_value=row),
    ):
        resp = await _post()

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Token generation — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_succeeded_job_generates_share_token():
    row = _make_row(status="succeeded")
    with (
        patch(
            "app.api.controllers.analysis.share.get_analysis_job_by_id",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.api.controllers.analysis.share.update_share_token",
            new=AsyncMock(return_value=True),
        ),
    ):
        resp = await _post()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["shareToken"], str)
    assert len(body["shareToken"]) > 0
    assert "expiresAt" in body


@pytest.mark.anyio
async def test_share_token_is_32_chars_url_safe():
    """secrets.token_urlsafe(24) produces a 32-character URL-safe token."""
    row = _make_row(status="succeeded")
    captured_tokens: list[str] = []

    async def _capture_update(job_id: str, token: str, expires_at: datetime) -> bool:
        captured_tokens.append(token)
        return True

    with (
        patch(
            "app.api.controllers.analysis.share.get_analysis_job_by_id",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.api.controllers.analysis.share.update_share_token",
            new=_capture_update,
        ),
    ):
        resp = await _post()

    assert resp.status_code == 200
    assert len(captured_tokens) == 1
    token = captured_tokens[0]
    assert len(token) == 32
    # URL-safe base64 only contains A-Z, a-z, 0-9, -, _
    _safe_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    assert all(c in _safe_chars for c in token)


@pytest.mark.anyio
async def test_expiry_is_approximately_7_days():
    row = _make_row(status="succeeded")
    with (
        patch(
            "app.api.controllers.analysis.share.get_analysis_job_by_id",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.api.controllers.analysis.share.update_share_token",
            new=AsyncMock(return_value=True),
        ),
    ):
        before = datetime.now(UTC)
        resp = await _post()
        after = datetime.now(UTC)

    assert resp.status_code == 200
    expires_at = datetime.fromisoformat(resp.json()["expiresAt"])
    expected_low = before + timedelta(days=7)
    expected_high = after + timedelta(days=7)
    assert expected_low <= expires_at <= expected_high


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_existing_valid_share_token_is_returned():
    """When a valid share token already exists, return it without generating
    a new one."""
    row = _make_row(
        status="succeeded",
        share_token="existingtoken1234567890123456",
        share_expires=_FUTURE_SHARE_EXPIRES,
    )
    update_mock = AsyncMock(return_value=True)
    with (
        patch(
            "app.api.controllers.analysis.share.get_analysis_job_by_id",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.api.controllers.analysis.share.update_share_token",
            new=update_mock,
        ),
    ):
        resp = await _post()

    assert resp.status_code == 200
    body = resp.json()
    assert body["shareToken"] == "existingtoken1234567890123456"
    # update_share_token must NOT be called when returning existing token
    update_mock.assert_not_called()


@pytest.mark.anyio
async def test_expired_share_token_triggers_new_generation():
    """When the existing share token is expired, a new one should be generated."""
    row = _make_row(
        status="succeeded",
        share_token="expiredtoken1234567890123456",
        share_expires=_PAST_SHARE_EXPIRES,
    )
    update_mock = AsyncMock(return_value=True)
    with (
        patch(
            "app.api.controllers.analysis.share.get_analysis_job_by_id",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.api.controllers.analysis.share.update_share_token",
            new=update_mock,
        ),
    ):
        resp = await _post()

    assert resp.status_code == 200
    body = resp.json()
    # New token must differ from the expired one
    assert body["shareToken"] != "expiredtoken1234567890123456"
    update_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_job_disappears_between_fetch_and_update_returns_401():
    """If update_share_token returns False (row gone), return the auth error."""
    row = _make_row(status="succeeded")
    with (
        patch(
            "app.api.controllers.analysis.share.get_analysis_job_by_id",
            new=AsyncMock(return_value=row),
        ),
        patch(
            "app.api.controllers.analysis.share.update_share_token",
            new=AsyncMock(return_value=False),
        ),
    ):
        resp = await _post()

    assert resp.status_code == 401
