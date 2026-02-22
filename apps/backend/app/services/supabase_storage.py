from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final

import httpx
from anyio.to_thread import run_sync
from storage3.exceptions import StorageApiError

from app.core.config import settings
from app.core.supabase_client import SupabaseClientError, get_supabase_admin_client

_DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
_CHUNK_SIZE: Final[int] = 64 * 1024


@dataclass(frozen=True)
class SupabaseStorageError(Exception):
    code: str
    detail: str | None = None


async def _create_signed_download_url(*, bucket: str, path: str) -> str:
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise SupabaseStorageError(code=exc.code, detail=exc.detail) from exc

    def _signed_url_sync() -> str:
        resp = supabase.storage.from_(bucket).create_signed_url(
            path, int(settings.supabase_signed_url_ttl_seconds)
        )
        signed = None
        if isinstance(resp, dict):
            signed = resp.get("signedURL") or resp.get("signedUrl")
        if not signed:
            raise SupabaseStorageError(
                code="storage_download_failed",
                detail="Could not generate a signed download URL.",
            )
        return str(signed)

    try:
        return await run_sync(_signed_url_sync)
    except SupabaseStorageError:
        raise
    except StorageApiError as exc:
        status = str(exc.status)
        if status == "404":
            raise SupabaseStorageError(
                code="storage_not_found", detail=exc.message
            ) from exc
        if status in ("401", "403"):
            raise SupabaseStorageError(
                code="storage_unauthorized", detail=exc.message
            ) from exc
        raise SupabaseStorageError(
            code="storage_download_failed",
            detail=f"Signed URL generation failed with status {exc.status}.",
        ) from exc
    except httpx.HTTPError as exc:
        raise SupabaseStorageError(
            code="storage_download_failed", detail=str(exc) or None
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise SupabaseStorageError(
            code="storage_download_failed", detail=str(exc) or None
        ) from exc


async def download_object_bytes(bucket: str, path: str) -> bytes:
    url = await _create_signed_download_url(bucket=bucket, path=path)

    try:
        async with httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            async with client.stream("GET", url) as resp:
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

                data = bytearray()
                size = 0
                async for chunk in resp.aiter_bytes(chunk_size=_CHUNK_SIZE):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > max_bytes:
                        raise SupabaseStorageError(code="file_too_large")
                    data.extend(chunk)

                return bytes(data)
    except httpx.HTTPError as exc:
        raise SupabaseStorageError(
            code="storage_download_failed", detail=str(exc) or None
        ) from exc


def compute_object_sha256(bucket: str, path: str) -> str:
    try:
        supabase = get_supabase_admin_client()
    except SupabaseClientError as exc:
        raise SupabaseStorageError(code=exc.code, detail=exc.detail) from exc

    try:
        resp = supabase.storage.from_(bucket).create_signed_url(
            path, int(settings.supabase_signed_url_ttl_seconds)
        )
        url = None
        if isinstance(resp, dict):
            url = resp.get("signedURL") or resp.get("signedUrl")
        if not url:
            raise SupabaseStorageError(
                code="storage_download_failed",
                detail="Could not generate a signed download URL.",
            )
    except StorageApiError as exc:
        status = str(exc.status)
        if status == "404":
            raise SupabaseStorageError(
                code="storage_not_found", detail=exc.message
            ) from exc
        if status in ("401", "403"):
            raise SupabaseStorageError(
                code="storage_unauthorized", detail=exc.message
            ) from exc
        raise SupabaseStorageError(
            code="storage_download_failed",
            detail=f"Signed URL generation failed with status {exc.status}.",
        ) from exc
    except httpx.HTTPError as exc:
        raise SupabaseStorageError(
            code="storage_download_failed", detail=str(exc) or None
        ) from exc

    try:
        with httpx.Client(
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            with client.stream("GET", str(url)) as resp:
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
