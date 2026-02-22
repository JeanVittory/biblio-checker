from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class ProblemDef:
    status: int
    title: str
    default_detail: str


PROBLEM_DEFS: dict[str, ProblemDef] = {
    "integrity_sha_mismatch": ProblemDef(
        status=409,
        title="Integrity check failed",
        default_detail="The provided SHA-256 does not match the stored file.",
    ),
    "storage_not_found": ProblemDef(
        status=404,
        title="Stored file not found",
        default_detail="The file could not be found in storage.",
    ),
    "storage_unauthorized": ProblemDef(
        status=502,
        title="Storage authorization failed",
        default_detail="The server could not access the storage provider.",
    ),
    "storage_download_failed": ProblemDef(
        status=502,
        title="Storage download failed",
        default_detail="The server could not download the file from storage.",
    ),
    "file_too_large": ProblemDef(
        status=413,
        title="File too large",
        default_detail="The uploaded file exceeds the maximum allowed size.",
    ),
    "server_misconfigured": ProblemDef(
        status=500,
        title="Server misconfigured",
        default_detail="The server is missing required configuration.",
    ),
    "text_extraction_unavailable": ProblemDef(
        status=500,
        title="Text extraction unavailable",
        default_detail="The server is missing required text extraction dependencies.",
    ),
    "text_extraction_failed": ProblemDef(
        status=422,
        title="Text extraction failed",
        default_detail="The server could not extract text from the document.",
    ),
    "extracted_text_too_large": ProblemDef(
        status=413,
        title="Extracted text too large",
        default_detail="The extracted text exceeds the maximum allowed size.",
    ),
    "db_unauthorized": ProblemDef(
        status=502,
        title="Database authorization failed",
        default_detail="The server could not access the database provider.",
    ),
    "analysis_job_create_failed": ProblemDef(
        status=502,
        title="Analysis job creation failed",
        default_detail="The server could not create the analysis job.",
    ),
}


def _problem_type(code: str) -> str:
    return f"urn:biblio-checker:problem:{code}"


def problem_response(
    code: str,
    *,
    detail_override: str | None = None,
    instance: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    definition = PROBLEM_DEFS.get(code)
    if definition is None:
        definition = ProblemDef(
            status=500,
            title="Unknown error",
            default_detail="An unexpected error occurred.",
        )
        code = "unknown_error"

    body: dict[str, Any] = {
        "type": _problem_type(code),
        "title": definition.title,
        "status": definition.status,
        "detail": (detail_override or definition.default_detail),
        "code": code,
    }
    if instance:
        body["instance"] = instance
    if extra:
        body["extra"] = extra

    return JSONResponse(
        status_code=definition.status,
        content=body,
        media_type="application/problem+json",
    )
