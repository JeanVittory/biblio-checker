from __future__ import annotations

import operator
from typing import Annotated, NotRequired, TypedDict


class GraphState(TypedDict):
    """Typed state shared across all LangGraph pipeline nodes.

    Fields are grouped by the node that writes them. Fields annotated with
    ``operator.add`` accumulate results from parallel fan-out invocations —
    LangGraph concatenates updates rather than overwriting. Plain-typed fields
    are written once (or overwritten) by a single node.

    Step 04: ``file_bytes`` and ``source_type`` are now ``NotRequired`` so that
    text-mode jobs (which enter the graph at ``normalize_references``, bypassing
    ``extract_text`` and ``parse_references``) do not need to supply these fields
    in their initial state.  All downstream nodes that use these fields
    (``extract_text``, ``parse_references``) already run before
    ``normalize_references`` in file-mode, so they are still populated correctly
    for file-mode jobs.
    """

    # --- Inputs (set once at graph invocation) ---
    job_id: str
    """UUID of the analysis job."""
    source_type: NotRequired[str]
    """Document type: ``"pdf"`` or ``"docx"``. Not required for text-mode jobs."""
    file_bytes: NotRequired[bytes]
    """Raw document bytes downloaded from Supabase Storage.
    Not required for text-mode jobs that enter at ``normalize_references``.
    """
    locale: str
    """User-selected locale for decisionReason/warnings rendering.
    One of ``"es" | "pt" | "en"``. Set at graph invocation; never mutated.
    Kept as plain ``str`` (not ``Literal``) because TypedDict with Literal
    aliases interact poorly with runtime dict construction in some LangGraph
    call sites. ``render()`` normalises invalid values to ``"es"`` at read time.
    """

    # --- After extract_text node ---
    raw_text: str
    """Plain text extracted from the document."""

    # --- After parse_references node ---
    raw_references: list[dict]
    """Raw reference strings with index, e.g. ``[{rawText: str, index: int}]``."""
    total_references_detected: int
    """Count of references found in the document by the LLM parser."""

    # --- After normalize_references node ---
    normalized_references: Annotated[list[dict], operator.add]
    """Structured reference metadata. Uses ``operator.add`` so parallel
    normalize shards accumulate correctly.
    Each dict: ``{referenceId, rawText, normalized: {title, authors, year, venue, doi, arxivId}}``
    """

    # --- After verify_single_reference (fan-out/fan-in) ---
    verified_references: Annotated[list[dict], operator.add]
    """References with evidence from API lookups (pre-classification).
    Uses ``operator.add`` so N parallel ``Send()`` invocations accumulate their
    individual results into a single list.
    Each dict: full ReferenceResult-like structure with evidence, candidates,
    source_errors.
    """

    # --- After classify_results node ---
    classified_references: list[dict]
    """Plain list with NO reducer. Written once by ``classify_results`` after
    fan-in completes. Using a plain field (not ``operator.add``) prevents
    double-accumulation since ``classify_results`` runs once, not in parallel.
    Each dict: verified_reference enriched with classification fields.
    """

    # --- After analyze_cross_patterns node ---
    cross_reference_analysis: dict
    """Cross-reference pattern analysis results. Written once by
    ``analyze_cross_patterns`` (Phase C implementation). Plain field with NO
    reducer — written by a single node, not accumulated from parallel calls.

    Access via ``state.get("cross_reference_analysis", {})`` — never via direct
    key access — because the field may be absent when cross-pattern analysis is
    disabled.
    """

    # --- Accumulated across all nodes ---
    warnings: Annotated[list[dict], operator.add]
    """Warnings accumulated during pipeline processing.
    Each dict: ``{code: str, message: str, referenceId: str | None, details: dict | None}``
    """

    # --- After assemble_report node ---
    results_v1: dict
    """The final ResultsV1 payload, Pydantic-validated and serialised via
    ``model_dump()``.
    """
