from pathlib import PurePosixPath
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import settings
from app.schemas.analysis_jobs import AnalysisJobStatus

SOURCE_TYPE_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

SOURCE_TYPE_TO_EXTENSION: dict[str, str] = {
    "pdf": ".pdf",
    "docx": ".docx",
}


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

    @field_validator("path")
    @classmethod
    def path_must_be_safe(cls, v: str) -> str:
        if ".." in v or v.startswith("/") or "\\" in v:
            raise ValueError(
                "storage.path contains unsafe sequences "
                "(path traversal or absolute paths are not allowed)"
            )
        if "\x00" in v:
            raise ValueError("storage.path contains null bytes")
        return v


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

    @model_validator(mode="after")
    def check_cross_field_consistency(self) -> "VerifyAuthenticityRequest":
        errors: list[str] = []

        # Rule 1: sourceType <-> mimeType consistency
        expected_mime = SOURCE_TYPE_TO_MIME.get(self.document.sourceType)
        if expected_mime and self.document.mimeType != expected_mime:
            errors.append(
                f"document.sourceType '{self.document.sourceType}' "
                f"does not match document.mimeType '{self.document.mimeType}'"
            )

        # Rule 3: storage.path must contain the requestId
        request_id_str = str(self.requestId)
        if request_id_str not in self.storage.path:
            errors.append(
                f"storage.path must contain the requestId '{request_id_str}'"
            )

        # Rule 4: document.fileName must match the filename in storage.path
        path_filename = PurePosixPath(self.storage.path).name
        if self.document.fileName != path_filename:
            errors.append(
                f"document.fileName '{self.document.fileName}' does not match "
                f"the filename in storage.path '{path_filename}'"
            )

        # Rule 5: bucket must be in the allowed list
        if self.storage.bucket not in settings.allowed_buckets_set:
            errors.append(
                f"storage.bucket '{self.storage.bucket}' is not in the "
                f"allowed buckets: {sorted(settings.allowed_buckets_set)}"
            )

        # Rule 6: fileName extension must match sourceType
        expected_ext = SOURCE_TYPE_TO_EXTENSION.get(self.document.sourceType)
        if expected_ext:
            actual_ext = PurePosixPath(self.document.fileName).suffix.lower()
            if actual_ext != expected_ext:
                errors.append(
                    f"document.fileName extension '{actual_ext}' "
                    f"does not match sourceType '{self.document.sourceType}' "
                    f"(expected '{expected_ext}')"
                )

        if errors:
            raise ValueError("; ".join(errors))

        return self


class VerifyAuthenticityResponse(BaseModel):
    success: bool | None = None
    message: str
    jobId: str | None = None
    status: AnalysisJobStatus | None = None
