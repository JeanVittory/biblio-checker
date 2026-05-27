from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import structlog
from anyio.to_thread import run_sync
from postgrest.exceptions import APIError

from app.core.supabase_client import SupabaseClientError, get_supabase_admin_client
from app.services._db_failure_classifier import is_service_offline_exception

logger = structlog.stdlib.get_logger(__name__)


@dataclass(frozen=True)
class AnalysisJobsRepoError(Exception):
    code: str
    detail: str | None = None


@dataclass
class AnalysisJob:
    """Represents a row from the analysis_jobs table.

    The four file-specific columns (bucket, path, sha256, source_type) are
    optional because text-mode jobs leave them NULL.  ``input_kind`` defaults
    to ``'file'`` so that callers reading existing rows without the column
    remain backward-compatible.
    """

    id: str
    status: str
    stage: str
    input_kind: Literal["file", "text"] = "file"
    raw_reference_text: str | None = None
    bucket: str | None = None
    path: str | None = None
    sha256: str | None = None
    source_type: str | None = None
    locale: str | None = None
    poll_status_token: str | None = None
    poll_status_token_expires_at: datetime | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    result_json: Any = field(default=None)
    error_code: str | None = None
    error_detail: str | None = None


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
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_insert_failed",
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
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
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_insert_failed",
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
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
                "id, status, stage, result_json, error_code, error_detail,"
                " created_at, completed_at,"
                " poll_status_token, poll_status_token_expires_at,"
                " share_token, share_token_expires_at"
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
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_fetch_failed",
                job_id=job_id,
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
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
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_fetch_failed",
                job_id=job_id,
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
        logger.error(
            "analysis_job_fetch_failed",
            job_id=job_id,
            error_code="analysis_job_fetch_failed",
            error_detail=str(exc),
        )
        raise AnalysisJobsRepoError(
            code="analysis_job_fetch_failed", detail=str(exc) or None
        ) from exc


async def get_analysis_job_by_share_token(
    share_token: str,
) -> dict[str, Any] | None:
    """Fetch a single analysis_jobs row by share_token.

    Returns a restricted dict (MUST NOT include poll_status_token, job_token,
    bucket, path, or sha256) or None when no row matches the token.
    Raises AnalysisJobsRepoError on any DB / client error.
    """
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise AnalysisJobsRepoError(code=exc.code, detail=exc.detail) from exc

    def _select_sync() -> dict[str, Any] | None:
        resp = (
            supabase.table("analysis_jobs")
            .select(
                "id, status, stage, result_json, error_code, error_detail,"
                " created_at, completed_at,"
                " share_token, share_token_expires_at"
            )
            .eq("share_token", share_token)
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

    logger.info("analysis_job_fetching_by_share_token")
    try:
        result = await run_sync(_select_sync)
        logger.info(
            "analysis_job_fetched_by_share_token",
            found=result is not None,
        )
        return result
    except AnalysisJobsRepoError as exc:
        logger.error(
            "analysis_job_fetch_by_share_token_failed",
            error_code=exc.code,
            error_detail=exc.detail,
        )
        raise
    except APIError as exc:
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_fetch_by_share_token_failed",
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
        code = str(exc.code or "").strip()
        is_auth_err = code in ("401", "403")
        err_code = "db_unauthorized" if is_auth_err else "analysis_job_fetch_failed"
        logger.error(
            "analysis_job_fetch_by_share_token_failed",
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
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_fetch_by_share_token_failed",
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
        logger.error(
            "analysis_job_fetch_by_share_token_failed",
            error_code="analysis_job_fetch_failed",
            error_detail=str(exc),
        )
        raise AnalysisJobsRepoError(
            code="analysis_job_fetch_failed", detail=str(exc) or None
        ) from exc


async def update_share_token(
    job_id: str,
    share_token: str,
    expires_at: datetime,
) -> bool:
    """Update share_token and share_token_expires_at on an analysis_jobs row.

    Returns True if the row was found and updated, False if no row with
    that id exists.  Raises AnalysisJobsRepoError on DB / client errors.
    """
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise AnalysisJobsRepoError(code=exc.code, detail=exc.detail) from exc

    def _update_sync() -> bool:
        resp = (
            supabase.table("analysis_jobs")
            .update(
                {
                    "share_token": share_token,
                    "share_token_expires_at": expires_at.isoformat(),
                }
            )
            .eq("id", job_id)
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list):
            raise AnalysisJobsRepoError(
                code="analysis_job_update_failed",
                detail="DB update returned an unexpected response.",
            )
        return len(data) > 0

    logger.info("analysis_job_share_token_updating", job_id=job_id)
    try:
        updated = await run_sync(_update_sync)
        logger.info(
            "analysis_job_share_token_updated",
            job_id=job_id,
            updated=updated,
        )
        return updated
    except AnalysisJobsRepoError as exc:
        logger.error(
            "analysis_job_share_token_update_failed",
            job_id=job_id,
            error_code=exc.code,
            error_detail=exc.detail,
        )
        raise
    except APIError as exc:
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_share_token_update_failed",
                job_id=job_id,
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
        code = str(exc.code or "").strip()
        is_auth_err = code in ("401", "403")
        err_code = "db_unauthorized" if is_auth_err else "analysis_job_update_failed"
        logger.error(
            "analysis_job_share_token_update_failed",
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
            code="analysis_job_update_failed", detail=str(exc) or None
        ) from exc
    except Exception as exc:  # noqa: BLE001
        if is_service_offline_exception(exc):
            logger.error(
                "analysis_job_share_token_update_failed",
                job_id=job_id,
                error_code="service_offline",
                error_detail=str(exc),
            )
            raise AnalysisJobsRepoError(
                code="service_offline", detail=str(exc) or None
            ) from exc
        logger.error(
            "analysis_job_share_token_update_failed",
            job_id=job_id,
            error_code="analysis_job_update_failed",
            error_detail=str(exc),
        )
        raise AnalysisJobsRepoError(
            code="analysis_job_update_failed", detail=str(exc) or None
        ) from exc
