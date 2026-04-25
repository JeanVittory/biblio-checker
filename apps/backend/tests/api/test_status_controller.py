"""Tests for the localized 401 response on GET /api/analysis/status.

When a poll_token / jobId is not found the controller returns a 401 whose
``error`` field is translated according to the Accept-Language header.

All tests mock ``get_analysis_job_by_id`` to return ``None`` so that the
"job not found → invalid token" branch is exercised without a real database.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app

STATUS_URL = "/api/analysis/status"

# Any non-empty strings satisfy the min_length=1 query validation.
_DUMMY_JOB_ID = "does-not-exist"
_DUMMY_TOKEN = "does-not-exist"


async def _get(accept_language: str | None = None) -> httpx.Response:
    """Issue GET /api/analysis/status with a non-existent jobId/jobToken."""
    headers = {}
    if accept_language is not None:
        headers["Accept-Language"] = accept_language

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.get(
            STATUS_URL,
            params={"jobId": _DUMMY_JOB_ID, "jobToken": _DUMMY_TOKEN},
            headers=headers,
        )


# ---------------------------------------------------------------------------
# Per-locale tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_invalid_token_returns_localized_detail_es():
    """Accept-Language: es-MX → Spanish error message."""
    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = await _get(accept_language="es-MX")

    assert resp.status_code == 401
    assert resp.json()["error"] == "Token inválido o expirado."


@pytest.mark.anyio
async def test_invalid_token_returns_localized_detail_pt():
    """Accept-Language: pt-BR → Portuguese error message."""
    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = await _get(accept_language="pt-BR")

    assert resp.status_code == 401
    assert resp.json()["error"] == "Token inválido ou expirado."


@pytest.mark.anyio
async def test_invalid_token_returns_localized_detail_en():
    """Accept-Language: en → English error message."""
    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = await _get(accept_language="en")

    assert resp.status_code == 401
    assert resp.json()["error"] == "Invalid or expired token."


@pytest.mark.anyio
async def test_invalid_token_unsupported_locale_falls_back_to_spanish():
    """Accept-Language: fr (unsupported) → falls back to the default Spanish message."""
    with patch(
        "app.api.controllers.analysis.status.get_analysis_job_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = await _get(accept_language="fr")

    assert resp.status_code == 401
    assert resp.json()["error"] == "Token inválido o expirado."
