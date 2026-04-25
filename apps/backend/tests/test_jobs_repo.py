"""Round-trip tests for create_analysis_job in analysis_jobs_repo.

Tests verify that the ``locale`` field (and other required fields) are
forwarded verbatim to the Supabase insert call, without touching a real
database.

The module-level ``get_supabase_admin_client`` is patched with a lightweight
stub whose ``table().insert().execute()`` chain captures the payload and
returns a minimal synthetic response.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.analysis_jobs_repo import create_analysis_job

# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------

_MINIMAL_ROW: dict = {
    "sha256": "a" * 64,
    "source_type": "pdf",
    "storage_path": "uploads/test.pdf",
    "locale": "pt",
}


def _make_fake_supabase(captured: dict):
    """Return a fake Supabase client that records the insert payload."""

    class _FakeTable:
        def insert(self, row):
            captured["payload"] = row
            return self

        def execute(self):
            return SimpleNamespace(data=[{**captured["payload"], "id": "fake-uuid"}])

    class _FakeSupabase:
        def table(self, _name):
            return _FakeTable()

    return _FakeSupabase()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_analysis_job_persists_locale_pt():
    """locale='pt' must be forwarded verbatim to the DB insert payload."""
    captured: dict = {}
    fake_client = _make_fake_supabase(captured)

    row = {**_MINIMAL_ROW, "locale": "pt"}

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=fake_client,
    ):
        result = await create_analysis_job(row=row)

    assert captured["payload"]["locale"] == "pt"
    assert result is not None
    assert result["id"] == "fake-uuid"


@pytest.mark.anyio
async def test_create_analysis_job_persists_locale_es():
    """locale='es' (default) must also round-trip correctly through the insert."""
    captured: dict = {}
    fake_client = _make_fake_supabase(captured)

    row = {**_MINIMAL_ROW, "locale": "es"}

    with patch(
        "app.services.analysis_jobs_repo.get_supabase_admin_client",
        return_value=fake_client,
    ):
        result = await create_analysis_job(row=row)

    assert captured["payload"]["locale"] == "es"
    assert result is not None
    assert result["id"] == "fake-uuid"
