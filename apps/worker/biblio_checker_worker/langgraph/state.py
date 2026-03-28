from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict):
    """Typed state shared across all LangGraph pipeline nodes.

    Fields are grouped by the node that writes them. Fields annotated with
    ``operator.add`` accumulate results from parallel fan-out invocations —
    LangGraph concatenates updates rather than overwriting. Plain-typed fields
    are written once (or overwritten) by a single node.
    """

    # --- Inputs (set once at graph invocation) ---
    job_id: str
    """UUID of the analysis job."""
    source_type: str
    """Document type: ``"pdf"`` or ``"docx"``."""
    file_bytes: bytes
    """Raw document bytes downloaded from Supabase Storage."""

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
