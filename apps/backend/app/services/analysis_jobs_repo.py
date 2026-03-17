from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog
from anyio.to_thread import run_sync
from postgrest.exceptions import APIError

from app.core.supabase_client import SupabaseClientError, get_supabase_admin_client

logger = structlog.stdlib.get_logger(__name__)


@dataclass(frozen=True)
class AnalysisJobsRepoError(Exception):
    code: str
    detail: str | None = None


async def create_analysis_job(row: dict[str, Any]) -> dict[str, Any]:
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise AnalysisJobsRepoError(code=exc.code, detail=exc.detail) from exc

    def _insert_sync() -> dict[str, Any]:
        resp = supabase.table("analysis_jobs").insert(row).execute()
        data = getattr(resp, "data", None)
        if not isinstance(data, list) or not data:
            raise AnalysisJobsRepoError(
                code="analysis_job_create_failed",
                detail="DB insert returned no row representation.",
            )
        if not isinstance(data[0], dict):
            raise AnalysisJobsRepoError(
                code="analysis_job_create_failed",
                detail="DB insert returned an unexpected row representation.",
            )
        return dict(data[0])

    logger.info("analysis_job_inserting")
    try:
        result = await run_sync(_insert_sync)
        job_id = result.get("id") or result.get("job_id")
        logger.info("analysis_job_inserted", job_id=job_id)
        return result
    except AnalysisJobsRepoError as exc:
        logger.error(
            "analysis_job_insert_failed",
            error_code=exc.code,
            error_detail=exc.detail,
        )
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        is_auth_err = code in ("401", "403")
        err_code = "db_unauthorized" if is_auth_err else "analysis_job_create_failed"
        logger.error(
            "analysis_job_insert_failed",
            error_code=err_code,
            error_detail=str(exc),
        )
        if is_auth_err:
            raise AnalysisJobsRepoError(
                code="db_unauthorized",
                detail=str(exc),
            ) from exc
        raise AnalysisJobsRepoError(
            code="analysis_job_create_failed", detail=str(exc) or None
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "analysis_job_insert_failed",
            error_code="analysis_job_create_failed",
            error_detail=str(exc),
        )
        raise AnalysisJobsRepoError(
            code="analysis_job_create_failed", detail=str(exc) or None
        ) from exc


async def get_analysis_job_by_id(job_id: str) -> dict[str, Any] | None:
    """Fetch a single analysis_jobs row by primary key.

    Returns the full row dict (including poll_status_token and
    poll_status_token_expires_at) or None when no row with that id exists.
    Raises AnalysisJobsRepoError on any DB / client error so callers can map
    it to a 502 uniformly.
    """
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise AnalysisJobsRepoError(code=exc.code, detail=exc.detail) from exc

    def _select_sync() -> dict[str, Any] | None:
        resp = (
            supabase.table("analysis_jobs")
            .select(
                "id, status, stage, results, error, created_at, completed_at,"
                " poll_status_token, poll_status_token_expires_at"
            )
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise AnalysisJobsRepoError(
                code="analysis_job_fetch_failed",
                detail="DB select returned an unexpected response.",
            )
        if not data:
            return None
        if not isinstance(data[0], dict):
            raise AnalysisJobsRepoError(
                code="analysis_job_fetch_failed",
                detail="DB select returned an unexpected row representation.",
            )
        return dict(data[0])

    logger.info("analysis_job_fetching", job_id=job_id)
    try:
        result = await run_sync(_select_sync)
        status = result.get("status") if result is not None else None
        logger.info("analysis_job_fetched", job_id=job_id, status=status)
        return result
    except AnalysisJobsRepoError as exc:
        logger.error(
            "analysis_job_fetch_failed",
            job_id=job_id,
            error_code=exc.code,
            error_detail=exc.detail,
        )
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        is_auth_err = code in ("401", "403")
        err_code = "db_unauthorized" if is_auth_err else "analysis_job_fetch_failed"
        logger.error(
            "analysis_job_fetch_failed",
            job_id=job_id,
            error_code=err_code,
            error_detail=str(exc),
        )
        if is_auth_err:
            raise AnalysisJobsRepoError(
                code="db_unauthorized",
                detail=str(exc),
            ) from exc
        raise AnalysisJobsRepoError(
            code="analysis_job_fetch_failed", detail=str(exc) or None
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "analysis_job_fetch_failed",
            job_id=job_id,
            error_code="analysis_job_fetch_failed",
            error_detail=str(exc),
        )
        raise AnalysisJobsRepoError(
            code="analysis_job_fetch_failed", detail=str(exc) or None
        ) from exc
