"""Tests for lease renewal — repo.renew_lease() and langgraph/lease.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from biblio_checker_worker.jobs import repo
from biblio_checker_worker.langgraph.lease import (
    clear_lease_context,
    init_lease_context,
    renew_lease_if_needed,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supabase(*, rpc_data: object) -> MagicMock:
    """Return a Supabase mock whose .rpc().execute().data == rpc_data."""
    supabase = MagicMock()
    supabase.rpc.return_value.execute.return_value.data = rpc_data
    return supabase


# ---------------------------------------------------------------------------
# repo.renew_lease — successful renewal
# ---------------------------------------------------------------------------


def test_renew_lease_returns_true_on_success() -> None:
    supabase = _make_supabase(rpc_data=True)

    result = repo.renew_lease(
        supabase,
        job_id="job-abc",
        token="tok-123",
        lease_seconds=300,
    )

    assert result is True
    supabase.rpc.assert_called_once_with(
        "renew_analysis_job_lease",
        {"p_job_id": "job-abc", "p_token": "tok-123", "p_lease_secs": 300},
    )


# ---------------------------------------------------------------------------
# repo.renew_lease — token mismatch / job not running
# ---------------------------------------------------------------------------


def test_renew_lease_returns_false_on_token_mismatch() -> None:
    """RPC returns False when the token does not match (job reclaimed)."""
    supabase = _make_supabase(rpc_data=False)

    result = repo.renew_lease(
        supabase,
        job_id="job-abc",
        token="wrong-token",
        lease_seconds=300,
    )

    assert result is False


# ---------------------------------------------------------------------------
# repo.renew_lease — RPC raises (network error, Supabase unavailable)
# ---------------------------------------------------------------------------


def test_renew_lease_returns_false_and_does_not_raise_on_rpc_error() -> None:
    """Exceptions from the RPC are swallowed; False is returned instead."""
    supabase = MagicMock()
    supabase.rpc.return_value.execute.side_effect = RuntimeError("connection refused")

    # Must not propagate the exception.
    result = repo.renew_lease(
        supabase,
        job_id="job-xyz",
        token="tok-456",
        lease_seconds=300,
    )

    assert result is False


# ---------------------------------------------------------------------------
# repo.renew_lease — job_id stays str (no uuid.UUID conversion)
# ---------------------------------------------------------------------------


def test_renew_lease_passes_job_id_as_str() -> None:
    supabase = _make_supabase(rpc_data=True)

    repo.renew_lease(
        supabase,
        job_id="550e8400-e29b-41d4-a716-446655440000",
        token="tok",
        lease_seconds=60,
    )

    call_kwargs = supabase.rpc.call_args[0][1]
    assert isinstance(call_kwargs["p_job_id"], str)


# ---------------------------------------------------------------------------
# renew_lease_if_needed — uninitialized context returns False
# ---------------------------------------------------------------------------


def test_renew_lease_if_needed_without_init_returns_false() -> None:
    """Safe to call before init_lease_context — must not raise."""
    # Ensure no leftover state from other tests.
    clear_lease_context()

    result = renew_lease_if_needed()

    assert result is False


# ---------------------------------------------------------------------------
# init_lease_context / renew_lease_if_needed / clear_lease_context lifecycle
# ---------------------------------------------------------------------------


def test_init_and_renew_lifecycle() -> None:
    supabase = _make_supabase(rpc_data=True)

    init_lease_context(
        supabase=supabase,
        job_id="job-lifecycle",
        token="tok-lifecycle",
        lease_seconds=300,
    )
    try:
        result = renew_lease_if_needed()
    finally:
        clear_lease_context()

    assert result is True
    supabase.rpc.assert_called_once_with(
        "renew_analysis_job_lease",
        {
            "p_job_id": "job-lifecycle",
            "p_token": "tok-lifecycle",
            "p_lease_secs": 300,
        },
    )


def test_clear_lease_context_makes_subsequent_call_return_false() -> None:
    supabase = _make_supabase(rpc_data=True)

    init_lease_context(
        supabase=supabase,
        job_id="job-clear",
        token="tok-clear",
        lease_seconds=300,
    )
    clear_lease_context()

    result = renew_lease_if_needed()

    assert result is False
    supabase.rpc.assert_not_called()


# ---------------------------------------------------------------------------
# renew_lease_if_needed — propagates RPC failure as False (no raise)
# ---------------------------------------------------------------------------


def test_renew_lease_if_needed_rpc_failure_returns_false() -> None:
    supabase = MagicMock()
    supabase.rpc.return_value.execute.side_effect = RuntimeError("timeout")

    init_lease_context(
        supabase=supabase,
        job_id="job-fail",
        token="tok-fail",
        lease_seconds=300,
    )
    try:
        result = renew_lease_if_needed()
    finally:
        clear_lease_context()

    assert result is False
