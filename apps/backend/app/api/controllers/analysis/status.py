from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from app.api.i18n.http_errors import t
from app.schemas.analysis import JobStatusResponse
from app.schemas.analysis_jobs import AnalysisJobStatus
from app.schemas.results import ResultsV1
from app.services.analysis_jobs_repo import (
    AnalysisJobsRepoError,
    get_analysis_job_by_id,
)
from app.utils.datetime_coercion import coerce_utc_datetime

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter()


def _invalid_token_response(accept_language: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": t("invalid_or_expired_token", accept_language)},
    )


def _service_unavailable_response(accept_language: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": t("service_temporarily_unavailable", accept_language)},
    )


@router.get("/status", response_model=JobStatusResponse)
async def get_job_status(
    jobId: str = Query(..., min_length=1),
    jobToken: str = Query(..., min_length=1),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> JobStatusResponse | JSONResponse:
    logger.info("job_status_requested", job_id=jobId)

    try:
        row = await get_analysis_job_by_id(jobId)
    except AnalysisJobsRepoError as exc:
        logger.warning(
            "job_status_repo_error",
            job_id=jobId,
            error_code=exc.code,
        )
        return _service_unavailable_response(accept_language)

    # Job not found — return 404 (same message as token mismatch to prevent enumeration)
    if row is None:
        logger.warning("job_status_not_found", job_id=jobId)
        return _invalid_token_response(accept_language)

    # Token comparison
    stored_token: str | None = row.get("poll_status_token")
    if not stored_token or stored_token != jobToken:
        logger.warning("job_status_token_invalid", job_id=jobId)
        return _invalid_token_response(accept_language)

    # Expiry check
    raw_expires_at = row.get("poll_status_token_expires_at")
    if not raw_expires_at:
        logger.warning("job_status_token_invalid", job_id=jobId)
        return _invalid_token_response(accept_language)

    try:
        expires_at = coerce_utc_datetime(
            raw_expires_at, field="poll_status_token_expires_at"
        )
    except ValueError:
        logger.warning("job_status_token_invalid", job_id=jobId)
        return _invalid_token_response(accept_language)

    if datetime.now(UTC) >= expires_at:
        logger.warning("job_status_token_invalid", job_id=jobId)
        return _invalid_token_response(accept_language)

    # Build the response — never include poll_status_token or
    # poll_status_token_expires_at
    status = AnalysisJobStatus(row["status"])

    raw_created_at = row.get("created_at")
    try:
        submitted_at = coerce_utc_datetime(raw_created_at, field="created_at")
    except ValueError:
        return _service_unavailable_response(accept_language)

    raw_completed_at = row.get("completed_at")
    completed_at: datetime | None = None
    if raw_completed_at is not None:
        try:
            completed_at = coerce_utc_datetime(raw_completed_at, field="completed_at")
        except ValueError:
            return _service_unavailable_response(accept_language)

    result: ResultsV1 | None = None
    if status == AnalysisJobStatus.SUCCEEDED:
        raw_results = row.get("result_json")
        if raw_results is not None:
            try:
                result = ResultsV1.model_validate(raw_results)
            except Exception:
                # Backward compat: invalid/legacy payload → return null, no crash.
                logger.warning("job_status_result_validation_failed", job_id=jobId)
                result = None

    error: str | None = None
    error_code: str | None = None
    if status == AnalysisJobStatus.FAILED:
        error = row.get("error_detail")
        raw_error_code = row.get("error_code")
        if isinstance(raw_error_code, str) and raw_error_code:
            error_code = raw_error_code

    return JobStatusResponse(
        jobId=str(row["id"]),
        status=status,
        stage=row.get("stage"),
        result=result,
        error=error,
        errorCode=error_code,
        submittedAt=submitted_at,
        completedAt=completed_at,
    )
