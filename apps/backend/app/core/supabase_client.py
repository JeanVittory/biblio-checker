from __future__ import annotations

from dataclasses import dataclass

from supabase import Client, create_client

from app.core.config import settings


@dataclass(frozen=True)
class SupabaseClientError(Exception):
    code: str
    detail: str | None = None


def get_supabase_admin_client() -> Client:
    if not (settings.supabase_url or "").strip() or not (
        settings.supabase_service_role_key or ""
    ).strip():
        raise SupabaseClientError(code="server_misconfigured")

    return create_client(settings.supabase_url, settings.supabase_service_role_key)
