from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anyio.to_thread import run_sync
from postgrest.exceptions import APIError

from app.core.supabase_client import SupabaseClientError, get_supabase_admin_client


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

    try:
        return await run_sync(_insert_sync)
    except AnalysisJobsRepoError:
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        if code in ("401", "403"):
            raise AnalysisJobsRepoError(
                code="db_unauthorized",
                detail=str(exc),
            ) from exc
        raise AnalysisJobsRepoError(
            code="analysis_job_create_failed", detail=str(exc) or None
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise AnalysisJobsRepoError(
            code="analysis_job_create_failed", detail=str(exc) or None
        ) from exc
