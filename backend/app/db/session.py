"""Async engine + session factory. One session = one Unit of Work."""

from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base

SQLITE_BUSY_TIMEOUT_S = 30

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(url: str | None = None) -> AsyncEngine:
    """Create (or recreate) the global engine. Tests call this with their own URL."""
    global _engine, _session_factory
    db_url = url or get_settings().database_url
    kwargs: dict = {"future": True}
    if db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": SQLITE_BUSY_TIMEOUT_S}
    _engine = create_async_engine(db_url, **kwargs)
    if db_url.startswith("sqlite") and ":memory:" not in db_url:
        event.listen(_engine.sync_engine, "connect", _sqlite_pragmas)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def _sqlite_pragmas(dbapi_conn, _record) -> None:
    """WAL lets the tick loop write while API requests read."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def get_engine() -> AsyncEngine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


async def create_all() -> None:
    """Create tables directly (dev/tests). Production uses Alembic migrations."""
    import app.models  # noqa: F401  (registers all models on Base.metadata)

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    async with session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
