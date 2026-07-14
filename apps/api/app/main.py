from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import Base, engine
from app.schemas import HealthResponse

# モデルを Base.metadata に登録
from app.models import core_entities as _core  # noqa: F401
from app.models import domain as _domain  # noqa: F401
from app.models import platform as _platform  # noqa: F401

STATIC_DIR = Path(__file__).resolve().parent.parent / "web_static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Never block process start on DB — Railway needs /health immediately.
    try:
        async with asyncio.timeout(8):
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("[elearning] database schema ready", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] database init skipped: {exc!r}", flush=True)

    # Demo catalog (best-effort; keeps UI useful on fresh Railway DB)
    try:
        async with asyncio.timeout(20):
            from app.scripts.seed import seed

            await seed()
            print("[elearning] demo seed applied", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] demo seed skipped: {exc!r}", flush=True)

    yield
    try:
        await engine.dispose()
    except Exception:  # noqa: BLE001
        pass


def _public_portal_html(settings) -> str:
    web = settings.public_web_base_url
    web_link = web or "/"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{settings.app_name}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{
      margin: 0; min-height: 100vh; font-family: "Hiragino Sans", "Noto Sans JP", sans-serif;
      background: linear-gradient(160deg, #eef5f6, #f7faf8); color: #12252b;
      display: grid; place-items: center;
    }}
    .box {{
      width: min(36rem, calc(100% - 2rem)); padding: 2rem; border-radius: 1rem;
      background: rgba(255,255,255,.88); border: 1px solid #c9d8db; box-shadow: 0 16px 40px rgba(18,37,43,.08);
    }}
    h1 {{ margin: 0 0 .5rem; font-size: 1.5rem; }}
    p {{ line-height: 1.6; color: #35545a; }}
    .links {{ display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1.25rem; }}
    a {{
      display: inline-block; padding: .65rem 1rem; border-radius: 999px; text-decoration: none; font-weight: 600;
      background: #12252b; color: #f4fafb;
    }}
    a.secondary {{ background: transparent; color: #0d5c63; border: 1px solid #9eb9be; }}
  </style>
</head>
<body>
  <main class="box">
    <h1>{settings.app_name}</h1>
    <p>公開エンドポイントで稼働中です。ローカルアドレスへはリダイレクトしません。</p>
    <div class="links">
      <a href="/docs">API ドキュメント</a>
      <a class="secondary" href="/health">Health</a>
      <a class="secondary" href="/courses/">サービス画面</a>
    </div>
  </main>
</body>
</html>"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    cors_kwargs: dict = {
        "allow_origins": settings.cors_origin_list,
        "allow_credentials": settings.cors_origin_list != ["*"],
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    app.add_middleware(CORSMiddleware, **cors_kwargs)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name, env=settings.app_env)

    @app.get("/", response_model=None, include_in_schema=False)
    async def root():
        """公開オリジン上でポータルを返す（127.0.0.1 へは飛ばさない）."""
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse(_public_portal_html(settings))

    @app.get("/app", response_class=HTMLResponse, include_in_schema=False)
    async def app_portal():
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse(_public_portal_html(settings))

    if STATIC_DIR.is_dir():
        next_assets = STATIC_DIR / "_next"
        if next_assets.is_dir():
            app.mount("/_next", StaticFiles(directory=str(next_assets)), name="next_assets")

        @app.get("/{full_path:path}", response_model=None, include_in_schema=False)
        async def spa_and_static(full_path: str):
            if full_path.split("/", 1)[0] in {"api", "docs", "redoc", "openapi.json", "health"}:
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            candidate = (STATIC_DIR / full_path).resolve()
            try:
                candidate.relative_to(STATIC_DIR.resolve())
            except ValueError:
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            if candidate.is_file():
                return FileResponse(candidate)
            nested = STATIC_DIR / full_path / "index.html"
            if nested.is_file():
                return FileResponse(nested)
            index = STATIC_DIR / "index.html"
            if index.is_file():
                return FileResponse(index)
            return JSONResponse({"detail": "Not Found"}, status_code=404)

    return app


app = create_app()
