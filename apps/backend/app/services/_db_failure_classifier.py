from __future__ import annotations

import httpx
from postgrest.exceptions import APIError

_OFFLINE_HTTP_STATUSES: frozenset[int] = frozenset({502, 503, 504, 521, 522})

_OFFLINE_STR_HINTS: tuple[str, ...] = (
    "connection refused",
    "connection reset",
    "connection aborted",
    "name or service not known",
    "temporary failure in name resolution",
    "timed out",
    "timeout",
    "remotedisconnected",
    "all connection attempts failed",
)


def is_service_offline_exception(exc: BaseException) -> bool:
    """True only when ``exc`` is clearly a connectivity / upstream failure
    (Supabase paused or unreachable), False for data/logic errors.

    Order matters: type-based checks first (exact), then numeric status on
    APIError, and finally a tight string allow-list as a last resort.
    Conservative on purpose — callers fall back to existing, more specific
    error codes when this returns False.
    """
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.TimeoutException,
            httpx.NetworkError,
        ),
    ):
        return True

    if isinstance(exc, APIError):
        raw = str(getattr(exc, "code", "") or "").strip()
        try:
            if int(raw) in _OFFLINE_HTTP_STATUSES:
                return True
        except ValueError:
            pass

    text = str(exc).lower()
    return any(hint in text for hint in _OFFLINE_STR_HINTS)
