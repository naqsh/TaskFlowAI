"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_version: str = "0.1.0"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow"
    supabase_url: str = ""
    supabase_anon_key: str = ""

    jwt_secret_key: str = Field(
        default="dev-only-jwt-secret-change-in-production-0123456789abcdef",
        min_length=32,
    )
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    auth_login_rate_limit: int = 10
    auth_login_rate_window_seconds: int = 60

    redis_url: str = "redis://localhost:6379/0"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    cors_origins: str = "http://localhost:3000"

    # Security Layer 1 (TF-E4)
    llamafirewall_enabled: bool = True
    llamafirewall_block_threshold: float = 0.9
    hf_token: str = ""
    security_monitor_enabled: bool = True
    mcp_default_size_threshold: int = 50_000
    mcp_anomaly_sigma: float = 2.0
    dlq_max_retries: int = 3

    # Identity & credentials (TF-E5)
    vault_mode: Literal["memory", "env"] = "memory"
    delegation_grace_seconds: int = 30
    consent_ttl_days: int = 30
    local_llm_enabled: bool = False
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3.1"
    local_llm_max_context_tokens: int = 4096

    # Production hardening (TF-E6)
    cache_warming_enabled: bool = False
    cache_ttl: int = 300
    ai_features_enabled: bool = True
    feature_vector_search: bool = False
    agent_manifest_path: str = "infrastructure/agent-manifest.json"
    ai_bom_path: str = "infrastructure/ai-bom.yaml"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        insecure_jwt_markers = ("dev-only", "change-in-production")
        if self.app_env == "production":
            if any(marker in self.jwt_secret_key for marker in insecure_jwt_markers):
                msg = "JWT_SECRET_KEY must be set to a secure value in production"
                raise ValueError(msg)
            if self.app_debug:
                msg = "APP_DEBUG must be false in production"
                raise ValueError(msg)
            if not self.database_url or "localhost" in self.database_url:
                msg = "DATABASE_URL must be set to a production value in production"
                raise ValueError(msg)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
