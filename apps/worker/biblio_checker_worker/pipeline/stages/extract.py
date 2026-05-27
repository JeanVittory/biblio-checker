from __future__ import annotations

import hashlib

import structlog
from supabase import Client

from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.enums import JobStage
from biblio_checker_worker.jobs.errors import StageError, TerminalJobError
from biblio_checker_worker.pipeline.context import JobContext

logger = structlog.stdlib.get_logger(__name__)


def extract_stage(*, supabase: Client, ctx: JobContext) -> None:
    """Download the source file, verify its SHA-256 checksum, and populate ctx.

    For file-mode jobs (``input_kind == "file"``):
    1. Download the file from Supabase Storage.
    2. Verify the SHA-256 digest against the value recorded on the job.
    3. Populate ctx.file_bytes with the downloaded content.
    4. Advance the job stage to EXTRACT_DONE via the repo layer.

    For text-mode jobs (``input_kind == "text"``):
    1. Validate that ``raw_reference_text`` is non-empty (fail fast if not).
    2. Populate ctx.raw_reference_text from the job model.
    3. Skip Supabase Storage download and SHA-256 verification entirely.
    4. Advance the job stage to EXTRACT_DONE via the repo layer.

    Raises:
        TerminalJobError: ``text_reference_missing`` when text-mode job has
            no reference text (NULL or whitespace-only).
        StageError (transient=True): Storage download failure (file-mode only).
        TerminalJobError: ``integrity_sha_mismatch`` — file corrupted or
            replaced; retrying would produce the same result (file-mode only).
        JobRepoError: Propagated from repo.update_stage; handled by the runner.
    """
    if ctx.job.input_kind == "text":
        _extract_text_mode(supabase=supabase, ctx=ctx)
    else:
        _extract_file_mode(supabase=supabase, ctx=ctx)


def _extract_text_mode(*, supabase: Client, ctx: JobContext) -> None:
    """Early-return path for text-mode jobs. No Supabase Storage access."""
    raw_text = ctx.job.raw_reference_text

    # Validate: must be non-empty after stripping whitespace.
    if not raw_text or not raw_text.strip():
        raise TerminalJobError(
            code="text_reference_missing",
            detail="Text-mode job has no raw_reference_text.",
        )

    ctx.raw_reference_text = raw_text

    logger.info(
        "extract_stage_skipped_text_mode",
        job_id=str(ctx.job.id),
    )

    # Advance stage (JobRepoError propagates to the runner).
    repo.update_stage(
        supabase,
        job_id=ctx.job.id,
        stage=JobStage.EXTRACT_DONE,
        token=ctx.token,
    )

    logger.info("extract_stage_done")


def _extract_file_mode(*, supabase: Client, ctx: JobContext) -> None:
    """Original file-download path. Logic is unchanged from pre-Step-04."""
    # Step 1: Download file from storage.
    logger.info("extract_downloading", bucket=ctx.job.bucket, path=ctx.job.path)
    try:
        file_bytes: bytes = supabase.storage.from_(ctx.job.bucket).download(
            ctx.job.path
        )
    except Exception as exc:  # noqa: BLE001
        raise StageError(
            code="storage_download_failed",
            detail=str(exc) or None,
            transient=True,
        ) from exc

    logger.info("extract_download_complete", size_bytes=len(file_bytes))

    # Step 2: SHA-256 integrity check.
    actual = hashlib.sha256(file_bytes).hexdigest()
    expected = (ctx.job.sha256 or "").lower()
    if actual != expected:
        logger.warning(
            "extract_sha_mismatch",
            expected_prefix=expected[:12],
            actual_prefix=actual[:12],
        )
        raise TerminalJobError(
            code="integrity_sha_mismatch",
            detail="File integrity check failed.",
        )

    logger.info("extract_sha_verified")

    # Step 3: Populate context.
    ctx.file_bytes = file_bytes

    # Step 4: Advance stage (JobRepoError propagates to the runner).
    repo.update_stage(
        supabase,
        job_id=ctx.job.id,
        stage=JobStage.EXTRACT_DONE,
        token=ctx.token,
    )

    logger.info("extract_stage_done")
