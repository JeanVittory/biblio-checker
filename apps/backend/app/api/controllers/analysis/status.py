from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.analysis import JobStatusResponse
from app.schemas.analysis_jobs import AnalysisJobStatus
from app.services.analysis_jobs_repo import AnalysisJobsRepoError, get_analysis_job_by_id

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

    if isinstance(raw_expires_at, str):
        # Supabase returns ISO 8601 strings; parse and ensure UTC-aware
        expires_at = datetime.fromisoformat(raw_expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    elif isinstance(raw_expires_at, datetime):
        expires_at = raw_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        return _INVALID_TOKEN_RESPONSE

    if datetime.now(timezone.utc) >= expires_at:
        return _INVALID_TOKEN_RESPONSE

    # Build the response — never include job_token or token_expires_at
    status = AnalysisJobStatus(row["status"])

    raw_created_at = row.get("created_at")
    if isinstance(raw_created_at, str):
        submitted_at = datetime.fromisoformat(raw_created_at)
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)
    elif isinstance(raw_created_at, datetime):
        submitted_at = raw_created_at
        if submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=timezone.utc)
    else:
        return _SERVICE_UNAVAILABLE_RESPONSE

    raw_completed_at = row.get("completed_at")
    completed_at: datetime | None = None
    if raw_completed_at is not None:
        if isinstance(raw_completed_at, str):
            completed_at = datetime.fromisoformat(raw_completed_at)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
        elif isinstance(raw_completed_at, datetime):
            completed_at = raw_completed_at
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)

    result = row.get("results") if status == AnalysisJobStatus.SUCCEEDED else None
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
