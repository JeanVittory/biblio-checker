"""LangGraph graph construction and wiring for the Biblio Checker pipeline.

Graph topology (deterministic — no LLM-driven routing):

    START
      └─► extract_text
            └─► parse_references
                  └─► normalize_references
                        └─► [fan_out_verify] ──► verify_single_reference (×N, parallel)
                                                        └─► classify_results (fan-in)
                                                                └─► assemble_report
                                                                        └─► END

The fan-out is driven by ``Send()`` — one invocation per normalized reference.
LangGraph manages concurrency internally; ``settings.max_references`` caps the
maximum number of simultaneous ``verify_single_reference`` calls.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send  # type: ignore[import-untyped]

from biblio_checker_worker.core.config import get_settings
from biblio_checker_worker.langgraph.nodes.assemble import assemble_report
from biblio_checker_worker.langgraph.nodes.classify import classify_results
from biblio_checker_worker.langgraph.nodes.extract_text import extract_text
from biblio_checker_worker.langgraph.nodes.normalize import normalize_references
from biblio_checker_worker.langgraph.nodes.parse_references import parse_references
from biblio_checker_worker.langgraph.nodes.verify import verify_single_reference
from biblio_checker_worker.langgraph.state import GraphState


def fan_out_verify(state: GraphState) -> list[Send]:
    """Route each normalized reference to its own verify_single_reference invocation.

    When there are no normalized references (empty document or LLM returned no
    references), skips verification entirely and routes directly to
    ``classify_results`` with empty data so the graph can still produce a valid
    ResultsV1 with zero references.

    When the number of references exceeds ``settings.max_references``, the list
    is truncated and a ``references_truncated`` warning is attached to the first
    ``Send`` so it is merged into the parent state via the ``operator.add``
    reducer.

    Args:
        state: Current graph state after ``normalize_references`` has run.

    Returns:
        A list of ``Send`` objects — one per reference to verify, or a single
        ``Send`` to ``classify_results`` when the reference list is empty.
    """
    settings = get_settings()
    normalized: list[dict] = state.get("normalized_references", [])  # type: ignore[call-overload]

    if not normalized:
        # No references to verify — skip directly to classify_results.
        # Pass warnings=[] (not the accumulated state warnings) to avoid
        # duplicating warnings already stored via the operator.add reducer.
        return [
            Send(
                "classify_results",
                {
                    "verified_references": [],
                    "classified_references": [],
                    "warnings": [],
                },
            )
        ]

    normalized_original = normalized
    truncation_warning: dict | None = None

    if len(normalized) > settings.max_references:
        normalized = normalized[: settings.max_references]
        truncation_warning = {
            "code": "references_truncated",
            "message": (
                f"El documento excede el límite de {settings.max_references}"
                f" referencias. Solo se procesaron las primeras"
                f" {settings.max_references}."
            ),
            "referenceId": None,
            "details": {
                "total_detected": len(normalized_original),
                "max_allowed": settings.max_references,
            },
        }

    sends: list[Send] = []
    for ref in normalized:
        sends.append(
            Send(
                "verify_single_reference",
                {
                    "job_id": state["job_id"],
                    "reference": ref,
                    "warnings": [],
                    "verified_references": [],
                },
            )
        )

    # Attach the truncation warning to the first Send so it is merged into
    # the parent state's warnings list via the operator.add reducer.
    if truncation_warning is not None and sends:
        first = sends[0]
        sends[0] = Send(
            "verify_single_reference",
            {
                **first.args,
                "warnings": [truncation_warning],
            },
        )

    return sends


def build_graph():
    """Construct, wire, and compile the analysis StateGraph.

    Registers all six pipeline nodes and connects them with deterministic edges
    plus a conditional fan-out edge from ``normalize_references`` that dispatches
    one ``Send`` per reference to ``verify_single_reference``.

    Returns:
        A compiled LangGraph executable (``CompiledGraph``).
    """
    graph = StateGraph(GraphState)  # type: ignore[type-var]

    # --- Node registration ---
    graph.add_node("extract_text", extract_text)
    graph.add_node("parse_references", parse_references)
    graph.add_node("normalize_references", normalize_references)
    graph.add_node("verify_single_reference", verify_single_reference)
    graph.add_node("classify_results", classify_results)
    graph.add_node("assemble_report", assemble_report)

    # --- Linear edges ---
    graph.add_edge(START, "extract_text")
    graph.add_edge("extract_text", "parse_references")
    graph.add_edge("parse_references", "normalize_references")

    # --- Fan-out: one Send per reference ---
    graph.add_conditional_edges("normalize_references", fan_out_verify)

    # --- Fan-in: all verify invocations converge at classify ---
    graph.add_edge("verify_single_reference", "classify_results")

    # --- Linear edges (post fan-in) ---
    graph.add_edge("classify_results", "assemble_report")
    graph.add_edge("assemble_report", END)

    return graph.compile()
