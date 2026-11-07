"""Explicit production configuration for the institutional runtime."""

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LWH_", extra="ignore", hide_input_in_errors=True)

    environment: str = "production"
    database_url: str
    data_key_hex: str = Field(repr=False)
    web_origin: str
    resend_api_key: str = Field(default="", repr=False)
    email_from: str = ""
    s3_endpoint: str = ""
    s3_access_key: str = Field(default="", repr=False)
    s3_secret_key: str = Field(default="", repr=False)
    s3_bucket: str = ""
    clamav_host: str = ""
    clamav_port: int = 3310
    jobs_secret: str = Field(default="", repr=False)
    authority_node_id: str
    openrouter_api_key: str = Field(default="", repr=False)
    openrouter_model: str = ""
    upstash_rest_url: str = ""
    upstash_rest_token: str = Field(default="", repr=False)
    session_minutes: int = Field(default=30, ge=5, le=60)
    reporting_enabled: bool = True

    @property
    def production(self) -> bool:
        return self.environment == "production"

    def validate_runtime(self) -> None:
        try:
            valid_key = len(bytes.fromhex(self.data_key_hex)) == 32
        except ValueError:
            valid_key = False
        if not valid_key:
            raise ValueError("LWH_DATA_KEY_HEX must be a separately provisioned 32-byte key")
        if self.openrouter_model and not self.openrouter_model.endswith(":free"):
            raise ValueError("Only explicitly free OpenRouter model variants are permitted")
        if self.production:
            if not self.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
                raise ValueError("Production requires PostgreSQL; no local or in-memory fallback")
            origin = urlparse(self.web_origin)
            if origin.scheme != "https" or not origin.hostname or origin.path not in ("", "/"):
                raise ValueError("LWH_WEB_ORIGIN must be the exact HTTPS application origin")
            if not self.jobs_secret or len(self.jobs_secret) < 32:
                raise ValueError("LWH_JOBS_SECRET must contain at least 32 characters")


@lru_cache
def get_platform_settings() -> PlatformSettings:
    return PlatformSettings()
