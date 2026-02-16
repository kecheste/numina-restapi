from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str
    app_name: str
    api_v1_prefix: str

    database_url: str
    redis_url: str

    jwt_issuer: str
    jwt_audience: str
    jwt_public_key: str

    stripe_secret_key: str
    stripe_webhook_secret: str

    class Config:
        env_file = ".env"

settings = Settings()
