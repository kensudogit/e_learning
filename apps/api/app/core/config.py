from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定（環境変数 / .env から読み込み）."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "e-Learning Platform API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database (local: PostgreSQL / prod: Amazon RDS)
    database_url: str = "postgresql+asyncpg://elearning:elearning@localhost:5433/elearning"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: str = "http://localhost:3000"

    # AWS Cognito (本番・ステージング用)
    cognito_region: str = "ap-northeast-1"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""
    cognito_issuer: str = ""

    # JWT (ローカル開発用フォールバック)
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
