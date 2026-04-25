"""POST /api/analysis/share — generate (or return existing) share token."""

from __future__ import annotations

import hmac
import secrets
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.i18n.http_errors import t
from app.schemas.analysis import ShareTokenResponse
from app.schemas.analysis_jobs import AnalysisJobStatus
from app.services.analysis_jobs_repo import (
    AnalysisJobsRepoError,
    get_analysis_job_by_id,
    update_share_token,
)
from app.utils.datetime_coercion import coerce_utc_datetime

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter()

_SHARE_TOKEN_TTL_DAYS = 7
_MAX_COLLISION_RETRIES = 3


class ShareRequest(BaseModel):
    jobId: str = Field(..., min_length=1)
    jobToken: str = Field(..., min_length=1)


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


@router.post("/share", response_model=None)
async def generate_share_token(
    body: ShareRequest,
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> ShareTokenResponse | JSONResponse:
    job_id = body.jobId
    job_token = body.jobToken

    logger.info("share_token_requested", job_id=job_id)

    # --- Fetch job row ---
    try:
        row = await get_analysis_job_by_id(job_id)
    except AnalysisJobsRepoError as exc:
        logger.warning(
            "share_token_repo_error",
            job_id=job_id,
            error_code=exc.code,
        )
        return _service_unavailable_response(accept_language)

    # Job not found — same generic response as status endpoint (enumeration-resistant)
    if row is None:
        logger.warning("share_token_job_not_found", job_id=job_id)
        return _invalid_token_response(accept_language)

    # --- Authenticate: constant-time token comparison ---
    stored_token: str | None = row.get("poll_status_token")
    if not stored_token or not hmac.compare_digest(stored_token, job_token):
        logger.warning("share_token_auth_failed", job_id=job_id)
        return _invalid_token_response(accept_language)

    # --- Authenticate: expiry check ---
    raw_expires_at = row.get("poll_status_token_expires_at")
    if not raw_expires_at:
        logger.warning("share_token_auth_failed", job_id=job_id)
        return _invalid_token_response(accept_language)

    try:
        poll_token_expires_at = coerce_utc_datetime(
            raw_expires_at, field="poll_status_token_expires_at"
        )
    except ValueError:
        logger.warning("share_token_auth_failed", job_id=job_id)
        return _invalid_token_response(accept_language)

    if datetime.now(UTC) >= poll_token_expires_at:
        logger.warning("share_token_auth_failed", job_id=job_id)
        return _invalid_token_response(accept_language)

    # --- Authorization: only succeeded jobs can be shared ---
    status = AnalysisJobStatus(row["status"])
    if status != AnalysisJobStatus.SUCCEEDED:
        logger.warning("share_token_job_not_completed", job_id=job_id, status=status)
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": "job_not_completed",
                "message": "Only completed jobs can be shared",
            },
        )

    # --- Idempotency: return existing token if still valid ---
    existing_share_token: str | None = row.get("share_token")
    existing_expires_raw = row.get("share_token_expires_at")

    if existing_share_token and existing_expires_raw:
        try:
            existing_expires_at = coerce_utc_datetime(
                existing_expires_raw, field="share_token_expires_at"
            )
            if datetime.now(UTC) < existing_expires_at:
                logger.info("share_token_reused", job_id=job_id)
                return ShareTokenResponse(
                    success=True,
                    shareToken=existing_share_token,
                    expiresAt=existing_expires_at.isoformat(),
                )
        except ValueError:
            # Corrupt expiry — fall through to generate a new token
            pass

    # --- Generate new token (with collision retry) ---
    new_expires_at = datetime.now(UTC) + timedelta(days=_SHARE_TOKEN_TTL_DAYS)

    for attempt in range(1, _MAX_COLLISION_RETRIES + 1):
        new_token = secrets.token_urlsafe(24)
        try:
            updated = await update_share_token(job_id, new_token, new_expires_at)
        except AnalysisJobsRepoError as exc:
            # Detect UNIQUE constraint violation by error detail string
            # (postgrest surfaces Postgres error codes in the detail)
            detail_str = (exc.detail or "").lower()
            code_str = (exc.code or "").lower()
            is_unique_violation = (
                "23505" in detail_str
                or "unique" in detail_str
                or "23505" in code_str
                or "unique" in code_str
            )
            if is_unique_violation and attempt < _MAX_COLLISION_RETRIES:
                logger.warning(
                    "share_token_collision_retry",
                    job_id=job_id,
                    attempt=attempt,
                )
                continue
            logger.error(
                "share_token_update_failed",
                job_id=job_id,
                error_code=exc.code,
                attempt=attempt,
            )
            return _service_unavailable_response(accept_language)

        if not updated:
            # Row disappeared between fetch and update
            logger.warning("share_token_job_disappeared", job_id=job_id)
            return _invalid_token_response(accept_language)

        logger.info("share_token_generated", job_id=job_id)
        return ShareTokenResponse(
            success=True,
            shareToken=new_token,
            expiresAt=new_expires_at.isoformat(),
        )

    # All retries exhausted
    logger.error("share_token_collision_exhausted", job_id=job_id)
    return JSONResponse(
        status_code=500,
        content={"error": t("internal_error", accept_language)},
    )
