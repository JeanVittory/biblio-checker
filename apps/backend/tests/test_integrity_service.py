import hashlib
from unittest.mock import patch

import pytest

from app.services.integrity import (
    IntegrityShaMismatchError,
    verify_sha256_bytes,
    verify_supabase_object_sha256,
)

CONTENT = b"dummy-content"
CONTENT_SHA256 = hashlib.sha256(CONTENT).hexdigest()

def test_verify_sha256_bytes_ok_case_insensitive():
    verify_sha256_bytes(content=CONTENT, sha256=CONTENT_SHA256.upper())


def test_verify_sha256_bytes_raises_on_mismatch():
    with pytest.raises(IntegrityShaMismatchError) as exc:
        verify_sha256_bytes(content=CONTENT, sha256=("a" * 64))

    assert exc.value.computed_sha256 == CONTENT_SHA256
    assert exc.value.provided_sha256 == ("a" * 64)


def test_verify_supabase_object_sha256_downloads_and_verifies():
    with patch(
        "app.services.integrity.compute_object_sha256",
        return_value=CONTENT_SHA256,
    ):
        verify_supabase_object_sha256(
            bucket="uploads",
            path="uploads/req/file.pdf",
            sha256=CONTENT_SHA256.upper(),
        )
