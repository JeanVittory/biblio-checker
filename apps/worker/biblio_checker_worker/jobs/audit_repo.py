from __future__ import annotations

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

_ERROR_DETAIL_MAX_LEN = 200


def _sanitize_detail(detail: str | None) -> str | None:
    if detail is None:
        return None
    return detail[:_ERROR_DETAIL_MAX_LEN]


def insert_job_event(
    supabase: Client,
    *,
    job_id: str,
    event_type: str,
    stage: str | None = None,
    status: str | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
    attempt: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        row: dict[str, Any] = {
            "job_id": job_id,
            "event_type": event_type,
            "stage": stage,
            "status": status,
            "error_code": error_code,
            "error_detail": _sanitize_detail(error_detail),
            "attempt": attempt,
            "metadata": metadata if metadata is not None else {},
        }
        supabase.table("job_events").insert(row).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to insert job event [event_type=%s, job_id=%s]: %s",
            event_type,
            job_id,
            exc,
        )


def build_reference_audit_entry(
    *,
    job_id: str,
    reference_id: str,
    raw_text: str | None = None,
    classification: str | None = None,
    confidence_score: float | None = None,
    reason_code: str | None = None,
    sources_checked: list[str],
    match_found: bool | None = None,
    error_detail: str | None = None,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "reference_id": reference_id,
        "raw_text": raw_text,
        "classification": classification,
        "confidence_score": confidence_score,
        "reason_code": reason_code,
        "sources_checked": sources_checked,
        "match_found": match_found,
        "error_detail": _sanitize_detail(error_detail),
    }


def insert_reference_audit_batch(
    supabase: Client,
    *,
    job_id: str,
    entries: list[dict[str, Any]],
) -> None:
    if not entries:
        return
    try:
        supabase.table("reference_audit_log").insert(entries).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to insert reference audit batch [job_id=%s, count=%d]: %s",
            job_id,
            len(entries),
            exc,
        )
