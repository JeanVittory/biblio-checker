from __future__ import annotations

import time

import structlog

from biblio_checker_worker.core.config import settings
from biblio_checker_worker.core.logging import setup_logging
from biblio_checker_worker.polling.runner import run_forever

logger = structlog.stdlib.get_logger("biblio_checker_worker")


def main() -> None:
    setup_logging()
    logger.info(
        "worker_starting",
        environment=settings.environment,
        table=settings.supabase_table,
        poll_interval=settings.poll_interval_seconds,
    )

    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("worker_stopped")
        time.sleep(0.05)
