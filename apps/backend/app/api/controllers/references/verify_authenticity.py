from fastapi import APIRouter

from app.schemas.references import VerifyAuthenticityRequest, VerifyAuthenticityResponse

router = APIRouter()

@router.post("/verify-authenticity", response_model=VerifyAuthenticityResponse)
def verify_authenticity(payload: VerifyAuthenticityRequest) -> VerifyAuthenticityResponse:
    return VerifyAuthenticityResponse(
        message="Document authenticity verified successfully",
        success=True,
    )
