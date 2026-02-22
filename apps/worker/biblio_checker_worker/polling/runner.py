from __future__ import annotations

import logging
import time

from supabase import Client

from biblio_checker_worker.core.config import settings
from biblio_checker_worker.supabase.client import (
    SupabaseClientError,
    get_supabase_admin_client,
)


def poll_once(*, supabase: Client) -> None:
    logger = logging.getLogger("biblio_checker_worker.polling")
    logger.debug("Polling tick (table=%s).", settings.supabase_table)
    time.sleep(0.0)


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
