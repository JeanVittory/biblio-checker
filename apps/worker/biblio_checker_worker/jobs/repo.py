from __future__ import annotations

from datetime import UTC, datetime

import structlog
from postgrest.exceptions import APIError
from supabase import Client

from biblio_checker_worker.jobs.enums import JobStage
from biblio_checker_worker.jobs.errors import JobRepoError
from biblio_checker_worker.jobs.models import AnalysisJob

# Maximum number of characters preserved from error_detail before writing to DB.
# Truncation prevents info-disclosure of potentially sensitive exception messages.
_ERROR_DETAIL_MAX_LEN = 200

logger = structlog.stdlib.get_logger(__name__)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _sanitize_detail(detail: str | None) -> str | None:
    """Truncate error_detail to _ERROR_DETAIL_MAX_LEN characters."""
    if detail is None:
        return None
    return detail[:_ERROR_DETAIL_MAX_LEN]


def claim_one_job(
    supabase: Client,
    *,
    token: str,
    lease_seconds: int,
) -> AnalysisJob | None:
    """Attempt to atomically claim one queued job via the claim_analysis_job RPC.

    Returns an AnalysisJob if a job was claimed, or None when the queue is empty.
    Raises JobRepoError on any DB or client error.
    """
    try:
        resp = supabase.rpc(
            "claim_analysis_job",
            {"p_token": token, "p_lease_secs": lease_seconds},
        ).execute()
        data = getattr(resp, "data", None)
        if not isinstance(data, list) or not data:
            return None
        job = AnalysisJob.from_row(data[0])
        logger.info("job_claimed_rpc", job_id=str(job.id))
        return job
    except JobRepoError:
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        logger.error(
            "job_claim_rpc_failed",
            code=code,
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        if code in ("401", "403"):
            raise JobRepoError(code="db_unauthorized", detail=str(exc)) from exc
        raise JobRepoError(code="claim_failed", detail=str(exc) or None) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "job_claim_rpc_failed",
            code="claim_failed",
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        raise JobRepoError(code="claim_failed", detail=str(exc) or None) from exc


def update_stage(
    supabase: Client,
    *,
    job_id: str,
    stage: JobStage,
    token: str,
) -> None:
    """Advance the stage of a running job.

    The token guard (eq("job_token", token)) ensures that only the worker
    currently holding the lease can modify the job.  If the lease expired and
    another worker reclaimed the job, this update will match zero rows and a
    JobRepoError is raised.

    Raises JobRepoError when zero rows are updated or on any DB error.
    """
    try:
        resp = (
            supabase.table("analysis_jobs")
            .update({"stage": stage.value, "updated_at": _now_iso()})
            .eq("id", job_id)
            .eq("job_token", token)
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list) or not data:
            raise JobRepoError(
                code="stage_update_failed",
                detail="No matching row — possible lease expiry or token mismatch",
            )
        logger.info("job_stage_updated", job_id=job_id, stage=stage.value)
    except JobRepoError:
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        logger.error(
            "job_stage_update_failed",
            job_id=job_id,
            stage=stage.value,
            code=code,
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        if code in ("401", "403"):
            raise JobRepoError(code="db_unauthorized", detail=str(exc)) from exc
        raise JobRepoError(code="stage_update_failed", detail=str(exc) or None) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "job_stage_update_failed",
            job_id=job_id,
            stage=stage.value,
            code="stage_update_failed",
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        raise JobRepoError(code="stage_update_failed", detail=str(exc) or None) from exc


def mark_succeeded(
    supabase: Client,
    *,
    job_id: str,
    result_json: dict,
    token: str,
) -> None:
    """Mark a job as successfully completed and write the result payload.

    Clears the job_token and job_token_expires_at to release the lease.
    Raises JobRepoError when zero rows are updated or on any DB error.
    """
    now = _now_iso()
    try:
        resp = (
            supabase.table("analysis_jobs")
            .update(
                {
                    "status": "succeeded",
                    "stage": "done",
                    "result_json": result_json,
                    "job_token": None,
                    "job_token_expires_at": None,
                    "updated_at": now,
                    "completed_at": now,
                }
            )
            .eq("id", job_id)
            .eq("job_token", token)
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list) or not data:
            raise JobRepoError(
                code="mark_succeeded_failed",
                detail="No matching row — possible lease expiry or token mismatch",
            )
        logger.info("job_mark_succeeded", job_id=job_id)
    except JobRepoError:
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        logger.error(
            "job_mark_succeeded_failed",
            job_id=job_id,
            code=code,
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        if code in ("401", "403"):
            raise JobRepoError(code="db_unauthorized", detail=str(exc)) from exc
        raise JobRepoError(
            code="mark_succeeded_failed", detail=str(exc) or None
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "job_mark_succeeded_failed",
            job_id=job_id,
            code="mark_succeeded_failed",
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        raise JobRepoError(
            code="mark_succeeded_failed", detail=str(exc) or None
        ) from exc


def mark_failed(
    supabase: Client,
    *,
    job_id: str,
    error_code: str,
    error_detail: str | None,
    requeue: bool,
    token: str,
) -> None:
    """Mark a job as failed, optionally re-queuing it for a retry.

    When requeue=True the job is reset to (status=queued, stage=created) so
    that another worker can claim it on the next poll cycle.  The lease token
    is cleared in both cases.

    When requeue=False the stage is preserved to aid post-mortem debugging
    (per Step 01 transition T8).

    error_detail is sanitized (truncated) before being written to the DB to
    limit potential information disclosure.

    Raises JobRepoError when zero rows are updated or on any DB error.
    """
    now = _now_iso()
    safe_detail = _sanitize_detail(error_detail)

    if requeue:
        payload: dict = {
            "status": "queued",
            "stage": "created",
            "error_code": error_code,
            "error_detail": safe_detail,
            "job_token": None,
            "job_token_expires_at": None,
            "updated_at": now,
        }
    else:
        # Do NOT include "stage" — preserve current stage for debugging.
        payload = {
            "status": "failed",
            "error_code": error_code,
            "error_detail": safe_detail,
            "job_token": None,
            "job_token_expires_at": None,
            "updated_at": now,
            "completed_at": now,
        }

    try:
        resp = (
            supabase.table("analysis_jobs")
            .update(payload)
            .eq("id", job_id)
            .eq("job_token", token)
            .execute()
        )
        data = getattr(resp, "data", None)
        if not isinstance(data, list) or not data:
            raise JobRepoError(
                code="mark_failed_failed",
                detail="No matching row — possible lease expiry or token mismatch",
            )
        logger.info("job_mark_failed", job_id=job_id, requeue=requeue)
    except JobRepoError:
        raise
    except APIError as exc:
        code = str(exc.code or "").strip()
        logger.error(
            "job_mark_failed_failed",
            job_id=job_id,
            code=code,
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        if code in ("401", "403"):
            raise JobRepoError(code="db_unauthorized", detail=str(exc)) from exc
        raise JobRepoError(code="mark_failed_failed", detail=str(exc) or None) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "job_mark_failed_failed",
            job_id=job_id,
            code="mark_failed_failed",
            error_type=type(exc).__name__,
            detail_preview=str(exc)[:80],
        )
        raise JobRepoError(code="mark_failed_failed", detail=str(exc) or None) from exc


def renew_lease(
    supabase: Client,
    *,
    job_id: str,
    token: str,
    lease_seconds: int,
) -> bool:
    """Renew the worker lease for a running job.

    Returns True if the lease was renewed, False if the job was not found
    or the token didn't match (e.g., the job was reclaimed by another worker).

    Does NOT raise on failure — lease renewal failure should not crash the
    pipeline.  Errors are logged at WARNING level.
    """
    try:
        resp = supabase.rpc(
            "renew_analysis_job_lease",
            {"p_job_id": job_id, "p_token": token, "p_lease_secs": lease_seconds},
        ).execute()
        renewed: bool = bool(getattr(resp, "data", False))
        if renewed:
            logger.debug("lease_renewed", job_id=job_id)
        else:
            logger.warning(
                "lease_renewal_failed", job_id=job_id, error="rpc returned false"
            )
        return renewed
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "lease_renewal_failed",
            job_id=job_id,
            error=str(exc)[:120],
        )
        return False
