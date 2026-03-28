from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
    )

    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "console"

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_table: str = "analysis_jobs"

    poll_interval_seconds: int = 5

    job_lease_seconds: int = Field(default=300, ge=1, le=3600)
    job_token_bytes: int = 32

    # --- LLM Provider ---
    llm_provider: str = "anthropic"
    # Valid values: "anthropic", "openai"
    # Determines which LangChain chat model class is instantiated.

    anthropic_api_key: SecretStr = SecretStr("")
    # Required when llm_provider="anthropic". The Anthropic API key.
    # Use .get_secret_value() when passing to LLM client constructors.

    openai_api_key: SecretStr = SecretStr("")
    # Required when llm_provider="openai". The OpenAI API key.
    # Use .get_secret_value() when passing to LLM client constructors.

    llm_model: str = "claude-sonnet-4-20250514"
    # The model identifier passed to the LLM provider.
    # Default is Claude Sonnet; change to e.g. "gpt-4o" when using OpenAI.

    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    # Temperature for LLM calls. 0.0 for deterministic output.

    # --- External APIs ---
    openalex_email: str = ""
    # Optional. If set, included in OpenAlex requests for polite pool (higher rate limits).

    api_timeout_seconds: int = Field(default=30, ge=1, le=120)
    # Timeout for each individual HTTP request to external APIs.

    # --- Text Extraction ---
    max_text_chars: int = 500_000
    # Maximum characters extracted from a document. Documents exceeding this raise an error.

    max_references: int = 150
    # Maximum number of references to process per document.
    # Documents exceeding this limit will process only the first N references.

    # --- Pipeline Metadata ---
    pipeline_name: str = "biblio-checker"
    pipeline_version: str = "0.1.0"
    # Included in the ResultsV1 `pipeline` field.

    @model_validator(mode="after")
    def validate_llm_provider_key(self) -> "Settings":
        if self.llm_provider not in ("anthropic", "openai"):
            raise ValueError(
                f"llm_provider must be 'anthropic' or 'openai', got '{self.llm_provider}'"
            )
        # API key presence is only enforced outside of development to allow local
        # development and testing without provider credentials configured.
        if self.environment != "development":
            if self.llm_provider == "anthropic" and not self.anthropic_api_key.get_secret_value():
                raise ValueError(
                    "anthropic_api_key must be non-empty when llm_provider='anthropic'"
                )
            if self.llm_provider == "openai" and not self.openai_api_key.get_secret_value():
                raise ValueError(
                    "openai_api_key must be non-empty when llm_provider='openai'"
                )
        return self


settings = Settings()


def get_settings() -> Settings:
    return settings
