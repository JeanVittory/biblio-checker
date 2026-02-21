import copy
import hashlib
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.main import app

DUMMY_CONTENT = b"dummy"
DUMMY_SHA256 = hashlib.sha256(DUMMY_CONTENT).hexdigest()

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
        "sha256": DUMMY_SHA256,
    },
}

URL = "/api/analysis/start"


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


async def _post(payload: dict):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.post(URL, json=payload)


@pytest.mark.anyio
async def test_happy_path():
    with patch(
        "app.api.controllers.analysis.start.download_object_bytes",
        new=AsyncMock(return_value=DUMMY_CONTENT),
    ), patch(
        "app.api.controllers.analysis.start.extract_text_from_bytes_async",
        new=AsyncMock(return_value="dummy text"),
    ):
        resp = await _post(VALID_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


@pytest.mark.anyio
async def test_sha_mismatch_returns_problem_json():
    with patch(
        "app.api.controllers.analysis.start.download_object_bytes",
        new=AsyncMock(return_value=DUMMY_CONTENT),
    ):
        resp = await _post(_payload(**{"integrity.sha256": "a" * 64}))
    assert resp.status_code == 409
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "integrity_sha_mismatch"


@pytest.mark.anyio
async def test_storage_not_found_returns_problem_json():
    from app.core.supabase_storage import SupabaseStorageError

    with patch(
        "app.api.controllers.analysis.start.download_object_bytes",
        new=AsyncMock(side_effect=SupabaseStorageError(code="storage_not_found")),
    ):
        resp = await _post(VALID_PAYLOAD)
    assert resp.status_code == 404
    assert "application/problem+json" in resp.headers.get("content-type", "")
    body = resp.json()
    assert body["code"] == "storage_not_found"


@pytest.mark.anyio
async def test_source_type_mime_type_mismatch():
    payload = _payload(
        **{
            "document.sourceType": "docx",
            "document.mimeType": "application/pdf",
            "document.fileName": "file.docx",
            "storage.path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/file.docx",
        }
    )
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_path_traversal_rejected():
    payload = _payload(**{"storage.path": "uploads/../etc/passwd"})
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_absolute_path_rejected():
    payload = _payload(
        **{
            "storage.path": (
                "/uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/"
                "dummy.pdf"
            )
        }
    )
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_backslash_in_path_rejected():
    payload = _payload(
        **{
            "storage.path": "uploads\\4806aa68-ed88-4205-ae86-cc085eb463fd\\file.pdf"
        }
    )
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_null_byte_in_path_rejected():
    payload = _payload(**{"storage.path": "uploads/\x00evil"})
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_request_id_not_in_path():
    payload = _payload(
        **{
            "storage.path": (
                "uploads/00000000-0000-0000-0000-000000000000/"
                "dummy.pdf"
            )
        }
    )
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_filename_mismatch_with_path():
    payload = _payload(**{"document.fileName": "other-file.pdf"})
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_disallowed_bucket():
    payload = _payload(**{"storage.bucket": "private-data"})
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_extension_source_type_mismatch():
    payload = _payload(
        **{
            "document.fileName": "file.docx",
            "storage.path": "uploads/4806aa68-ed88-4205-ae86-cc085eb463fd/file.docx",
        }
    )
    resp = await _post(payload)
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_missing_integrity():
    payload = copy.deepcopy(VALID_PAYLOAD)
    del payload["integrity"]
    resp = await _post(payload)
    assert resp.status_code == 422
