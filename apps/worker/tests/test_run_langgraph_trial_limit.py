"""Integration test for the ``trial_limit_reached`` mapping in
``run_langgraph_stage``.

Verifies that a provider RateLimitError raised inside the LangGraph flow is
re-mapped to ``StageError(code="trial_limit_reached", transient=False)`` so
that the runner will mark the job as failed (without retry) and the frontend
can show the generic trial-limit message.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import openai
import pytest

from biblio_checker_worker.jobs.errors import StageError
from biblio_checker_worker.jobs.models import AnalysisJob
from biblio_checker_worker.pipeline.context import JobContext
from biblio_checker_worker.pipeline.stages.run_langgraph import run_langgraph_stage


def _fake_response() -> httpx.Response:
    return httpx.Response(
        status_code=429,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat"),
    )


def _job_fixture(*, input_kind: str = "text") -> AnalysisJob:
    return AnalysisJob(
        id="job-fixture",
        status="running",
        stage="langgraph_running",
        attempts=1,
        max_attempts=3,
        input_kind=input_kind,
        raw_reference_text=(
            "Smith, J. (2024). A study on something. Nature, 12(3), 45."
            if input_kind == "text"
            else None
        ),
    )


def _ctx(job: AnalysisJob) -> JobContext:
    return JobContext(
        job=job,
        token="lease-token",
        raw_reference_text=job.raw_reference_text,
    )


def test_rate_limit_maps_to_trial_limit_reached() -> None:
    job = _job_fixture(input_kind="text")
    ctx = _ctx(job)

    rate_limit = openai.RateLimitError(
        "You exceeded your current quota, please check your plan and billing details.",
        response=_fake_response(),
        body=None,
    )

    with (
        patch(
            "biblio_checker_worker.pipeline.stages.run_langgraph.repo.update_stage"
        ),
        patch(
            "biblio_checker_worker.pipeline.stages.run_langgraph.start_text_analysis_flow",
            side_effect=rate_limit,
        ),
    ):
        with pytest.raises(StageError) as exc_info:
            run_langgraph_stage(supabase=object(), ctx=ctx)

    err = exc_info.value
    assert err.code == "trial_limit_reached"
    assert err.transient is False  # do not retry — quota will not free itself


def test_unrelated_exception_still_maps_to_langgraph_flow_failed() -> None:
    """No-regression: any non-rate-limit exception keeps the generic code."""
    job = _job_fixture(input_kind="text")
    ctx = _ctx(job)

    with (
        patch(
            "biblio_checker_worker.pipeline.stages.run_langgraph.repo.update_stage"
        ),
        patch(
            "biblio_checker_worker.pipeline.stages.run_langgraph.start_text_analysis_flow",
            side_effect=ValueError("malformed parsed reference"),
        ),
    ):
        with pytest.raises(StageError) as exc_info:
            run_langgraph_stage(supabase=object(), ctx=ctx)

    err = exc_info.value
    assert err.code == "langgraph_flow_failed"
    assert err.transient is True
