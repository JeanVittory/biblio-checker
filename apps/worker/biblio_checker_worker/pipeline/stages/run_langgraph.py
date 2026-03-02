from __future__ import annotations

from supabase import Client

from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.enums import JobStage
from biblio_checker_worker.jobs.errors import StageError
from biblio_checker_worker.langgraph.flow import start_analysis_flow
from biblio_checker_worker.pipeline.context import JobContext


def run_langgraph_stage(*, supabase: Client, ctx: JobContext) -> None:
    """Invoke the LangGraph analysis flow and capture its result.

    Steps:
    1. Advance stage to LANGGRAPH_RUNNING.
    2. Call start_analysis_flow; wrap any exception as a transient StageError.
    3. Advance stage to VERIFYING_REFERENCES.
    4. Persist the flow result onto ctx.result_json.

    Raises:
        StageError (transient=True): The LangGraph flow raised an exception.
        JobRepoError: Propagated from repo.update_stage; handled by the runner.
    """
    # Step 1: Mark stage as running.
    repo.update_stage(
        supabase,
        job_id=ctx.job.id,
        stage=JobStage.LANGGRAPH_RUNNING,
        token=ctx.token,
    )

    # Step 2: Execute the flow.
    try:
        result = start_analysis_flow(job=ctx.job, file_bytes=ctx.file_bytes)
    except Exception as exc:  # noqa: BLE001
        raise StageError(
            code="langgraph_flow_failed",
            detail=str(exc) or None,
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
