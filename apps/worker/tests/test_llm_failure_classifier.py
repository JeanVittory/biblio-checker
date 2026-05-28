"""Unit tests for :mod:`biblio_checker_worker.jobs.llm_failure_classifier`.

Verifies that LLM provider rate-limit / quota exhaustion is detected
reliably and that unrelated exceptions do NOT trigger a false positive.
"""

from __future__ import annotations

import anthropic
import groq
import httpx
import openai
import pytest

from biblio_checker_worker.jobs.llm_failure_classifier import (
    is_trial_limit_exception,
)


def _fake_response(status_code: int = 429) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", "https://api.example/v1/chat"),
    )


def _openai_rate_limit() -> openai.RateLimitError:
    return openai.RateLimitError(
        "You exceeded your current quota, please check your plan and billing details.",
        response=_fake_response(429),
        body=None,
    )


def _anthropic_rate_limit() -> anthropic.RateLimitError:
    return anthropic.RateLimitError(
        "rate_limit_exceeded",
        response=_fake_response(429),
        body=None,
    )


def _groq_rate_limit() -> groq.RateLimitError:
    return groq.RateLimitError(
        "Rate limit reached for model",
        response=_fake_response(429),
        body=None,
    )


class _Wrapper(Exception):
    """Mimics a wrapper exception (e.g. langchain) that exposes status_code."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class _NestedResponse(Exception):
    """Exception that exposes the upstream response via .response."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.response = _fake_response(status_code)


@pytest.mark.parametrize(
    ("exc_factory", "expected"),
    [
        # --- True: real provider rate limits ---------------------------------
        (_openai_rate_limit, True),
        (_anthropic_rate_limit, True),
        (_groq_rate_limit, True),
        # --- True: wrappers exposing status_code or .response ----------------
        (lambda: _Wrapper("Something bad happened", 429), True),
        (lambda: _NestedResponse("Upstream failed", 429), True),
        # --- True: text allow-list as last resort ----------------------------
        (lambda: Exception("Request failed: insufficient_quota"), True),
        (lambda: Exception("rate_limit_exceeded for model X"), True),
        (lambda: RuntimeError("You exceeded your current quota."), True),
        # --- False: unrelated HTTP errors (no 429) ---------------------------
        (lambda: _Wrapper("Server error", 500), False),
        (lambda: _NestedResponse("Server error", 503), False),
        # --- False: random non-LLM exceptions --------------------------------
        (lambda: ValueError("bad data"), False),
        (lambda: KeyError("missing"), False),
        (lambda: Exception("Random unrelated failure"), False),
        # --- False: ambiguous strings that should NOT match ------------------
        (lambda: Exception("connection refused"), False),
        (lambda: Exception("timeout reading from socket"), False),
    ],
)
def test_is_trial_limit_exception(exc_factory, expected: bool) -> None:
    exc = exc_factory()
    assert is_trial_limit_exception(exc) is expected
