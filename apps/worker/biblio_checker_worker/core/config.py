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
    # Valid values: "anthropic", "openai", "groq"
    # Determines which LangChain chat model class is instantiated.

    anthropic_api_key: SecretStr = SecretStr("")
    # Required when llm_provider="anthropic". The Anthropic API key.
    # Use .get_secret_value() when passing to LLM client constructors.

    openai_api_key: SecretStr = SecretStr("")
    # Required when llm_provider="openai". The OpenAI API key.
    # Use .get_secret_value() when passing to LLM client constructors.

    groq_api_key: SecretStr = SecretStr("")
    # Required when llm_provider="groq". The Groq API key.
    # Use .get_secret_value() when passing to LLM client constructors.

    llm_model: str = "claude-sonnet-4-20250514"
    # The model identifier passed to the LLM provider.
    # Default is Claude Sonnet; change to e.g. "gpt-4o" (OpenAI) or
    # "llama-3.3-70b-versatile" (Groq) when using another provider.

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

    # --- AI-Enhanced Classification ---
    ai_adjudication_enabled: bool = True
    # Master toggle for AI adjudication. When False, the ai_adjudicate node
    # passes through without making any LLM calls.
    # Cost impact: adds 1 LLM call per job (batched, only for uncertain references).

    ai_adjudication_max_references: int = Field(default=20, ge=1, le=150)
    # Maximum number of uncertain references to adjudicate per job.
    # References are prioritized by lowest confidence score (most uncertain first).
    # Must be between 1 and 150 (the max_references pipeline cap).

    cross_pattern_analysis_enabled: bool = True
    # Toggle for cross-reference pattern detection and LLM analysis.
    # When False, the analyze_cross_patterns node passes through entirely.
    # Deterministic checks also require this to be True.

    cross_pattern_llm_enabled: bool = True
    # Toggle for the LLM call within cross-pattern analysis.
    # When False, deterministic checks still run and produce flags, but no LLM
    # call is made. Only meaningful when cross_pattern_analysis_enabled is True.
    # Cost impact: adds 1 LLM call per job (only when patterns are detected).

    # --- Pipeline Metadata ---
    pipeline_name: str = "biblio-checker"
    pipeline_version: str = "0.1.0"
    # Included in the ResultsV1 `pipeline` field.

    @model_validator(mode="after")
    def validate_llm_provider_key(self) -> "Settings":
        if self.llm_provider not in ("anthropic", "openai", "groq"):
            raise ValueError(
                f"llm_provider must be 'anthropic', 'openai', or 'groq', got '{self.llm_provider}'"
            )
        # API key presence is only enforced outside of development to allow local
        # development and testing without provider credentials configured.
        if self.environment != "development":
            if (
                self.llm_provider == "anthropic"
                and not self.anthropic_api_key.get_secret_value()
            ):
                raise ValueError(
                    "anthropic_api_key must be non-empty when llm_provider='anthropic'"
                )
            if (
                self.llm_provider == "openai"
                and not self.openai_api_key.get_secret_value()
            ):
                raise ValueError(
                    "openai_api_key must be non-empty when llm_provider='openai'"
                )
            if self.llm_provider == "groq" and not self.groq_api_key.get_secret_value():
                raise ValueError(
                    "groq_api_key must be non-empty when llm_provider='groq'"
                )
        return self


settings = Settings()


def get_settings() -> Settings:
    return settings
