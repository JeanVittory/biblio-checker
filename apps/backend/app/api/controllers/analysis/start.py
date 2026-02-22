from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.problems import problem_response
from app.schemas.analysis import VerifyAuthenticityRequest, VerifyAuthenticityResponse
from app.schemas.analysis_jobs import AnalysisJobStage, AnalysisJobStatus
from app.services.analysis_jobs_repo import AnalysisJobsRepoError, create_analysis_job
from app.services.integrity import (
    IntegrityShaMismatchError,
    verify_sha256_bytes,
)
from app.services.supabase_storage import SupabaseStorageError, download_object_bytes
from app.services.text_extraction import (
    TextExtractionError,
    extract_text_from_bytes_async,
)

router = APIRouter()


@router.post("/start", response_model=VerifyAuthenticityResponse)
async def start_analysis(
    payload: VerifyAuthenticityRequest,
    request: Request,
) -> VerifyAuthenticityResponse | JSONResponse:
    try:
        content = await download_object_bytes(
            bucket=payload.storage.bucket, path=payload.storage.path
        )
        verify_sha256_bytes(
            content=content,
            sha256=payload.integrity.sha256,
        )
        await extract_text_from_bytes_async(
            source_type=payload.document.sourceType,
            content=content,
            max_chars=int(settings.max_extracted_text_chars),
        )

        job_row = {
            "status": AnalysisJobStatus.QUEUED.value,
            "stage": AnalysisJobStage.CREATED.value,
            "bucket": payload.storage.bucket,
            "path": payload.storage.path,
            "sha256": payload.integrity.sha256,
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

    except SupabaseStorageError as exc:
        return problem_response(exc.code, detail_override=exc.detail)
    except AnalysisJobsRepoError as exc:
        return problem_response(exc.code, detail_override=exc.detail)
    except IntegrityShaMismatchError:
        return problem_response(
            "integrity_sha_mismatch",
            extra={"requestId": str(payload.requestId)},
        )
    except TextExtractionError as exc:
        return problem_response(exc.code, detail_override=exc.detail)

    return VerifyAuthenticityResponse(
        message="Analysis started successfully",
        success=True,
        jobId=str(job_id),
        status=AnalysisJobStatus.QUEUED,
    )
