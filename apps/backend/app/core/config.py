import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Biblio Checker API"
    environment: str = "development"
    # Keep as a plain string so dotenv values like:
    #   ALLOWED_ORIGINS="http://localhost:3000"
    # don't get JSON-decoded by pydantic-settings (which would error for list[str]).
    allowed_origins: str = "http://localhost:3000"
    allowed_buckets: str = "uploads"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_extracted_text_chars: int = 1_000_000

    @property
    def allowed_buckets_set(self) -> set[str]:
        return {b.strip() for b in self.allowed_buckets.split(",") if b.strip()}

    @property
    def allowed_origins_list(self) -> list[str]:
        value = (self.allowed_origins or "").strip()
        if not value:
            return []

        if value.startswith("["):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed if str(origin).strip()]

        return [origin.strip() for origin in value.split(",") if origin.strip()]


settings = Settings()
