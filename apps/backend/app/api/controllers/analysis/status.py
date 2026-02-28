from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.analysis import JobStatusResponse
from app.schemas.analysis_jobs import AnalysisJobStatus
from app.schemas.results import ResultsV1
from app.services.analysis_jobs_repo import (
    AnalysisJobsRepoError,
    get_analysis_job_by_id,
)
from app.utils.datetime_coercion import coerce_utc_datetime

router = APIRouter()

_INVALID_TOKEN_RESPONSE = JSONResponse(
    status_code=401,
    content={"error": "Invalid or expired token"},
)

_JOB_NOT_FOUND_RESPONSE = JSONResponse(
    status_code=404,
    content={"error": "Invalid or expired token"},
)

_SERVICE_UNAVAILABLE_RESPONSE = JSONResponse(
    status_code=502,
    content={"error": "Service temporarily unavailable"},
)


@router.get("/status", response_model=JobStatusResponse)
async def get_job_status(
    jobId: str = Query(..., min_length=1),
    jobToken: str = Query(..., min_length=1),
) -> JobStatusResponse | JSONResponse:
    try:
        row = await get_analysis_job_by_id(jobId)
    except AnalysisJobsRepoError:
        return _SERVICE_UNAVAILABLE_RESPONSE

    # Job not found — return 404 (same message as token mismatch to prevent enumeration)
    if row is None:
        return _JOB_NOT_FOUND_RESPONSE

    # Token comparison
    stored_token: str | None = row.get("job_token")
    if not stored_token or stored_token != jobToken:
        return _INVALID_TOKEN_RESPONSE

    # Expiry check
    raw_expires_at = row.get("token_expires_at")
    if not raw_expires_at:
        return _INVALID_TOKEN_RESPONSE

    try:
        expires_at = coerce_utc_datetime(raw_expires_at, field="token_expires_at")
    except ValueError:
        return _INVALID_TOKEN_RESPONSE

    if datetime.now(UTC) >= expires_at:
        return _INVALID_TOKEN_RESPONSE

    # Build the response — never include job_token or token_expires_at
    status = AnalysisJobStatus(row["status"])

    raw_created_at = row.get("created_at")
    try:
        submitted_at = coerce_utc_datetime(raw_created_at, field="created_at")
    except ValueError:
        return _SERVICE_UNAVAILABLE_RESPONSE

    raw_completed_at = row.get("completed_at")
    completed_at: datetime | None = None
    if raw_completed_at is not None:
        try:
            completed_at = coerce_utc_datetime(raw_completed_at, field="completed_at")
        except ValueError:
            return _SERVICE_UNAVAILABLE_RESPONSE

    result: ResultsV1 | None = None
    if status == AnalysisJobStatus.SUCCEEDED:
        raw_results = row.get("results")
        if raw_results is not None:
            try:
                result = ResultsV1.model_validate(raw_results)
            except Exception:
                # Backward compat: invalid/legacy payload → return null, no crash.
                result = None

    error = row.get("error") if status == AnalysisJobStatus.FAILED else None

    return JobStatusResponse(
        jobId=str(row["id"]),
        status=status,
        stage=row.get("stage"),
        result=result,
        error=error,
        submittedAt=submitted_at,
        completedAt=completed_at,
    )
