from __future__ import annotations

import logging
from typing import Any

from anyio.to_thread import run_sync

from app.core.supabase_client import get_supabase_admin_client

logger = logging.getLogger(__name__)

_ERROR_DETAIL_MAX_LEN = 200


async def insert_job_event(
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
        supabase = get_supabase_admin_client()
        safe_detail = error_detail[:_ERROR_DETAIL_MAX_LEN] if error_detail else None
        row: dict[str, Any] = {
            "job_id": job_id,
            "event_type": event_type,
            "stage": stage,
            "status": status,
            "error_code": error_code,
            "error_detail": safe_detail,
            "attempt": attempt,
            "metadata": metadata if metadata is not None else {},
        }

        def _insert_sync() -> None:
            supabase.table("job_events").insert(row).execute()

        await run_sync(_insert_sync)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to insert job event [event_type=%s, job_id=%s]: %s",
            event_type,
            job_id,
            exc,
        )
