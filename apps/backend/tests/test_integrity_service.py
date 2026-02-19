from unittest.mock import patch

import pytest

from app.services.integrity import (
    IntegrityShaMismatchError,
    verify_supabase_object_sha256,
)


def test_verify_supabase_object_sha256_ok_case_insensitive():
    with patch("app.services.integrity.compute_object_sha256", return_value="a" * 64):
        verify_supabase_object_sha256(
            bucket="uploads",
            path="uploads/req/file.pdf",
            sha256=("A" * 64),
        )


def test_verify_supabase_object_sha256_raises_on_mismatch():
    with patch("app.services.integrity.compute_object_sha256", return_value="b" * 64):
        with pytest.raises(IntegrityShaMismatchError) as exc:
            verify_supabase_object_sha256(
                bucket="uploads",
                path="uploads/req/file.pdf",
                sha256=("A" * 64),
            )

    assert exc.value.computed_sha256 == ("b" * 64)
    assert exc.value.provided_sha256 == ("a" * 64)
