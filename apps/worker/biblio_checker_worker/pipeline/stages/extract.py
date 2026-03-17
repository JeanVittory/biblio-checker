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

    Steps:
    1. Download the file from Supabase Storage.
    2. Verify the SHA-256 digest against the value recorded on the job.
    3. Populate ctx.file_bytes with the downloaded content.
    4. Advance the job stage to EXTRACT_DONE via the repo layer.

    Raises:
        StageError (transient=True): Storage download failure.
        TerminalJobError: SHA-256 digest mismatch — the file is corrupted or
            was replaced; retrying would produce the same result.
        JobRepoError: Propagated from repo.update_stage; handled by the runner.
    """
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
    expected = ctx.job.sha256.lower()
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
