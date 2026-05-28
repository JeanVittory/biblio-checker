"""Detect when an exception raised by the LangGraph flow is caused by an
LLM provider rate limit / quota issue.

Kept conservative on purpose: returns False unless we recognize the failure
signature, so genuine bugs are not silently re-labelled as a trial limit.

The classifier is intentionally generic — the resulting ``error_code`` shown
to the user does not mention the provider, the word "quota", or "rate limit".
"""

from __future__ import annotations

import anthropic
import groq
import openai

# Status codes that virtually always indicate an LLM quota / rate-limit
# situation across providers (HTTP 429) or a downstream upstream-down
# variant of it.
_RATE_LIMIT_STATUSES: frozenset[int] = frozenset({429})

# Tight allow-list. Each phrase appears in the body of real provider errors
# when the cause is a quota / billing issue. Kept narrow to avoid mis-tagging
# transient infra hiccups.
_TRIAL_LIMIT_HINTS: tuple[str, ...] = (
    "insufficient_quota",
    "exceeded your current quota",
    "rate_limit_exceeded",
    "quota",
)


def is_trial_limit_exception(exc: BaseException) -> bool:
    """Return True when ``exc`` looks like an LLM provider rate-limit /
    quota exhaustion.

    Order matters:
    1. Exact provider RateLimitError types (no string matching).
    2. Any exception exposing ``status_code == 429`` (langchain wrappers).
    3. Text allow-list as a last resort.
    """
    if isinstance(
        exc,
        (
            openai.RateLimitError,
            anthropic.RateLimitError,
            groq.RateLimitError,
        ),
    ):
        return True

    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in _RATE_LIMIT_STATUSES:
        return True

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None) if response else None
    if isinstance(response_status, int) and response_status in _RATE_LIMIT_STATUSES:
        return True

    text = str(exc).lower()
    return any(hint in text for hint in _TRIAL_LIMIT_HINTS)
