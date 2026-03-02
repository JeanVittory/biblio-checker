from __future__ import annotations

import logging
import secrets
import time

from supabase import Client

from biblio_checker_worker.core.config import settings
from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.errors import JobRepoError
from biblio_checker_worker.pipeline.runner import process_job
from biblio_checker_worker.supabase.client import (
    SupabaseClientError,
    get_supabase_admin_client,
)

logger = logging.getLogger("biblio_checker_worker.polling")


def poll_once(*, supabase: Client) -> None:
    token = secrets.token_urlsafe(settings.job_token_bytes)
    try:
        job = repo.claim_one_job(
            supabase, token=token, lease_seconds=settings.job_lease_seconds
        )
    except JobRepoError as exc:
        logger.error("Failed to claim job (code=%s): %s", exc.code, exc.detail)
        return
    if job is None:
        logger.debug("No jobs available.")
        return
    logger.info("Claimed job id=%s attempt=%d/%d", job.id, job.attempts, job.max_attempts)
    process_job(supabase=supabase, job=job)


def run_forever() -> None:
    logger = logging.getLogger("biblio_checker_worker.polling")
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise RuntimeError(f"Supabase misconfigured: {exc.code}") from exc

    logger.info("Polling loop started.")
    while True:
        poll_once(supabase=supabase)
        time.sleep(max(1, int(settings.poll_interval_seconds)))
