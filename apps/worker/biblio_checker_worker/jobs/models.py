from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal


@dataclass(frozen=True)
class AnalysisJob:
    """Typed, immutable view of a row from the ``analysis_jobs`` table.

    Step 04 (single-reference text-check) extends this model with:
    - ``input_kind``: discriminator for file vs. text-mode jobs. Defaults to
      ``"file"`` so that pre-Step-02 RPC responses (which omit the column)
      continue to work without crashing deserialization.
    - ``raw_reference_text``: pasted reference text for text-mode jobs.
    - ``bucket``, ``path``, ``sha256``, ``source_type``: now optional; required
      only when ``input_kind == "file"``.
    """

    id: str
    status: str
    stage: str
    attempts: int
    max_attempts: int
    # --- input_kind discriminator (Step 04) ---
    # Default "file" provides defense-in-depth: if the RPC does not return this
    # column (e.g. older DB without the migration applied), the worker treats the
    # job as file-mode and will fail fast at extract_stage on the NULL bucket/path
    # rather than crashing here during deserialization.
    input_kind: Literal["file", "text"] = "file"
    # --- file-mode fields (optional post Step 04 migration) ---
    bucket: str | None = None
    path: str | None = None
    sha256: str | None = None
    source_type: str | None = None
    # --- text-mode fields ---
    raw_reference_text: str | None = None
    # --- shared optional fields ---
    locale: str = "es"
    job_token: str | None = None
    job_token_expires_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    # The set of field names accepted by from_row(); extra dict keys are ignored.
    _FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "id",
            "status",
            "stage",
            "bucket",
            "path",
            "sha256",
            "source_type",
            "attempts",
            "max_attempts",
            "input_kind",
            "raw_reference_text",
            "locale",
            "job_token",
            "job_token_expires_at",
            "created_at",
            "updated_at",
        }
    )

    @classmethod
    def from_row(cls, row: dict) -> AnalysisJob:
        """Construct an AnalysisJob from a raw Supabase response dict.

        Extra keys not present in the model are silently ignored.  Missing
        optional keys fall back to None.  Missing required keys raise KeyError
        so that the calling repository layer can surface the error.

        ``input_kind`` defaults to ``"file"`` when absent from the row (defense-
        in-depth for pre-Step-02 database rows).
        """
        filtered = {k: v for k, v in row.items() if k in cls._FIELDS}
        return cls(
            id=filtered["id"],
            status=filtered["status"],
            stage=filtered["stage"],
            attempts=filtered["attempts"],
            max_attempts=filtered["max_attempts"],
            input_kind=filtered.get("input_kind") or "file",  # type: ignore[arg-type]
            bucket=filtered.get("bucket"),
            path=filtered.get("path"),
            sha256=filtered.get("sha256"),
            source_type=filtered.get("source_type"),
            raw_reference_text=filtered.get("raw_reference_text"),
            locale=filtered.get("locale")
            or "es",  # defensive default for pre-migration rows
            job_token=filtered.get("job_token"),
            job_token_expires_at=filtered.get("job_token_expires_at"),
            created_at=filtered.get("created_at"),
            updated_at=filtered.get("updated_at"),
        )

    def __repr__(self) -> str:
        # SECURITY: Redact job_token to prevent it appearing in logs.
        return (
            f"AnalysisJob(id={self.id!r}, status={self.status!r}, "
            f"stage={self.stage!r}, attempts={self.attempts}, "
            f"job_token=<redacted>)"
        )
