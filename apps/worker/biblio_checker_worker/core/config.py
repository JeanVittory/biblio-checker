from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
    )

    environment: str = "development"
    log_level: str = "INFO"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_table: str = "analysis_jobs"

    poll_interval_seconds: int = 5


settings = Settings()
