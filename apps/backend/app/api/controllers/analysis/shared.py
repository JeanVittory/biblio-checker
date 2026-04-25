"""GET /api/analysis/shared/{shareToken} — public read endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.analysis import SharedAnalysisResponse
from app.schemas.results import ResultsV1
from app.services.analysis_jobs_repo import (
    AnalysisJobsRepoError,
    get_analysis_job_by_share_token,
)
from app.utils.datetime_coercion import coerce_utc_datetime

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter()

_MAX_TOKEN_LENGTH = 64

_NOT_FOUND_RESPONSE = JSONResponse(
    status_code=404,
    content={
        "success": False,
        "error": "not_found",
        "message": "Shared analysis not found or expired",
    },
)


@router.get("/shared/{shareToken}", response_model=None)
async def get_shared_analysis(
    shareToken: str,
) -> SharedAnalysisResponse | JSONResponse:
    # --- Validate token length before any DB call ---
    if len(shareToken) > _MAX_TOKEN_LENGTH:
        logger.warning(
            "shared_analysis_token_too_long",
            token_length=len(shareToken),
        )
        return _NOT_FOUND_RESPONSE

    logger.info("shared_analysis_requested")

    # --- Look up by share token ---
    try:
        row = await get_analysis_job_by_share_token(shareToken)
    except AnalysisJobsRepoError as exc:
        logger.warning(
            "shared_analysis_repo_error",
            error_code=exc.code,
        )
        # Return 404 for all error cases (enumeration-resistant)
        return _NOT_FOUND_RESPONSE

    if row is None:
        logger.info("shared_analysis_not_found")
        return _NOT_FOUND_RESPONSE

    # --- Validate expiry ---
    raw_expires_at = row.get("share_token_expires_at")
    if not raw_expires_at:
        return _NOT_FOUND_RESPONSE

    try:
        share_expires_at = coerce_utc_datetime(
            raw_expires_at, field="share_token_expires_at"
        )
    except ValueError:
        return _NOT_FOUND_RESPONSE

    if datetime.now(UTC) >= share_expires_at:
        logger.info("shared_analysis_token_expired")
        return _NOT_FOUND_RESPONSE

    # --- Validate job status ---
    status: str = row.get("status", "")
    if status != "succeeded":
        logger.info("shared_analysis_job_not_succeeded", status=status)
        return _NOT_FOUND_RESPONSE

    # --- Parse completedAt ---
    raw_completed_at = row.get("completed_at")
    completed_at_str: str | None = None
    if raw_completed_at is not None:
        try:
            completed_at_str = coerce_utc_datetime(
                raw_completed_at, field="completed_at"
            ).isoformat()
        except ValueError:
            # Non-fatal: return null completedAt rather than a 404
            completed_at_str = None

    # --- Validate result payload (graceful degradation) ---
    result: ResultsV1 | None = None
    raw_result = row.get("result_json")
    if raw_result is not None:
        try:
            result = ResultsV1.model_validate(raw_result)
        except Exception:
            logger.warning("shared_analysis_result_validation_failed")
            result = None

    job_id = str(row["id"])
    logger.info("shared_analysis_served", job_id=job_id)

    return SharedAnalysisResponse(
        success=True,
        jobId=job_id,
        status="succeeded",
        result=result,
        completedAt=completed_at_str,
        fileName=None,  # v1: no original_file_name column yet
        expiresAt=share_expires_at.isoformat(),
    )
