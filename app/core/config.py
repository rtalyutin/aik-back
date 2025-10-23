"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseModel):
    """Feature flag toggles used to orchestrate external providers."""

    enable_lalal_alternative: bool = False
    enable_align_alternative: bool = False
    use_dummy_s3: bool = False


class Settings(BaseSettings):
    """Base application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "AI Karaoke Backend"
    environment: str = "development"

    database_url: str = "sqlite+aiosqlite:///./aik.db"

    s3_endpoint_url: AnyHttpUrl | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "aik-jobs"
    s3_region_name: str | None = None
    s3_upload_expire_seconds: int = 3600

    lalal_api_key: str | None = None
    lalal_base_url: AnyHttpUrl | None = None

    lalal_alternative_base_url: AnyHttpUrl | None = None

    asr_provider: str = "default"
    asr_callback_secret: str | None = None

    align_provider: str = "default"

    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)

    log_level: str = "INFO"

    def provider_options(self) -> dict[str, Any]:
        """Return a mapping with provider-specific options for wiring services."""
        return {
            "lalal": {
                "base_url": self.lalal_base_url,
                "api_key": self.lalal_api_key,
                "alternative_base_url": self.lalal_alternative_base_url,
            },
            "asr": {
                "provider": self.asr_provider,
                "callback_secret": self.asr_callback_secret,
            },
            "align": {
                "provider": self.align_provider,
            },
        }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
