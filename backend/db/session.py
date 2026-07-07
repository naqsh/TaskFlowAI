"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.settings import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def prepare_database_url(database_url: str) -> tuple[str, dict[str, Any]]:
    """Strip libpq query params unsupported by asyncpg and map SSL settings.

    Supavisor (port 6543) requires ``statement_cache_size=0`` for asyncpg.
    Passwords with special characters must be percent-encoded in ``DATABASE_URL``.
    """
    parsed = urlparse(database_url)
    query = dict(parse_qsl(parsed.query))
    connect_args: dict[str, Any] = {}
    sslmode = query.pop("sslmode", None)
    if sslmode in {"require", "verify-full", "verify-ca"}:
        connect_args["ssl"] = "require"
    if "supabase.com" in parsed.netloc or parsed.port == 6543:
        connect_args["statement_cache_size"] = 0
    clean = parsed._replace(query=urlencode(query))
    return urlunparse(clean), connect_args


def init_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create or return the cached async engine."""
    global _engine, _session_factory
    resolved = settings or get_settings()
    if _engine is None:
        url, connect_args = prepare_database_url(resolved.database_url)
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            echo=resolved.app_debug,
            connect_args=connect_args,
            pool_reset_on_return=None,
        )
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, initializing the engine if needed."""
    init_engine()
    assert _session_factory is not None
    return _session_factory


def reset_engine() -> None:
    """Clear cached engine and session factory (for tests)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def dispose_engine() -> None:
    """Dispose the cached engine and reset module state."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide a transactional async session scope."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
