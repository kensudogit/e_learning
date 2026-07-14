from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import Base, engine
from app.schemas import HealthResponse

# モデルを Base.metadata に登録
from app.models import domain as _domain  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 開発初期: create_all。本番は Alembic マイグレーションを使用
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001 — 起動時は DB 未起動でも docs/health を確認可能にする
        print(f"[warn] database init skipped: {exc}")
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name, env=settings.app_env)

    return app


app = create_app()
