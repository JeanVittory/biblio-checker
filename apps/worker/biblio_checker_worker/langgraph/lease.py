"""Lease renewal utility for LangGraph nodes.

Provides a ContextVar-based context so that any graph node can call
``renew_lease_if_needed()`` without threading Supabase client or lease
credentials through GraphState (which would add non-serializable objects
to state and break LangGraph's Send() fan-out serialisation).

Typical lifecycle (managed by flow.py / run_langgraph.py):

    init_lease_context(supabase=..., job_id=..., token=..., lease_seconds=...)
    try:
        graph.invoke(state)
    finally:
        clear_lease_context()
"""

from __future__ import annotations

import contextvars

import structlog
from supabase import Client

from biblio_checker_worker.jobs import repo

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.lease")

# ContextVar is safe across async tasks and thread-pool executors used by
# LangGraph's Send() fan-out.  Never use a plain module-level variable here.
_lease_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "lease_ctx", default=None
)


def init_lease_context(
    *,
    supabase: Client,
    job_id: str,
    token: str,
    lease_seconds: int,
) -> None:
    """Initialize lease renewal context.

    Must be called once before graph invocation.  The context is stored in a
    ContextVar so it is isolated to the current execution context.
    """
    _lease_ctx.set(
        {
            "supabase": supabase,
            "job_id": job_id,
            "token": token,
            "lease_seconds": lease_seconds,
        }
    )


def renew_lease_if_needed() -> bool:
    """Renew the lease if context is initialized.

    Returns True if the lease was successfully renewed, False otherwise.
    Safe to call even when the context has not been initialized (returns False
    without raising).
    """
    ctx = _lease_ctx.get(None)
    if ctx is None:
        logger.debug("lease_context_not_initialized")
        return False
    return repo.renew_lease(
        ctx["supabase"],
        job_id=ctx["job_id"],
        token=ctx["token"],
        lease_seconds=ctx["lease_seconds"],
    )


def clear_lease_context() -> None:
    """Clear the lease context after graph execution."""
    _lease_ctx.set(None)
