from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.problems import problem_response
from app.core.supabase_storage import SupabaseStorageError
from app.schemas.references import VerifyAuthenticityRequest, VerifyAuthenticityResponse
from app.services.integrity import (
    IntegrityShaMismatchError,
    verify_supabase_object_sha256,
)

router = APIRouter()


@router.post("/verify-authenticity", response_model=VerifyAuthenticityResponse)
def verify_authenticity(
    payload: VerifyAuthenticityRequest,
) -> VerifyAuthenticityResponse | JSONResponse:
    try:
        verify_supabase_object_sha256(
            bucket=payload.storage.bucket,
            path=payload.storage.path,
            sha256=payload.integrity.sha256,
        )
    except SupabaseStorageError as exc:
        return problem_response(exc.code, detail_override=exc.detail)
    except IntegrityShaMismatchError:
        return problem_response(
            "integrity_sha_mismatch",
            extra={"requestId": str(payload.requestId)},
        )

    return VerifyAuthenticityResponse(
        message="Document authenticity verified successfully",
        success=True,
    )
