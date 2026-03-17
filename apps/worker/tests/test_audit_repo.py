from __future__ import annotations

from unittest.mock import MagicMock

from biblio_checker_worker.jobs.audit_repo import (
    build_reference_audit_entry,
    insert_job_event,
    insert_reference_audit_batch,
)

# ---------------------------------------------------------------------------
# insert_job_event
# ---------------------------------------------------------------------------


def test_insert_job_event_success() -> None:
    supabase = MagicMock()
    insert_job_event(supabase, job_id="job-1", event_type="job_created")
    supabase.table.assert_called_once_with("job_events")
    supabase.table("job_events").insert.assert_called_once()
    supabase.table("job_events").insert().execute.assert_called_once()


def test_insert_job_event_swallows_errors() -> None:
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "db down"
    )
    # Must not propagate the exception.
    insert_job_event(supabase, job_id="job-1", event_type="job_claimed")


def test_insert_job_event_truncates_error_detail() -> None:
    supabase = MagicMock()
    long_detail = "x" * 201
    insert_job_event(
        supabase,
        job_id="job-1",
        event_type="job_failed",
        error_detail=long_detail,
    )
    inserted_row = supabase.table("job_events").insert.call_args[0][0]
    assert inserted_row["error_detail"] == "x" * 200


def test_insert_job_event_default_metadata() -> None:
    supabase = MagicMock()
    insert_job_event(supabase, job_id="job-1", event_type="job_created", metadata=None)
    inserted_row = supabase.table("job_events").insert.call_args[0][0]
    assert inserted_row["metadata"] == {}


# ---------------------------------------------------------------------------
# build_reference_audit_entry
# ---------------------------------------------------------------------------


def test_build_reference_audit_entry_mapping() -> None:
    entry = build_reference_audit_entry(
        job_id="job-1",
        reference_id="ref-1",
        raw_text="Some author (2020)",
        classification="valid",
        confidence_score=0.95,
        reason_code="exact_match",
        sources_checked=["openalex", "arxiv"],
        match_found=True,
        error_detail=None,
    )
    assert entry["job_id"] == "job-1"
    assert entry["reference_id"] == "ref-1"
    assert entry["raw_text"] == "Some author (2020)"
    assert entry["classification"] == "valid"
    assert entry["confidence_score"] == 0.95
    assert entry["reason_code"] == "exact_match"
    assert entry["sources_checked"] == ["openalex", "arxiv"]
    assert entry["match_found"] is True
    assert entry["error_detail"] is None


def test_build_reference_audit_entry_truncates_error_detail() -> None:
    entry = build_reference_audit_entry(
        job_id="job-1",
        reference_id="ref-2",
        sources_checked=[],
        error_detail="y" * 201,
    )
    assert entry["error_detail"] == "y" * 200


def test_build_reference_audit_entry_no_id_or_created_at() -> None:
    entry = build_reference_audit_entry(
        job_id="job-1", reference_id="ref-3", sources_checked=[]
    )
    assert "id" not in entry
    assert "created_at" not in entry


# ---------------------------------------------------------------------------
# insert_reference_audit_batch
# ---------------------------------------------------------------------------


def test_insert_reference_audit_batch_success() -> None:
    supabase = MagicMock()
    entries = [{"job_id": "job-1", "reference_id": "ref-1"}]
    insert_reference_audit_batch(supabase, job_id="job-1", entries=entries)
    supabase.table.assert_called_once_with("reference_audit_log")
    supabase.table("reference_audit_log").insert.assert_called_once_with(entries)
    supabase.table("reference_audit_log").insert(entries).execute.assert_called_once()


def test_insert_reference_audit_batch_empty_entries() -> None:
    supabase = MagicMock()
    insert_reference_audit_batch(supabase, job_id="job-1", entries=[])
    supabase.table.assert_not_called()


def test_insert_reference_audit_batch_swallows_errors() -> None:
    supabase = MagicMock()
    supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "network error"
    )
    entries = [{"job_id": "job-1", "reference_id": "ref-1"}]
    # Must not propagate the exception.
    insert_reference_audit_batch(supabase, job_id="job-1", entries=entries)
