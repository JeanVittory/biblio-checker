"""Tests for POST /api/analysis/start-text (Step 03).

Coverage:
- Happy path: 200 with correct response shape and DB row content
- 422 validation failures (rawText length, whitespace, null byte, control chars,
  missing requestId, invalid locale, extra forbidden field)
- Verify rawText content is never emitted in logs (structlog capture)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import structlog
import structlog.testing

from app.main import app

URL = "/api/analysis/start-text"
VALID_REQUEST_ID = "4806aa68-ed88-4205-ae86-cc085eb463fd"
VALID_RAW_TEXT = "Smith, J. (2021). A study on climate change. Nature, 123, 456-478."
DUMMY_JOB_ID = "e8d916e8-72b5-4ba8-bca3-602a0ddf7d26"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


async def _post(payload: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.post(URL, json=payload)


def _valid_payload(**overrides) -> dict:
    base = {
        "requestId": VALID_REQUEST_ID,
        "reference": {"rawText": VALID_RAW_TEXT},
        "locale": "es",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fake Supabase stub for repo-level tests
# ---------------------------------------------------------------------------


def _make_fake_supabase(captured: dict):
    """Return a fake Supabase client that records the insert payload."""

    class _FakeTable:
        def insert(self, row):
            captured["payload"] = row
            return self

        def execute(self):
            return SimpleNamespace(
                data=[{**captured["payload"], "id": DUMMY_JOB_ID}]
            )

    class _FakeSupabase:
        def table(self, _name):
            return _FakeTable()

    return _FakeSupabase()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_happy_path_returns_200_with_correct_shape():
    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(return_value={"id": DUMMY_JOB_ID}),
    ):
        resp = await _post(_valid_payload())

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["jobId"] == DUMMY_JOB_ID
    assert body["status"] == "queued"
    assert "jobToken" in body
    assert body["jobToken"]  # non-empty string
    assert body["message"] == "Analysis started successfully"


@pytest.mark.anyio
async def test_happy_path_db_row_has_correct_fields():
    """Verify the dict passed to create_analysis_job has the right fields."""
    captured: dict = {}
    fake_supabase = _make_fake_supabase(captured)

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=fake_supabase,
    ):
        resp = await _post(_valid_payload())

    assert resp.status_code == 200
    payload = captured["payload"]
    assert payload["input_kind"] == "text"
    assert payload["raw_reference_text"] == VALID_RAW_TEXT
    # File fields must be absent (not sent as None — CHECK constraint wants NULL)
    assert "bucket" not in payload
    assert "path" not in payload
    assert "sha256" not in payload
    assert "source_type" not in payload


@pytest.mark.anyio
async def test_happy_path_trims_whitespace():
    """rawText is trimmed before insertion; trimmed value stored in DB."""
    padded = "   " + VALID_RAW_TEXT + "   "
    captured: dict = {}
    fake_supabase = _make_fake_supabase(captured)

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=fake_supabase,
    ):
        resp = await _post(_valid_payload(**{"reference": {"rawText": padded}}))

    assert resp.status_code == 200
    assert captured["payload"]["raw_reference_text"] == VALID_RAW_TEXT


@pytest.mark.anyio
async def test_happy_path_locale_pt():
    captured: dict = {}
    fake_supabase = _make_fake_supabase(captured)

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=fake_supabase,
    ):
        resp = await _post(_valid_payload(locale="pt"))

    assert resp.status_code == 200
    assert captured["payload"]["locale"] == "pt"


@pytest.mark.anyio
async def test_happy_path_locale_defaults_to_es():
    """Omitting locale should default to 'es'."""
    payload = {"requestId": VALID_REQUEST_ID, "reference": {"rawText": VALID_RAW_TEXT}}
    captured: dict = {}
    fake_supabase = _make_fake_supabase(captured)

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=fake_supabase,
    ):
        resp = await _post(payload)

    assert resp.status_code == 200
    assert captured["payload"]["locale"] == "es"


@pytest.mark.anyio
async def test_two_simultaneous_requests_produce_distinct_job_ids():
    """Two valid requests must produce different jobIds and jobTokens."""
    job_id_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    job_id_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(
            side_effect=[{"id": job_id_a}, {"id": job_id_b}]
        ),
    ):
        resp_a = await _post(_valid_payload())
        resp_b = await _post(
            _valid_payload(requestId="5906bb79-fe99-5316-bf97-dd196fc574ae")
        )

    # Both succeed
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    body_a = resp_a.json()
    body_b = resp_b.json()
    # Distinct jobIds
    assert body_a["jobId"] != body_b["jobId"]
    # Distinct jobTokens (generated independently via secrets.token_urlsafe)
    assert body_a["jobToken"] != body_b["jobToken"]


# ---------------------------------------------------------------------------
# 422: rawText validation failures
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_422_raw_text_too_short_after_trim():
    """19 chars after trim → 422."""
    short = "A" * 19  # exactly one below minimum
    resp = await _post(_valid_payload(**{"reference": {"rawText": short}}))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_raw_text_padded_to_appear_long_but_short_after_trim():
    """Whitespace-padded string whose trimmed value is 19 chars → 422."""
    short_trimmed = "A" * 19
    padded = "   " + short_trimmed + "   "
    resp = await _post(_valid_payload(**{"reference": {"rawText": padded}}))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_raw_text_too_long():
    """2001 chars → 422."""
    long_text = "A" * 2001
    resp = await _post(_valid_payload(**{"reference": {"rawText": long_text}}))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_raw_text_all_whitespace():
    """All-whitespace rawText → 422 (empty after trim)."""
    resp = await _post(_valid_payload(**{"reference": {"rawText": "   "}}))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_raw_text_contains_null_byte():
    """rawText with null byte → 422."""
    with_null = "Smith, J. (2021). Climate change study.\x00injected"
    resp = await _post(_valid_payload(**{"reference": {"rawText": with_null}}))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_raw_text_contains_bel_control_char():
    """rawText with \\x07 (BEL) → 422 (banned control char)."""
    with_bel = "Smith, J. (2021). A study on climate change.\x07alert"
    resp = await _post(_valid_payload(**{"reference": {"rawText": with_bel}}))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_raw_text_with_tab_is_accepted():
    """\\t (U+0009) is explicitly allowed per spec."""
    with_tab = "Smith, J. (2021).\tA study on climate change. Nature, 123, 456-478."
    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(return_value={"id": DUMMY_JOB_ID}),
    ):
        resp = await _post(_valid_payload(**{"reference": {"rawText": with_tab}}))
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_422_raw_text_with_newline_is_accepted():
    """\\n (U+000A) is explicitly allowed per spec."""
    with_newline = (
        "Smith, J. (2021). A study on climate change.\nNature, 123, 456-478."
    )
    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(return_value={"id": DUMMY_JOB_ID}),
    ):
        resp = await _post(_valid_payload(**{"reference": {"rawText": with_newline}}))
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_422_raw_text_with_carriage_return_is_accepted():
    """\\r (U+000D) is explicitly allowed per spec."""
    with_cr = (
        "Smith, J. (2021). A study on climate change.\rNature, 123, 456-478."
    )
    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(return_value={"id": DUMMY_JOB_ID}),
    ):
        resp = await _post(_valid_payload(**{"reference": {"rawText": with_cr}}))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 422: other field failures
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_422_missing_request_id():
    payload = {"reference": {"rawText": VALID_RAW_TEXT}, "locale": "es"}
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_invalid_locale_fr():
    resp = await _post(_valid_payload(locale="fr"))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_invalid_locale_es_es():
    """Region suffix 'es-ES' must be rejected (not normalized)."""
    resp = await _post(_valid_payload(locale="es-ES"))
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_422_extra_top_level_field_forbidden():
    """extra='forbid' — unknown top-level field must cause 422."""
    payload = _valid_payload()
    payload["unknownField"] = "should-be-rejected"
    resp = await _post(payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 500 (problem_response) on repo error
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_repo_error_returns_problem_json():
    from app.services.analysis_jobs_repo import AnalysisJobsRepoError

    with patch(
        "app.api.controllers.analysis.start_text.create_analysis_job",
        new=AsyncMock(
            side_effect=AnalysisJobsRepoError(
                code="analysis_job_create_failed",
                detail="connection refused",
            )
        ),
    ):
        resp = await _post(_valid_payload())

    assert resp.status_code == 502
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "analysis_job_create_failed"


# ---------------------------------------------------------------------------
# Log privacy: rawText content must never appear in log events
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_logs_do_not_contain_raw_text_content():
    """structlog capture must not include rawText value in any log event."""
    with structlog.testing.capture_logs() as cap_logs:
        with patch(
            "app.api.controllers.analysis.start_text.create_analysis_job",
            new=AsyncMock(return_value={"id": DUMMY_JOB_ID}),
        ):
            resp = await _post(_valid_payload())

    assert resp.status_code == 200

    raw_text_value = VALID_RAW_TEXT
    for log_entry in cap_logs:
        for v in log_entry.values():
            assert raw_text_value not in str(v), (
                f"rawText content found in log entry: {log_entry}"
            )
