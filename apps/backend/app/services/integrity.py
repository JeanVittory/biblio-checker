from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.services.supabase_storage import compute_object_sha256


@dataclass(frozen=True)
class IntegrityShaMismatchError(Exception):
    computed_sha256: str
    provided_sha256: str


def compute_sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def verify_sha256_bytes(*, content: bytes, sha256: str) -> None:
    computed_sha256 = compute_sha256_bytes(content).lower()
    provided_sha256 = sha256.lower()

    if computed_sha256 != provided_sha256:
        raise IntegrityShaMismatchError(
            computed_sha256=computed_sha256,
            provided_sha256=provided_sha256,
        )


def verify_supabase_object_sha256(*, bucket: str, path: str, sha256: str) -> None:
    computed_sha256 = compute_object_sha256(bucket, path).lower()
    provided_sha256 = sha256.lower()

    if computed_sha256 != provided_sha256:
        raise IntegrityShaMismatchError(
            computed_sha256=computed_sha256,
            provided_sha256=provided_sha256,
        )
