from functools import lru_cache
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def to_asyncpg_url(url: str) -> str:
    """Railway 等の postgresql:// / postgres:// を asyncpg 用に正規化."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    replacements = (
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
        ("postgresql+psycopg://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
    )
    for src, dst in replacements:
        if url.startswith(src):
            return dst + url.removeprefix(src)
    return url


def _is_loopback_url(url: str) -> bool:
    lowered = url.lower()
    return any(
        host in lowered
        for host in (
            "://127.0.0.1",
            "://localhost",
            "://0.0.0.0",
            "://[::1]",
        )
    )


class Settings(BaseSettings):
    """アプリケーション設定（環境変数 / .env から読み込み）."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "e-Learning Platform API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://elearning:elearning@localhost:5433/elearning"
    redis_url: str = "redis://localhost:6379/0"

    # 本番は CORS_ORIGINS に公開 URL を設定。未設定時は *（Railway 公開用）
    cors_origins: str = "*"

    # 空 / loopback の場合は Railway 公開ドメイン or 同一オリジンを使う
    web_base_url: str = ""

    cognito_region: str = "ap-northeast-1"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""
    cognito_issuer: str = ""

    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str) and value:
            return to_asyncpg_url(value)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def public_web_base_url(self) -> str:
        """Never return 127.0.0.1/localhost for public redirects."""
        raw = (self.web_base_url or "").strip().rstrip("/")
        if raw and not _is_loopback_url(raw):
            return raw

        railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
        if railway_domain:
            if railway_domain.startswith("http://") or railway_domain.startswith("https://"):
                return railway_domain.rstrip("/")
            return f"https://{railway_domain}"

        # Same-origin portal (this public service)
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
