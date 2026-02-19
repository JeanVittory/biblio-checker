from __future__ import annotations

from dataclasses import dataclass

from app.core.supabase_storage import compute_object_sha256


@dataclass(frozen=True)
class IntegrityShaMismatchError(Exception):
    computed_sha256: str
    provided_sha256: str


def verify_supabase_object_sha256(*, bucket: str, path: str, sha256: str) -> None:
    computed_sha256 = compute_object_sha256(bucket, path).lower()
    provided_sha256 = sha256.lower()

    if computed_sha256 != provided_sha256:
        raise IntegrityShaMismatchError(
            computed_sha256=computed_sha256,
            provided_sha256=provided_sha256,
        )
