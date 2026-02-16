from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str
    app_name: str
    api_v1_prefix: str

    database_url: str
    redis_url: str

    # JWT (backend-issued tokens)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "numina-api"
    jwt_audience: str = "numina-api"
    jwt_access_token_expire_minutes: int = 60

    stripe_secret_key: str
    stripe_webhook_secret: str


settings = Settings()
