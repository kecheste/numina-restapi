from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_database_url_and_connect_args() -> tuple[str, dict]:
    """Return (url, connect_args) for create_async_engine. Strips sslmode for asyncpg; use ssl=True for Neon."""
    url = settings.database_url
    need_ssl = "neon.tech" in url or "sslmode" in url
    if not need_ssl:
        return url, {}
    parsed = urlparse(url)
    q = parse_qs(parsed.query, keep_blank_values=True)
    for key in ("sslmode", "channel_binding"):
        q.pop(key, None)
    new_query = urlencode(q, doseq=True) if q else ""
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    return clean_url, {"ssl": True}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Numina API"
    api_v1_prefix: str = "/api/v1"

    # Neon Postgres: use postgresql+asyncpg://... for async SQLAlchemy
    database_url: str

    # Redis: required for BullMQ and caching
    redis_url: str = "redis://localhost:6379/0"

    # JWT (backend-issued tokens)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "numina-api"
    jwt_audience: str = "numina-api"
    jwt_access_token_expire_minutes: int = 60

    # Stripe (optional until payments are enabled)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    # OpenAI (optional; used by AI refinement worker)
    openai_api_key: str | None = None

    # AI safeguards: max tokens per request, rate limit per user per day
    ai_max_tokens_per_request: int = 1024
    ai_max_requests_per_user_per_day: int = 20


settings = Settings()
