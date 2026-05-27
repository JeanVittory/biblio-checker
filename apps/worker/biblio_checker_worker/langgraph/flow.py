"""Entry point for the LangGraph analysis pipeline.

Provides two public entrypoints:
- ``start_analysis_flow()`` — file-mode pipeline (extract_text → … → assemble_report)
- ``start_text_analysis_flow()`` — text-mode pipeline
  (normalize_references → … → assemble_report)

Both initialize the lease renewal context (when a Supabase client is supplied)
and return a dict conforming to ResultsV1.

Implementation note (§ 4b strategy):
    Text-mode uses a **separate compiled subgraph** that starts at
    ``normalize_references`` and skips ``extract_text`` / ``parse_references``.
    This is the smallest possible diff: ``build_graph()`` is untouched, and the
    subgraph is built lazily from the same node functions and wiring that the
    main graph uses from ``normalize_references`` onward.

The compiled graphs are cached at module level — the graph structure is
stateless, so a single compiled instance is safe to reuse across jobs.
"""

from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.jobs.models import AnalysisJob
from biblio_checker_worker.langgraph.graph import build_graph, fan_out_verify
from biblio_checker_worker.langgraph.lease import (
    clear_lease_context,
    init_lease_context,
)
from biblio_checker_worker.langgraph.nodes.ai_adjudicate import ai_adjudicate
from biblio_checker_worker.langgraph.nodes.assemble import assemble_report
from biblio_checker_worker.langgraph.nodes.classify import classify_results
from biblio_checker_worker.langgraph.nodes.cross_patterns import analyze_cross_patterns
from biblio_checker_worker.langgraph.nodes.normalize import normalize_references
from biblio_checker_worker.langgraph.nodes.verify import verify_single_reference
from biblio_checker_worker.langgraph.state import GraphState

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph")

# Cached compiled graphs — stateless, safe to reuse across invocations.
_compiled_graph = None
_compiled_text_graph = None


def _get_graph():
    """Return the cached compiled file-mode graph, building it on first call."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def _build_text_graph():
    """Build and compile the text-mode subgraph.

    Topology (same as main graph from normalize_references onward):

        START → normalize_references → fan_out_verify
          → verify_single_reference → classify_results
          → analyze_cross_patterns → ai_adjudicate
          → assemble_report → END

    The text-mode entrypoint expects ``raw_references`` (not ``file_bytes``) in
    the initial state, so ``extract_text`` and ``parse_references`` are not
    needed.
    """
    graph = StateGraph(GraphState)  # type: ignore[type-var]

    graph.add_node("normalize_references", normalize_references)
    graph.add_node("verify_single_reference", verify_single_reference)
    graph.add_node("classify_results", classify_results)
    graph.add_node("analyze_cross_patterns", analyze_cross_patterns)
    graph.add_node("ai_adjudicate", ai_adjudicate)
    graph.add_node("assemble_report", assemble_report)

    graph.add_edge(START, "normalize_references")
    graph.add_conditional_edges("normalize_references", fan_out_verify)
    graph.add_edge("verify_single_reference", "classify_results")
    graph.add_edge("classify_results", "analyze_cross_patterns")
    graph.add_edge("analyze_cross_patterns", "ai_adjudicate")
    graph.add_edge("ai_adjudicate", "assemble_report")
    graph.add_edge("assemble_report", END)

    return graph.compile()


def _get_text_graph():
    """Return the cached compiled text-mode graph, building it on first call."""
    global _compiled_text_graph
    if _compiled_text_graph is None:
        _compiled_text_graph = _build_text_graph()
    return _compiled_text_graph


def start_analysis_flow(
    *,
    job: AnalysisJob,
    file_bytes: bytes,
    supabase=None,
) -> dict:
    """Run the LangGraph analysis pipeline end-to-end (file mode).

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


def start_text_analysis_flow(
    *,
    job: AnalysisJob,
    raw_reference_text: str,
    supabase=None,
) -> dict:
    """Run the LangGraph text-mode pipeline for a single pasted reference.

    Skips ``extract_text`` and ``parse_references`` by entering the graph at
    ``normalize_references`` directly.  The single reference is pre-populated
    into ``raw_references`` so the existing node sees the same input format it
    always receives from ``parse_references``.

    Args:
        job: The claimed analysis job (provides job_id, locale, job_token).
        raw_reference_text: The pasted bibliographic reference string.
        supabase: Optional Supabase client for lease renewal. Pass ``None``
            in tests to skip lease setup.

    Returns:
        A dict conforming to the ResultsV1 schema.

    Raises:
        Any exception raised inside the graph propagates to the caller
        (``run_langgraph_stage``), which wraps it as a transient
        ``StageError``. The ``finally`` block always clears the lease context.
    """
    locale = job.locale

    logger.info(
        "text_analysis_flow_started",
        job_id=str(job.id),
        locale=locale,
        text_length=len(raw_reference_text),
    )

    if supabase is not None and job.job_token is not None:
        settings = get_settings()
        init_lease_context(
            supabase=supabase,
            job_id=str(job.id),
            token=job.job_token,
            lease_seconds=settings.job_lease_seconds,
        )

    try:
        # ``normalize_references`` expects ``raw_references`` in the format
        # [{index: int, rawText: str}].  We supply the single reference at
        # index 0.  ``raw_text`` is kept for completeness (assemble_report
        # may reference it for metadata).
        initial_state: dict = {
            "job_id": str(job.id),
            "locale": locale,
            "raw_text": raw_reference_text,
            "raw_references": [
                {"index": 0, "rawText": raw_reference_text}
            ],
            "warnings": [],
            "total_references_detected": 1,
        }

        graph = _get_text_graph()
        final_state = graph.invoke(initial_state)

        result: dict = final_state.get("results_v1", {})

        # Safe-access pattern per spec § 11
        classification = (result.get("references") or [{}])[0].get(
            "classification", "unknown"
        )

        logger.info(
            "text_analysis_flow_completed",
            job_id=str(job.id),
            references_count=1,
            classification=classification,
        )

        return result

    except Exception:
        logger.error(
            "text_analysis_flow_failed",
            job_id=str(job.id),
        )
        raise

    finally:
        clear_lease_context()
