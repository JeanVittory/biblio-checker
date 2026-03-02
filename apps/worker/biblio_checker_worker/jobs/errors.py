from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobRepoError(Exception):
    """Raised by repository functions when a DB operation fails."""

    code: str
    detail: str | None = None


@dataclass(frozen=True)
class StageError(Exception):
    """Raised by pipeline stages when a processing step fails.

    When ``transient`` is True the error is retryable and the job may be
    re-queued.  When False the job should fail permanently.
    """

    code: str
    detail: str | None = None
    transient: bool = True


@dataclass(frozen=True)
class TerminalJobError(Exception):
    """Raised when a job must fail permanently regardless of remaining attempts."""

    code: str
    detail: str | None = None
