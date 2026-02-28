from __future__ import annotations

from datetime import UTC, datetime


def coerce_utc_datetime(value: object, *, field: str) -> datetime:
    """Coerce a Supabase timestamp value into a timezone-aware datetime.

    Accepts either:
    - a datetime (aware or naive)
    - an ISO-8601 string (including a trailing 'Z')

    Naive datetimes are assumed to be UTC, matching the controller's existing
    behavior (fail-closed for security-sensitive fields).
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        s = value.strip()
        if s.endswith(("Z", "z")):
            s = f"{s[:-1]}+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise ValueError(f"{field}: invalid datetime string") from exc
    else:
        raise ValueError(f"{field}: expected str or datetime")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    return dt


def coerce_optional_utc_datetime(value: object, *, field: str) -> datetime | None:
    if value is None:
        return None
    return coerce_utc_datetime(value, field=field)
