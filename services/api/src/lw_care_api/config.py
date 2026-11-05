"""
Application Configuration for LoveWorld Care (/v1 API & Worker).
Loads cloud-hosted PostgreSQL, Redis, S3/R2, LiveKit, Paystack, Flutterwave,
Espees Wallet, KingsChat, Termii, Resend, and AI Model Gateway settings.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "production"
    jurisdiction_default: str = "NG"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"
    )

    # Cloud Database, Upstash Serverless Redis & S3/R2
    database_url: str = Field(
        default="sqlite+aiosqlite:///D:/.toolchains/tmp/lw_care_production.db",
        validation_alias=AliasChoices("LW_DATABASE_URL", "DATABASE_URL"),
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"
    upstash_redis_rest_url: str = Field(
        default="",
        validation_alias=AliasChoices("LW_UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_URL"),
    )
    upstash_redis_rest_token: str = Field(
        default="",
        validation_alias=AliasChoices("LW_UPSTASH_REDIS_REST_TOKEN", "UPSTASH_REDIS_REST_TOKEN"),
    )
    s3_endpoint_url: str = "https://r2.cloudflarestorage.com"
    s3_region: str = "auto"
    s3_bucket_clinical: str = "loveworld-care-clinical-t3"
    s3_bucket_exports: str = "loveworld-care-finance-exports"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_presigned_expiry_seconds: int = 300

    # Identity, Ed25519 Clinical Signing & Audit Chain Keys (T4)
    jwt_signing_key: str = "lw-care-jwt-signing-key-configure-in-production-env-256bit"
    session_cookie_secret: str = "lw-care-session-cookie-secret-configure-in-prod-256bit"
    clinical_signing_seed_hex: str = (
        "4c6f7665576f726c6443617265436c696e6963616c5369676e696e6753656564"
    )
    audit_hmac_chain_key: str = "lw-care-tamper-evident-audit-hmac-chain-key-256bit"
    break_glass_max_duration_minutes: int = 30

    # Bearer-token identity (ADR-0003). 32-byte Ed25519 seed as 64 hex chars.
    # Required in production; generated ephemerally per process in development/test.
    token_signing_seed_hex: str = ""
    token_issuer: str = "https://api.care.loveworld.org"
    access_token_ttl_minutes: int = 30

    # LiveKit WebRTC
    livekit_url: str = "wss://loveworld-care.livekit.cloud"
    livekit_api_key: str = "APILoveWorldCareKey"
    livekit_api_secret: str = "LoveWorldCareLiveKitSecretKeyMinimum32BytesLong"
    livekit_webhook_secret: str = "LoveWorldCareLiveKitWebhookSecretKey32Bytes"
    rtc_recording_enabled: bool = False

    # Payment Gateways: Paystack, Flutterwave, Espees Wallet
    paystack_secret_key: str = "sk_live_configure_in_env"
    paystack_public_key: str = "pk_live_configure_in_env"
    paystack_webhook_secret: str = "sk_live_configure_in_env"

    flutterwave_secret_key: str = "FLWSECK_configure_in_env"
    flutterwave_public_key: str = "FLWPUBK_configure_in_env"
    flutterwave_webhook_hash: str = "flw_webhook_hash_configure_in_env"

    espees_merchant_code: str = "LW_CARE_MERCHANT"
    espees_api_key: str = "espees_api_key_configure_in_env"
    espees_webhook_secret: str = "espees_webhook_secret_configure_in_env"
    espees_api_base_url: str = "https://api.espees.org/v2"

    # Secondary PHI-Free Messaging: KingsChat, Termii SMS, Resend Email
    kingschat_client_id: str = ""
    kingschat_client_secret: str = ""
    kingschat_api_url: str = "https://connect.kingsch.at/api"

    termii_api_key: str = ""
    termii_sender_id: str = "LWCare"
    termii_base_url: str = "https://v3.api.termii.com"

    resend_api_key: str = ""
    email_from: str = "no-reply@care.loveworld.org"

    # AI Model Gateway & Kill Switch (OpenRouter Free Tier + MedGemma + Gemini + Anthropic)
    ai_global_kill_switch: bool = False
    openrouter_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LW_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
    )
    gemini_api_key: str = ""
    gemini_model_admin: str = "gemini-2.5-flash"
    medgemma_endpoint_url: str = ""
    medgemma_api_key: str = ""
    medgemma_model_id: str = "google/medgemma-1.5-4b-it"
    anthropic_api_key: str = ""
    ai_max_cost_minor_per_encounter: int = 20000

    # SponsorCare & Unit Economics
    sponsor_small_cohort_min_k: int = 5
    default_gp_fee_ngn_minor: int = 600000  # 6,000.00 NGN in kobo
    default_gp_clinician_payable_ngn_minor: int = 330000  # 3,300.00 NGN in kobo
    default_institutional_access_fee_ngn_minor: int = 35000  # 350.00 NGN in kobo

    # ------------------------------------------------------------------
    # Fail-closed runtime validation (ADR-0003)
    # ------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() not in NON_PRODUCTION_ENVIRONMENTS

    @property
    def dev_token_endpoint_enabled(self) -> bool:
        return not self.is_production

    def insecure_configuration_findings(self) -> list[str]:
        """Return every reason this configuration is unsafe to run as production."""
        findings: list[str] = []
        fields = type(self).model_fields
        for name in PRODUCTION_SECRET_FIELDS:
            value = str(getattr(self, name) or "")
            default = str(fields[name].default or "")
            if not value:
                findings.append(f"{name} is empty")
            elif value == default:
                findings.append(f"{name} still uses the shipped default")
            elif any(marker in value.upper() for marker in PLACEHOLDER_MARKERS):
                findings.append(f"{name} contains a placeholder value")

        try:
            if len(bytes.fromhex(self.token_signing_seed_hex)) != 32:
                findings.append("token_signing_seed_hex must be 32 bytes (64 hex chars)")
        except ValueError:
            findings.append("token_signing_seed_hex is not valid hex")

        if self.database_url.startswith("sqlite"):
            findings.append("database_url points at SQLite")

        for origin in (o.strip() for o in self.cors_origins.split(",") if o.strip()):
            if origin == "*" or "localhost" in origin or "127.0.0.1" in origin:
                findings.append(f"cors_origins contains non-production origin '{origin}'")
            elif not origin.startswith("https://"):
                findings.append(f"cors_origins contains non-HTTPS origin '{origin}'")
        return findings

    def assert_safe_for_runtime(self) -> None:
        if not self.is_production:
            return
        findings = self.insecure_configuration_findings()
        if findings:
            raise InsecureConfigurationError(
                "Refusing to start LoveWorld Care API in production:\n  - "
                + "\n  - ".join(findings)
            )


NON_PRODUCTION_ENVIRONMENTS = frozenset({"development", "dev", "local", "test"})
PLACEHOLDER_MARKERS = ("REPLACE", "CONFIGURE_IN", "CHANGEME", "CHANGE_ME")
PRODUCTION_SECRET_FIELDS = (
    "jwt_signing_key",
    "session_cookie_secret",
    "clinical_signing_seed_hex",
    "audit_hmac_chain_key",
    "token_signing_seed_hex",
    "livekit_api_key",
    "livekit_api_secret",
    "livekit_webhook_secret",
    "paystack_secret_key",
    "paystack_webhook_secret",
)


class InsecureConfigurationError(RuntimeError):
    """Raised when production starts with default, placeholder or missing secrets."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
