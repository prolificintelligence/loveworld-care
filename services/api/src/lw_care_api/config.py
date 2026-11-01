"""
Application Configuration for LoveWorld Care (/v1 API & Worker).
Loads cloud-hosted PostgreSQL, Redis, S3/R2, LiveKit, Paystack, Flutterwave,
Espees Wallet, KingsChat, Termii, Resend, and AI Model Gateway settings.
"""

from __future__ import annotations

from functools import lru_cache

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
    database_url: str = "sqlite+aiosqlite:///D:/.toolchains/tmp/lw_care_production.db"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    redis_url: str = "redis://localhost:6379/0"
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
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
    openrouter_api_key: str = ""
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
