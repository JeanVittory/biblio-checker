from __future__ import annotations

import structlog

from biblio_checker_worker.jobs.models import AnalysisJob

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph")


def start_analysis_flow(*, job: AnalysisJob, file_bytes: bytes) -> dict:
    """Stub for the LangGraph analysis flow.

    Accepts the claimed job and the raw file bytes produced by the extract
    stage.  Returns a result dict that the persist stage writes to the
    database.

    This is a stub implementation that logs the invocation and returns an
    empty dict.  The real LangGraph graph will be wired in a later step.
    """
    logger.info("langgraph_flow_invoked", file_bytes=len(file_bytes))
    return {}
