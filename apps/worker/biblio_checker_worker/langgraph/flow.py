from __future__ import annotations

import logging

from biblio_checker_worker.jobs.models import AnalysisJob

logger = logging.getLogger("biblio_checker_worker.langgraph")


def start_analysis_flow(*, job: AnalysisJob, file_bytes: bytes) -> dict:
    """Stub for the LangGraph analysis flow.

    Accepts the claimed job and the raw file bytes produced by the extract
    stage.  Returns a result dict that the persist stage writes to the
    database.

    This is a stub implementation that logs the invocation and returns an
    empty dict.  The real LangGraph graph will be wired in a later step.
    """
    logger.info(
        "LangGraph flow stub invoked (job_id=%s, file_bytes=%d).",
        job.id,
        len(file_bytes),
    )
    return {}
