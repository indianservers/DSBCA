from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = ""
    database_url_unpooled: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    cors_allowed_origins: list[str] = []
    app_env: str = "development"
    reset_delivery_url: str = ""
    reset_delivery_token: str = ""
    openai_api_key: str = ""
    ai_chat_model: str = ""
    ai_fast_model: str = ""
    ai_embedding_model: str = ""
    ai_request_timeout: int = 45
    ai_total_request_timeout: float = Field(default=35, gt=0, le=45)
    ai_max_output_tokens: int = 1800
    ai_retrieval_top_k: int = 8
    ai_min_evidence_score: float = 0.25
    ai_history_window: int = 8
    ai_daily_requests: int = 50
    ai_daily_tokens: int = 150000
    ai_embedding_batch_size: int = 16
    ai_max_context_chars: int = 24000
    ai_retention_days: int = 365
    ai_vector_backend: str = "pgvector"
    pdf_max_bytes: int = 30000000
    pdf_max_pages: int = 200
    pdf_daily_uploads: int = 20
    pdf_storage_backend: str = "disabled"
    pdf_local_root: str = ".private_pdf_storage"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    indexing_worker_secret: str = ""
    cron_secret: str = ""
    data_encryption_key: str = ""
    resend_api_key: str = ""
    notification_email_from: str = ""
    fcm_project_id: str = ""
    fcm_service_account_file: str = ""
    indexing_lease_seconds: int = 180
    indexing_max_attempts: int = 5
    indexing_max_concurrency: int = 2


@lru_cache
def settings():
    value = Settings()
    import os

    if os.environ.get("VERCEL") == "1" and value.app_env not in {
        "production",
        "staging",
    }:
        raise ValueError("Vercel requires explicit production or staging APP_ENV")
    if value.app_env not in {"development", "test", "staging", "production"}:
        raise ValueError("Unknown APP_ENV")
    if value.app_env in {"production", "staging"}:
        import base64

        if not value.cors_allowed_origins or any(
            not x.startswith("https://") or "*" in x for x in value.cors_allowed_origins
        ):
            raise ValueError("Explicit HTTPS CORS origins required")
        from urllib.parse import urlparse

        for endpoint in [value.reset_delivery_url, value.s3_endpoint_url]:
            if endpoint and (
                urlparse(endpoint).scheme != "https" or not urlparse(endpoint).hostname
            ):
                raise ValueError(
                    "Hosted storage and reset-delivery endpoints require HTTPS"
                )
        if value.pdf_storage_backend == "local":
            raise ValueError(
                "Ephemeral local storage is forbidden in hosted environments"
            )
        if value.ai_vector_backend != "pgvector":
            raise ValueError("Hosted research requires the pgvector backend")
        try:
            if len(base64.urlsafe_b64decode(value.data_encryption_key)) != 32:
                raise ValueError()
        except Exception:
            raise ValueError("A valid independent data encryption key is required")
    if value.jwt_algorithm != "HS256":
        raise ValueError("Only HS256 is enabled")
    if value.app_env != "test" and len(value.jwt_secret_key) < 32:
        raise ValueError("Configure JWT_SECRET_KEY with at least 32 characters")
    return value
