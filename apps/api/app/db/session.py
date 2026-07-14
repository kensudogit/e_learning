from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings, to_asyncpg_url


class Base(DeclarativeBase):
    pass


settings = get_settings()
_database_url = to_asyncpg_url(settings.database_url)

# Short timeouts so a bad/unreachable DATABASE_URL cannot block Railway boot.
engine = create_async_engine(
    _database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args={
        "timeout": 5,
        "command_timeout": 5,
        "server_settings": {"application_name": "elearning-api"},
    },
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
