import copy
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "requestId": "4806aa68-ed88-4205-ae86-cc085eb463fd",
    "extractMode": "backend_extract_references",
    "document": {
        "sourceType": "pdf",
        "fileName": "dummy.pdf",
        "mimeType": "application/pdf",
    },
    "storage": {
        "provider": "supabase",
        "bucket": "uploads",
        "path": (
            "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/"
            "dummy.pdf"
        ),
    },
    "integrity": {
        "sha256": "a" * 64,
    },
}

URL = "/api/references/verify-authenticity"


def _payload(**overrides):
    """Return a deep copy of VALID_PAYLOAD with nested overrides applied."""
    data = copy.deepcopy(VALID_PAYLOAD)
    for dotted_key, value in overrides.items():
        keys = dotted_key.split(".")
        target = data
        for k in keys[:-1]:
            target = target[k]
        target[keys[-1]] = value
    return data


def test_happy_path():
    with patch(
        "app.services.integrity.compute_object_sha256",
        return_value="a" * 64,
    ):
        resp = client.post(URL, json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_sha_mismatch_returns_problem_json():
    with patch(
        "app.services.integrity.compute_object_sha256",
        return_value="b" * 64,
    ):
        resp = client.post(URL, json=VALID_PAYLOAD)
    assert resp.status_code == 409
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "integrity_sha_mismatch"


def test_storage_not_found_returns_problem_json():
    from app.core.supabase_storage import SupabaseStorageError

    with patch(
        "app.services.integrity.compute_object_sha256",
        side_effect=SupabaseStorageError(code="storage_not_found"),
    ):
        resp = client.post(URL, json=VALID_PAYLOAD)
    assert resp.status_code == 404
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "storage_not_found"


def test_source_type_mime_type_mismatch():
    payload = _payload(
        **{
            "document.sourceType": "docx",
            "document.mimeType": "application/pdf",
            "document.fileName": "file.docx",
            "storage.path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/file.docx",
        }
    )
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_path_traversal_rejected():
    payload = _payload(**{"storage.path": "uploads/../etc/passwd"})
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_absolute_path_rejected():
    payload = _payload(
        **{
            "storage.path": (
                "/uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/"
                "dummy.pdf"
            )
        }
    )
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_backslash_in_path_rejected():
    payload = _payload(
        **{
            "storage.path": "uploads\\4806aa68-ed88-4205-ae86-cc085eb463fd\\file.pdf"
        }
    )
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_null_byte_in_path_rejected():
    payload = _payload(**{"storage.path": "uploads/\x00evil"})
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_request_id_not_in_path():
    payload = _payload(
        **{
            "storage.path": (
                "uploads/00000000-0000-0000-0000-000000000000/"
                "dummy.pdf"
            )
        }
    )
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_filename_mismatch_with_path():
    payload = _payload(**{"document.fileName": "other-file.pdf"})
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_disallowed_bucket():
    payload = _payload(**{"storage.bucket": "private-data"})
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_extension_source_type_mismatch():
    payload = _payload(
        **{
            "document.fileName": "file.docx",
            "storage.path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/file.docx",
        }
    )
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_missing_integrity():
    payload = copy.deepcopy(VALID_PAYLOAD)
    del payload["integrity"]
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422
