from __future__ import annotations

from supabase import Client

from biblio_checker_worker.jobs import repo
from biblio_checker_worker.jobs.enums import JobStage
from biblio_checker_worker.pipeline.context import JobContext


def persist_stage(*, supabase: Client, ctx: JobContext) -> None:
    """Write the analysis result to the database and mark the job succeeded.

    Steps:
    1. Advance stage to PERSISTING_RESULT.
    2. Call repo.mark_succeeded with the accumulated result_json.

    Any JobRepoError raised by either repo call propagates directly to the
    pipeline runner, which treats it as an unexpected error and handles
    requeue/failure logic accordingly.
    """
    # Step 1: Advance stage (JobRepoError propagates to runner).
    repo.update_stage(
        supabase,
        job_id=ctx.job.id,
        stage=JobStage.PERSISTING_RESULT,
        token=ctx.token,
    )

    # Step 2: Finalise job (JobRepoError propagates to runner).
    repo.mark_succeeded(
        supabase,
        job_id=ctx.job.id,
        result_json=ctx.result_json,
        token=ctx.token,
    )
