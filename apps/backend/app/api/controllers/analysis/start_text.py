import secrets
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.problems import problem_response
from app.schemas.analysis import VerifyAuthenticityResponse, VerifyTextReferenceRequest
from app.schemas.analysis_jobs import AnalysisJobStage, AnalysisJobStatus
from app.services.analysis_jobs_repo import AnalysisJobsRepoError, create_analysis_job

logger = structlog.stdlib.get_logger(__name__)

router = APIRouter()


@router.post("/start-text", response_model=VerifyAuthenticityResponse)
async def start_text_analysis(
    payload: VerifyTextReferenceRequest,
) -> VerifyAuthenticityResponse | JSONResponse:
    # rawText is already trimmed by the field_validator; read trimmed length only
    trimmed_text = payload.reference.rawText
    text_length = len(trimmed_text)

    logger.info(
        "analysis_text_start_requested",
        requestId=str(payload.requestId),
        locale=payload.locale,
        text_length=text_length,
    )

    try:
        poll_token = secrets.token_urlsafe(32)
        poll_token_expires_at = datetime.now(UTC) + timedelta(hours=1)

        job_row = {
            "status": AnalysisJobStatus.QUEUED.value,
            "stage": AnalysisJobStage.CREATED.value,
            "input_kind": "text",
            "raw_reference_text": trimmed_text,
            "poll_status_token": poll_token,
            "poll_status_token_expires_at": poll_token_expires_at.isoformat(),
            "locale": payload.locale,
        }
        inserted = await create_analysis_job(job_row)
        job_id = (
            inserted.get("id")
            or inserted.get("job_id")
            or inserted.get("jobId")
            or inserted.get("jobid")
        )
        if not job_id:
            return problem_response(
                "analysis_job_create_failed",
                detail_override="DB insert succeeded but no job id was returned.",
            )

        logger.info(
            "analysis_text_job_created",
            job_id=job_id,
            requestId=str(payload.requestId),
        )

    except AnalysisJobsRepoError as exc:
        logger.warning(
            "analysis_text_repo_error",
            error_code=exc.code,
            error_detail=exc.detail,
        )
        return problem_response(exc.code, detail_override=exc.detail)

    # TODO: Call worker

    return VerifyAuthenticityResponse(
        message="Analysis started successfully",
        success=True,
        jobId=str(job_id),
        status=AnalysisJobStatus.QUEUED,
        jobToken=poll_token,
    )
