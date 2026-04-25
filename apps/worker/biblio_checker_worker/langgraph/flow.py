"""Entry point for the LangGraph analysis pipeline.

Provides ``start_analysis_flow()`` which:
1. Builds the initial graph state from the AnalysisJob and file bytes.
2. Initializes the lease renewal context (when a Supabase client is supplied).
3. Invokes the compiled LangGraph graph.
4. Extracts the ``results_v1`` dict from the final state.
5. Clears the lease context (always, even on error).

The compiled graph is cached at module level — the graph structure is
stateless, so a single compiled instance is safe to reuse across jobs.
"""

from __future__ import annotations

import structlog

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.jobs.models import AnalysisJob
from biblio_checker_worker.langgraph.graph import build_graph
from biblio_checker_worker.langgraph.lease import (
    clear_lease_context,
    init_lease_context,
)

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph")

# Cached compiled graph — stateless, safe to reuse across invocations.
_compiled_graph = None


def _get_graph():
    """Return the cached compiled graph, building it on first call."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def start_analysis_flow(
    *,
    job: AnalysisJob,
    file_bytes: bytes,
    supabase=None,
) -> dict:
    """Run the LangGraph analysis pipeline end-to-end.

    Args:
        job: The claimed analysis job (provides job_id, source_type,
            job_token).
        file_bytes: Raw document bytes (PDF or DOCX) downloaded from
            Supabase Storage.
        supabase: Optional Supabase client. When supplied, lease renewal is
            initialized before graph invocation so long-running graphs keep
            the job lease alive. Pass ``None`` in tests to skip lease setup.

    Returns:
        A dict conforming to the ResultsV1 schema (as produced by
        ``assemble_report`` via ``model_dump()``).

    Raises:
        Any exception raised inside the graph propagates to the caller
        (``run_langgraph_stage``), which wraps it as a transient
        ``StageError``. The ``finally`` block always clears the lease context.
    """
    logger.info(
        "langgraph_flow_starting",
        job_id=str(job.id),
        source_type=job.source_type,
        file_bytes=len(file_bytes),
    )

    # Initialize lease renewal context so graph nodes can call
    # renew_lease_if_needed() without needing direct Supabase access.
    if supabase is not None and job.job_token is not None:
        settings = get_settings()
        init_lease_context(
            supabase=supabase,
            job_id=str(job.id),
            token=job.job_token,
            lease_seconds=settings.job_lease_seconds,
        )

    try:
        initial_state = {
            "job_id": str(job.id),
            "source_type": job.source_type,
            "file_bytes": file_bytes,
            "locale": job.locale,
        }

        graph = _get_graph()
        final_state = graph.invoke(initial_state)

        result: dict = final_state.get("results_v1", {})

        logger.info(
            "langgraph_flow_complete",
            job_id=str(job.id),
            references_analyzed=len(result.get("references", [])),
        )

        return result

    except Exception:
        logger.error(
            "langgraph_flow_failed",
            job_id=str(job.id),
        )
        raise

    finally:
        clear_lease_context()
