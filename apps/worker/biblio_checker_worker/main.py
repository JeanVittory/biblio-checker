from __future__ import annotations

import logging
import time

from biblio_checker_worker.core.config import settings
from biblio_checker_worker.polling.runner import run_forever


def _configure_logging() -> None:
    level_name = (settings.log_level or "INFO").upper().strip()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main() -> None:
    _configure_logging()
    logger = logging.getLogger("biblio_checker_worker")

    logger.info(
        "Worker starting (env=%s, table=%s, poll_interval=%ss)",
        settings.environment,
        settings.supabase_table,
        settings.poll_interval_seconds,
    )

    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("Worker stopped (KeyboardInterrupt).")
        time.sleep(0.05)
