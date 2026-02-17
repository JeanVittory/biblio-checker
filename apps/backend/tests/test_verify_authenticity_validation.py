import copy

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "requestId": "4806aa68-ed88-4205-ae86-cc085eb463fd",
    "extractMode": "backend_extract_references",
    "document": {
        "sourceType": "pdf",
        "fileName": "Certificado laboral Jean.pdf",
        "mimeType": "application/pdf",
    },
    "storage": {
        "provider": "supabase",
        "bucket": "uploads",
        "path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/Certificado laboral Jean.pdf",
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
    resp = client.post(URL, json=VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


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
            "storage.path": "/uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/Certificado laboral Jean.pdf"
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
            "storage.path": "uploads/00000000-0000-0000-0000-000000000000/Certificado laboral Jean.pdf"
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
