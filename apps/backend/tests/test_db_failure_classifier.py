"""Unit tests for :mod:`app.services._db_failure_classifier`.

These tests cover the contract documented in the spec:
- True for connectivity-class failures (httpx connect/timeout, APIError with
  upstream-down statuses, exception strings matching the allow-list).
- False for data/logic errors (validation, duplicate key, etc.) — preserves
  existing more-specific error codes.
"""

from __future__ import annotations

import httpx
import pytest
from postgrest.exceptions import APIError

from app.services._db_failure_classifier import is_service_offline_exception


def _api_error(*, code: str, message: str = "boom") -> APIError:
    return APIError(
        {"message": message, "code": code, "details": "", "hint": ""}
    )


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        # --- True: connectivity-class via httpx types ---------------------
        (httpx.ConnectError("Connection refused"), True),
        (httpx.ConnectTimeout("timeout"), True),
        (httpx.ReadTimeout("timeout"), True),
        (httpx.WriteTimeout("timeout"), True),
        (httpx.PoolTimeout("timeout"), True),
        # --- True: APIError with upstream-down HTTP status ----------------
        (_api_error(code="503"), True),
        (_api_error(code="504"), True),
        (_api_error(code="502"), True),
        (_api_error(code="521"), True),
        # --- True: bare Exception whose message matches allow-list --------
        (Exception("Connection refused while talking to db"), True),
        (Exception("Read operation timed out reading from socket"), True),
        (Exception("temporary failure in name resolution"), True),
        # --- False: data / logic / schema errors (must stay False) --------
        (_api_error(code="23505", message="duplicate key value"), False),
        (_api_error(code="23503", message="violates foreign key"), False),
        (_api_error(code="42P01", message="relation does not exist"), False),
        (_api_error(code="22P02", message="invalid input syntax for type uuid"), False),
        # --- False: random unrelated exceptions ---------------------------
        (ValueError("bad data"), False),
        (KeyError("missing"), False),
        (Exception("something else entirely"), False),
        # --- False: APIError without numeric code falls back to text -----
        (_api_error(code="PGRST116", message="multiple rows"), False),
    ],
)
def test_is_service_offline_exception(exc: BaseException, expected: bool) -> None:
    assert is_service_offline_exception(exc) is expected
