from __future__ import annotations

import structlog
from supabase import Client

from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.enums import JobStage
from biblio_checker_worker.jobs.errors import StageError
from biblio_checker_worker.langgraph.flow import (
    start_analysis_flow,
    start_text_analysis_flow,
)
from biblio_checker_worker.pipeline.context import JobContext

logger = structlog.stdlib.get_logger(__name__)


def run_langgraph_stage(*, supabase: Client, ctx: JobContext) -> None:
    """Invoke the LangGraph analysis flow and capture its result.

    Branches on ``ctx.job.input_kind``:
    - ``"text"``: calls ``start_text_analysis_flow`` with the pasted reference
      text set by ``extract_stage``.
    - ``"file"`` (default): calls the original ``start_analysis_flow`` with the
      downloaded file bytes.

    Both code paths share the same error-handling envelope.

    Steps:
    1. Advance stage to LANGGRAPH_RUNNING.
    2. Call the appropriate flow function; wrap any exception as a transient
       StageError.
    3. Advance stage to VERIFYING_REFERENCES.
    4. Persist the flow result onto ctx.result_json.

    Raises:
        StageError (transient=True): The LangGraph flow raised an exception.
        JobRepoError: Propagated from repo.update_stage; handled by the runner.
    """
    logger.info("langgraph_stage_starting")

    # Step 1: Mark stage as running.
    repo.update_stage(
        supabase,
        job_id=ctx.job.id,
        stage=JobStage.LANGGRAPH_RUNNING,
        token=ctx.token,
    )

    # Step 2: Execute the appropriate flow.
    try:
        if ctx.job.input_kind == "text":
            # raw_reference_text was validated and set by extract_stage.
            result = start_text_analysis_flow(
                job=ctx.job,
                raw_reference_text=ctx.raw_reference_text or "",
                supabase=supabase,
            )
        else:
            result = start_analysis_flow(
                job=ctx.job, file_bytes=ctx.file_bytes, supabase=supabase
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("langgraph_flow_exception")
        raise StageError(
            code="langgraph_flow_failed",
            detail="LangGraph analysis flow failed.",
            transient=True,
        ) from exc

    # Step 3: Advance stage to verifying.
    repo.update_stage(
        supabase,
        job_id=ctx.job.id,
        stage=JobStage.VERIFYING_REFERENCES,
        token=ctx.token,
    )

    # Step 4: Store result on context.
    ctx.result_json = result

    logger.info("langgraph_stage_complete")
