from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.problems import problem_response
from app.core.supabase_storage import SupabaseStorageError, download_object_bytes
from app.schemas.analysis import VerifyAuthenticityRequest, VerifyAuthenticityResponse
from app.services.integrity import (
    IntegrityShaMismatchError,
    verify_sha256_bytes,
)
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
        extracted_text = await extract_text_from_bytes_async(
            source_type=payload.document.sourceType,
            content=content,
            max_chars=int(settings.max_extracted_text_chars),
        )

        request.state.extracted_text = extracted_text
    except SupabaseStorageError as exc:
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
    )
