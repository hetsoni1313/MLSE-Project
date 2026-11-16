"""Async database manager supporting PostgreSQL and SQLite."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from llmops_governance.logging.setup import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages async database connections with auto-detection of backend."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/llmops.db")
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self._url

    async def initialize(self) -> None:
        """Create engine and session factory."""
        connect_args = {}
        pool_kwargs = {}

        if self.is_sqlite:
            connect_args = {"check_same_thread": False}
            # SQLite doesn't support pool_size
            pool_kwargs = {"pool_pre_ping": True}
            # Ensure directory exists
            db_path = self._url.split("///")[-1] if "///" in self._url else ""
            if db_path and db_path != ":memory:":
                os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        else:
            pool_kwargs = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_pre_ping": True,
            }

        self._engine = create_async_engine(
            self._url,
            echo=False,
            connect_args=connect_args,
            **pool_kwargs,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create all tables
        from llmops_governance.metrics.models import Base

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("database_initialized", url=self._url.split("@")[-1])

    async def close(self) -> None:
        """Close the database engine."""
        if self._engine:
            await self._engine.dispose()
            logger.info("database_closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional async session scope."""
        if self._session_factory is None:
            await self.initialize()
        assert self._session_factory is not None

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @property
    def engine(self) -> AsyncEngine | None:
        return self._engine


# Module-level singleton
_db_manager: DatabaseManager | None = None


def get_db_manager(url: str | None = None) -> DatabaseManager:
    """Get or create the database manager singleton."""
    global _db_manager  # noqa: PLW0603
    if _db_manager is None:
        _db_manager = DatabaseManager(url)
    return _db_manager


async def reset_db_manager() -> None:
    """Reset the database manager (for testing)."""
    global _db_manager  # noqa: PLW0603
    if _db_manager:
        await _db_manager.close()
    _db_manager = None
