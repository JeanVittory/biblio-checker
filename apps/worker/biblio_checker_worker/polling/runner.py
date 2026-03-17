from __future__ import annotations

import secrets
import time

import structlog
from supabase import Client

from biblio_checker_worker.core.config import settings
from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.errors import JobRepoError
from biblio_checker_worker.pipeline.runner import process_job
from biblio_checker_worker.supabase.client import (
    SupabaseClientError,
    get_supabase_admin_client,
)

logger = structlog.stdlib.get_logger("biblio_checker_worker.polling")


def poll_once(*, supabase: Client) -> None:
    token = secrets.token_urlsafe(settings.job_token_bytes)
    try:
        job = repo.claim_one_job(
            supabase, token=token, lease_seconds=settings.job_lease_seconds
        )
    except JobRepoError as exc:
        logger.error("claim_failed", code=exc.code, detail=exc.detail)
        return
    if job is None:
        logger.debug("no_jobs_available")
        return
    logger.info(
        "job_claimed",
        job_id=str(job.id),
        attempt=job.attempts,
        max_attempts=job.max_attempts,
    )
    process_job(supabase=supabase, job=job)


def run_forever() -> None:
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise RuntimeError(f"Supabase misconfigured: {exc.code}") from exc

    logger.info("polling_loop_started")
    while True:
        poll_once(supabase=supabase)
        time.sleep(max(1, int(settings.poll_interval_seconds)))
