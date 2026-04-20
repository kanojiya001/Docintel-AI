from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

_db_url = settings.DATABASE_URL

# ── Convert URL to async driver ───────────────────────────────────────────────
if _db_url.startswith("postgresql://"):
    ASYNC_DATABASE_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql+asyncpg://"):
    ASYNC_DATABASE_URL = _db_url
elif _db_url.startswith("sqlite"):
    ASYNC_DATABASE_URL = _db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
else:
    ASYNC_DATABASE_URL = _db_url

# ── Engine config ─────────────────────────────────────────────────────────────
_connect_args = {}
_engine_kwargs = {"echo": False}

if "pooler.supabase.com" in ASYNC_DATABASE_URL:
    # Transaction pooler — disable prepared statements
    _connect_args = {"statement_cache_size": 0}

if "sqlite" in ASYNC_DATABASE_URL:
    _connect_args = {"check_same_thread": False}
else:
    _engine_kwargs.update({"pool_size": 10, "max_overflow": 5})

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args=_connect_args,
    **_engine_kwargs,
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
