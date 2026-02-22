from __future__ import annotations

import logging
from typing import Any


def start_analysis_flow(*, job: dict[str, Any]) -> None:
    logger = logging.getLogger("biblio_checker_worker.langgraph")
    logger.info("LangGraph flow stub (job_id=%s).", job.get("id"))
