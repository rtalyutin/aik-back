"""Database configuration and session management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from .core.config import Settings, get_settings


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create an asynchronous SQLAlchemy engine."""

    current_settings = settings or get_settings()
    return create_async_engine(current_settings.database_url, future=True, echo=False)


engine: AsyncEngine = create_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Initialise database tables."""

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope for database operations."""

    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an async session."""

    async with session_scope() as session:
        yield session
