from __future__ import annotations

import logging

from supabase import Client

from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.errors import JobRepoError, StageError, TerminalJobError
from biblio_checker_worker.jobs.models import AnalysisJob
from biblio_checker_worker.pipeline.context import JobContext
from biblio_checker_worker.pipeline.stages.extract import extract_stage
from biblio_checker_worker.pipeline.stages.persist import persist_stage
from biblio_checker_worker.pipeline.stages.run_langgraph import run_langgraph_stage

logger = logging.getLogger("biblio_checker_worker.pipeline")

# Ordered list of pipeline stage callables.  Each must accept (*, supabase, ctx).
_STAGES = [extract_stage, run_langgraph_stage, persist_stage]


def process_job(supabase: Client, job: AnalysisJob) -> None:
    """Execute the full analysis pipeline for a single claimed job.

    Iterates through the ordered stage list, passing a shared JobContext.
    All error handling and final repo state transitions are consolidated here
    so individual stages only need to raise the appropriate error type.

    Error handling contract:
    - TerminalJobError  -> mark_failed(requeue=False) unconditionally.
    - StageError        -> requeue only when transient=True AND attempts remain.
    - Unexpected        -> requeue when attempts remain; error_detail is a
                           generic string (raw exc detail is never written to
                           the DB to prevent information disclosure).
    - JobRepoError from mark_failed itself -> log CRITICAL, do not re-raise
                           (the lease will expire and another worker can retry).
    """
    logger.info(
        "Processing job id=%s attempt=%d/%d",
        job.id,
        job.attempts,
        job.max_attempts,
    )

    if job.job_token is None:
        raise TerminalJobError(
            code="missing_job_token",
            detail="Job was dispatched without a token.",
        )
    token = job.job_token

    ctx = JobContext(job=job, token=token)

    try:
        for stage in _STAGES:
            stage(supabase=supabase, ctx=ctx)
    except TerminalJobError as exc:
        _safe_mark_failed(
            supabase=supabase,
            job=job,
            token=token,
            error_code=exc.code,
            error_detail=exc.detail,
            requeue=False,
        )
        return
    except StageError as exc:
        requeue = exc.transient and job.attempts < job.max_attempts
        _safe_mark_failed(
            supabase=supabase,
            job=job,
            token=token,
            error_code=exc.code,
            error_detail=exc.detail,
            requeue=requeue,
        )
        return
    except Exception:
        # SECURITY: Do not write raw exception detail to the database.
        # Log the full traceback internally only.
        logger.error(
            "Job id=%s raised an unexpected exception",
            job.id,
            exc_info=True,
        )
        requeue = job.attempts < job.max_attempts
        _safe_mark_failed(
            supabase=supabase,
            job=job,
            token=token,
            error_code="unexpected_worker_error",
            error_detail="An unexpected internal error occurred.",
            requeue=requeue,
        )
        return

    logger.info("Job id=%s succeeded", job.id)


def _safe_mark_failed(
    *,
    supabase: Client,
    job: AnalysisJob,
    token: str,
    error_code: str,
    error_detail: str | None,
    requeue: bool,
) -> None:
    """Call repo.mark_failed and absorb any JobRepoError that it raises.

    If mark_failed itself fails there is nothing more the worker can do —
    the lease will expire and the job will become available again naturally.
    The failure is logged at CRITICAL so that on-call engineers are alerted.
    """
    if requeue:
        logger.warning(
            "Job id=%s requeued (code=%s, attempt=%d/%d)",
            job.id,
            error_code,
            job.attempts,
            job.max_attempts,
        )
    else:
        logger.error(
            "Job id=%s failed permanently (code=%s)",
            job.id,
            error_code,
        )

    try:
        repo.mark_failed(
            supabase,
            job_id=job.id,
            error_code=error_code,
            error_detail=error_detail,
            requeue=requeue,
            token=token,
        )
    except JobRepoError as exc:
        logger.critical(
            "Job id=%s mark_failed raised (code=%s) — lease will expire",
            job.id,
            exc.code,
        )
        # Do not re-raise: let the lease expire naturally.
