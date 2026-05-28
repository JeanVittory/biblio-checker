import re
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.config import settings
from app.schemas.analysis_jobs import AnalysisJobStatus
from app.schemas.results import ResultsV1

# Supported locales — must stay in sync with the DB CHECK constraint and the
# worker i18n module.
Locale = Literal["es", "pt", "en"]

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
    locale: Locale = Field(
        default="es",
        description=(
            "Language for worker-rendered text (decisionReason, warnings[].message). "
            "Must be a canonical two-letter code: 'es', 'pt', or 'en'. "
            "Region suffixes (e.g. 'es-ES') are NOT normalised server-side and will "
            "cause a 422 validation error. Immutable after job creation."
        ),
    )

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
            errors.append(f"storage.path must contain the requestId '{request_id_str}'")

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


# ---------------------------------------------------------------------------
# Text-mode schemas (single-reference paste flow)
# ---------------------------------------------------------------------------

# Banned control chars: U+0001–U+001F except \t (0x09), \n (0x0A), \r (0x0D)
_BANNED_CONTROL_RE = re.compile(r"[\x01-\x08\x0b\x0c\x0e-\x1f]")


class TextReferencePayload(BaseModel):
    rawText: str = Field(..., min_length=1)

    @field_validator("rawText", mode="before")
    @classmethod
    def validate_raw_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("rawText must be a string")
        # Strip leading/trailing whitespace first
        trimmed = v.strip()
        # Reject all-whitespace (empty after strip)
        if not trimmed:
            raise ValueError("rawText must not be empty or all whitespace")
        # Length check on trimmed value
        if len(trimmed) < 20:
            raise ValueError(
                f"rawText must be at least 20 characters after trimming "
                f"(got {len(trimmed)})"
            )
        if len(trimmed) > 2000:
            raise ValueError(
                f"rawText must be at most 2000 characters after trimming "
                f"(got {len(trimmed)})"
            )
        # Null byte check
        if "\x00" in trimmed:
            raise ValueError("rawText must not contain null bytes")
        # Banned ASCII control character check
        if _BANNED_CONTROL_RE.search(trimmed):
            raise ValueError(
                "rawText must not contain ASCII control characters "
                "(U+0001–U+001F except \\t, \\n, \\r)"
            )
        return trimmed


class VerifyTextReferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requestId: UUID
    reference: TextReferencePayload
    locale: Locale = Field(default="es")


class VerifyAuthenticityResponse(BaseModel):
    success: bool | None = None
    message: str
    jobId: str | None = None
    status: AnalysisJobStatus | None = None
    jobToken: str | None = None


class JobStatusResponse(BaseModel):
    jobId: str
    status: AnalysisJobStatus
    stage: str | None = None
    result: ResultsV1 | None = None
    error: str | None = None
    errorCode: str | None = None
    submittedAt: datetime
    completedAt: datetime | None = None


class ShareTokenResponse(BaseModel):
    """Response body for POST /api/analysis/share (success path)."""

    success: bool
    shareToken: str
    expiresAt: str  # ISO 8601


class SharedAnalysisResponse(BaseModel):
    """Response body for GET /api/analysis/shared/{shareToken} (success path)."""

    success: bool
    jobId: str
    status: Literal["succeeded"]
    result: ResultsV1 | None
    completedAt: str | None  # ISO 8601
    fileName: str | None  # always null in v1 (security requirement)
    expiresAt: str  # ISO 8601
