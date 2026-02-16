from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentPayload(BaseModel):
    fileName: str = Field(..., min_length=1)
    mimeType: Literal[
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    sourceType: Literal["pdf", "docx"]


class StoragePayload(BaseModel):
    bucket: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    provider: Literal["supabase"]


class IntegrityPayload(BaseModel):
    sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-fA-F0-9]{64}$",
    )


class VerifyAuthenticityRequest(BaseModel):
    document: DocumentPayload
    extractMode: Literal["backend_extract_references"]
    requestId: UUID
    storage: StoragePayload
    integrity: IntegrityPayload


class VerifyAuthenticityResponse(BaseModel):
    success: bool | None = None
    message: str
