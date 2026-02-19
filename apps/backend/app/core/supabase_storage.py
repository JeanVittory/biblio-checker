from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final
from urllib.parse import quote

import httpx

from app.core.config import settings

_DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
_CHUNK_SIZE: Final[int] = 64 * 1024


@dataclass(frozen=True)
class SupabaseStorageError(Exception):
    code: str
    detail: str | None = None


def _object_url(bucket: str, path: str) -> str:
    base = (settings.supabase_url or "").rstrip("/")
    return (
        f"{base}/storage/v1/object/"
        f"{quote(bucket, safe='')}/{quote(path, safe='/')}"
    )


def _headers() -> dict[str, str]:
    key = settings.supabase_service_role_key or ""
    return {
        "authorization": f"Bearer {key}",
        "apikey": key,
    }


def compute_object_sha256(bucket: str, path: str) -> str:
    if not (settings.supabase_url or "").strip() or not (
        settings.supabase_service_role_key or ""
    ).strip():
        raise SupabaseStorageError(code="server_misconfigured")

    url = _object_url(bucket, path)
    headers = _headers()

    try:
        with httpx.Client(
            timeout=_DEFAULT_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            with client.stream("GET", url, headers=headers) as resp:
                if resp.status_code == 404:
                    raise SupabaseStorageError(code="storage_not_found")
                if resp.status_code in (401, 403):
                    raise SupabaseStorageError(code="storage_unauthorized")
                if resp.status_code >= 400:
                    status_code = resp.status_code
                    raise SupabaseStorageError(
                        code="storage_download_failed",
                        detail=f"Storage request failed with status {status_code}.",
                    )

                max_bytes = int(settings.max_file_size_bytes)
                content_length = resp.headers.get("content-length")
                if content_length is not None:
                    try:
                        if int(content_length) > max_bytes:
                            raise SupabaseStorageError(code="file_too_large")
                    except ValueError:
                        pass

                digest = hashlib.sha256()
                size = 0
                for chunk in resp.iter_bytes(chunk_size=_CHUNK_SIZE):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > max_bytes:
                        raise SupabaseStorageError(code="file_too_large")
                    digest.update(chunk)

                return digest.hexdigest()
    except httpx.HTTPError as exc:
        raise SupabaseStorageError(
            code="storage_download_failed", detail=str(exc) or None
        ) from exc
