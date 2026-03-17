from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class AnalysisJob:
    """Typed, immutable view of a row from the ``analysis_jobs`` table."""

    id: str
    status: str
    stage: str
    bucket: str
    path: str
    sha256: str
    source_type: str
    attempts: int
    max_attempts: int
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
        optional keys (job_token, job_token_expires_at, created_at, updated_at)
        fall back to None.  Missing required keys raise KeyError so that the
        calling repository layer can surface the error.
        """
        filtered = {k: v for k, v in row.items() if k in cls._FIELDS}
        return cls(
            id=filtered["id"],
            status=filtered["status"],
            stage=filtered["stage"],
            bucket=filtered["bucket"],
            path=filtered["path"],
            sha256=filtered["sha256"],
            source_type=filtered["source_type"],
            attempts=filtered["attempts"],
            max_attempts=filtered["max_attempts"],
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
