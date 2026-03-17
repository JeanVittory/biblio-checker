from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.supabase_client import SupabaseClientError
from app.services.audit_repo import insert_job_event

JOB_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EVENT_TYPE = "job_created"


def _make_mock_client() -> MagicMock:
    """Return a MagicMock that satisfies the .table().insert().execute() chain."""
    client = MagicMock()
    return client


@pytest.mark.anyio
async def test_insert_job_event_success():
    """Happy path: correct row is passed to .table("job_events").insert().execute()."""
    mock_client = _make_mock_client()

    with patch(
        "app.services.audit_repo.get_supabase_admin_client",
        return_value=mock_client,
    ):
        await insert_job_event(
            job_id=JOB_ID,
            event_type=EVENT_TYPE,
            stage="created",
            status="queued",
            attempt=1,
            metadata={"source": "test"},
        )

    expected_row = {
        "job_id": JOB_ID,
        "event_type": EVENT_TYPE,
        "stage": "created",
        "status": "queued",
        "error_code": None,
        "error_detail": None,
        "attempt": 1,
        "metadata": {"source": "test"},
    }
    mock_client.table.assert_called_once_with("job_events")
    mock_client.table("job_events").insert.assert_called_once_with(expected_row)
    mock_client.table("job_events").insert(expected_row).execute.assert_called_once()


@pytest.mark.anyio
async def test_insert_job_event_truncates_error_detail():
    """error_detail longer than 200 chars is truncated to exactly 200 chars."""
    long_detail = "x" * 201
    mock_client = _make_mock_client()

    with patch(
        "app.services.audit_repo.get_supabase_admin_client",
        return_value=mock_client,
    ):
        await insert_job_event(
            job_id=JOB_ID,
            event_type=EVENT_TYPE,
            error_detail=long_detail,
        )

    inserted_row = mock_client.table("job_events").insert.call_args[0][0]
    assert inserted_row["error_detail"] == "x" * 200


@pytest.mark.anyio
async def test_insert_job_event_swallows_api_error():
    """APIError raised during insert must not propagate — fire-and-forget."""
    from postgrest.exceptions import APIError

    mock_client = _make_mock_client()
    mock_client.table.return_value.insert.return_value.execute.side_effect = APIError(
        {"message": "db error", "code": "500", "details": "", "hint": ""}
    )

    with patch(
        "app.services.audit_repo.get_supabase_admin_client",
        return_value=mock_client,
    ):
        # Must not raise
        await insert_job_event(job_id=JOB_ID, event_type=EVENT_TYPE)


@pytest.mark.anyio
async def test_insert_job_event_swallows_client_error():
    """SupabaseClientError raised by get_supabase_admin_client must not propagate."""
    with patch(
        "app.services.audit_repo.get_supabase_admin_client",
        side_effect=SupabaseClientError(code="server_misconfigured"),
    ):
        # Must not raise
        await insert_job_event(job_id=JOB_ID, event_type=EVENT_TYPE)


@pytest.mark.anyio
async def test_insert_job_event_default_metadata():
    """When metadata=None, the inserted row must contain metadata={}."""
    mock_client = _make_mock_client()

    with patch(
        "app.services.audit_repo.get_supabase_admin_client",
        return_value=mock_client,
    ):
        await insert_job_event(
            job_id=JOB_ID,
            event_type=EVENT_TYPE,
            metadata=None,
        )

    inserted_row = mock_client.table("job_events").insert.call_args[0][0]
    assert inserted_row["metadata"] == {}
