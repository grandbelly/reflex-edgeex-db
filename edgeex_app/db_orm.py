"""
Fixed SQLAlchemy ORM Configuration for Reflex
=============================================
Reflex 이벤트 루프와 호환되도록 수정된 버전

Key Changes:
1. Lazy engine initialization
2. Background event compatible
3. No module-level async operations
"""
from __future__ import annotations

import os
import ssl
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
import logging
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
RAW_DSN = os.getenv(
    "TS_DSN",
    "postgresql://postgres:postgres@pgai-db:5432/ecoanp?sslmode=disable"
)

# USE_DB_POOLING=false keeps NullPool (default, for Reflex background events
# which each open a fresh asyncpg connection). Long-running schedulers should
# opt in via USE_DB_POOLING=true to avoid per-query connection-setup latency.
USE_POOLING = os.getenv("USE_DB_POOLING", "false").lower() == "true"
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

# asyncpg command_timeout was previously hardcoded to 10s — too tight for
# TimescaleDB hypertable inserts (chunk creation + many horizons per session).
COMMAND_TIMEOUT = int(os.getenv("DB_COMMAND_TIMEOUT", "30"))
CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

# Server-side statement_timeout in ms (set 0 to disable). Independent of
# asyncpg's command_timeout — enforced by Postgres, bounds the query DB-side.
STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000"))

POOL_TRACE = os.getenv("DB_POOL_TRACE", "false").lower() == "true"

def normalize_asyncpg_url(raw: str) -> str:
    """
    asyncpg doesn't accept 'sslmode' in URL parameters
    Remove it and convert to postgresql+asyncpg://
    """
    parsed = urlparse(raw)

    # Change scheme to asyncpg
    if parsed.scheme in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"
    elif "asyncpg" in parsed.scheme:
        scheme = parsed.scheme
    else:
        scheme = "postgresql+asyncpg"

    # Remove sslmode from query params for asyncpg
    query_params = parse_qs(parsed.query)
    query_params.pop('sslmode', None)

    # Rebuild URL
    new_query = urlencode(query_params, doseq=True) if query_params else ""
    new_url = urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return new_url

ASYNC_URL = normalize_asyncpg_url(RAW_DSN)

# ------------------------------------------------------------------------------
# Global Engine Manager (Lazy Initialization)
# ------------------------------------------------------------------------------
class EngineManager:
    """
    Lazy engine initialization to avoid event loop conflicts
    Engine is created only when first needed
    """
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        # Diagnostics — populated when POOL_TRACE is on (or accessed by tests)
        self.checkouts = 0
        self.checkins = 0
        self.connects = 0

    def get_engine(self) -> AsyncEngine:
        """Get or create engine (lazy initialization)"""
        if self._engine is None:
            server_settings = {
                "application_name": "reflex_app",
                "jit": "off",
            }
            from .scada_config import scada_server_settings
            server_settings.update(scada_server_settings())
            if STATEMENT_TIMEOUT_MS > 0:
                # asyncpg uses str values for server_settings
                server_settings["statement_timeout"] = str(STATEMENT_TIMEOUT_MS)

            connect_args = {
                "server_settings": server_settings,
                "timeout": CONNECT_TIMEOUT,
                "command_timeout": COMMAND_TIMEOUT,
            }

            if USE_POOLING:
                logger.info(
                    "Creating async engine with AsyncAdaptedQueuePool "
                    "(pool_size=%d, max_overflow=%d, pool_timeout=%d, "
                    "pool_recycle=%d, command_timeout=%d, "
                    "statement_timeout_ms=%d)",
                    POOL_SIZE, MAX_OVERFLOW, POOL_TIMEOUT,
                    POOL_RECYCLE, COMMAND_TIMEOUT, STATEMENT_TIMEOUT_MS,
                )
                self._engine = create_async_engine(
                    ASYNC_URL,
                    echo=False,
                    poolclass=AsyncAdaptedQueuePool,
                    pool_size=POOL_SIZE,
                    max_overflow=MAX_OVERFLOW,
                    pool_timeout=POOL_TIMEOUT,
                    pool_recycle=POOL_RECYCLE,
                    pool_pre_ping=True,
                    connect_args=connect_args,
                )
            else:
                # Legacy behavior: NullPool for Reflex background-event
                # compatibility. Each get_async_session() opens a fresh
                # asyncpg connection.
                logger.info(
                    "Creating async engine with NullPool "
                    "(command_timeout=%d, statement_timeout_ms=%d)",
                    COMMAND_TIMEOUT, STATEMENT_TIMEOUT_MS,
                )
                self._engine = create_async_engine(
                    ASYNC_URL,
                    echo=False,
                    poolclass=NullPool,
                    connect_args=connect_args,
                )

            # Pool checkout/checkin counters — drive the connection-leak
            # regression tests; opt-in trace logging via DB_POOL_TRACE=true.
            sync_engine = self._engine.sync_engine

            @event.listens_for(sync_engine, "connect")
            def _on_connect(dbapi_conn, conn_record):  # noqa: ARG001
                self.connects += 1
                if POOL_TRACE:
                    logger.debug("DB connect (#%d)", self.connects)

            @event.listens_for(sync_engine, "checkout")
            def _on_checkout(dbapi_conn, conn_record, conn_proxy):  # noqa: ARG001
                self.checkouts += 1
                if POOL_TRACE:
                    logger.debug(
                        "DB checkout (#%d, outstanding=%d)",
                        self.checkouts, self.checkouts - self.checkins,
                    )

            @event.listens_for(sync_engine, "checkin")
            def _on_checkin(dbapi_conn, conn_record):  # noqa: ARG001
                self.checkins += 1
                if POOL_TRACE:
                    logger.debug(
                        "DB checkin (#%d, outstanding=%d)",
                        self.checkins, self.checkouts - self.checkins,
                    )

            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

        return self._engine

    def get_session_factory(self) -> async_sessionmaker:
        """Get session factory"""
        if self._session_factory is None:
            self.get_engine()  # Initialize engine first
        return self._session_factory

    async def close(self):
        """Close engine"""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self.checkouts = 0
            self.checkins = 0
            self.connects = 0

    @property
    def outstanding_connections(self) -> int:
        """Connections currently checked out but not yet returned."""
        return self.checkouts - self.checkins

# Global manager instance
_manager = EngineManager()

# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async session for use in Reflex background events

    Usage in Reflex State:
    ```python
    @rx.event(background=True)  # REQUIRED!
    async def load_data(self):
        async with get_async_session() as session:
            result = await session.execute(select(Table))
            data = [row.to_dict() for row in result.scalars()]

        async with self:  # REQUIRED for state updates
            self.data = data
            yield  # Optional UI update
    ```
    """
    session_factory = _manager.get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

def get_engine() -> AsyncEngine:
    """
    Get the async engine (for direct use if needed)
    WARNING: Usually you should use get_async_session() instead
    """
    return _manager.get_engine()


def get_engine_manager() -> "EngineManager":
    """Return the singleton EngineManager (exposes checkout/checkin counters).

    Intended for tests and operational diagnostics — production code should
    keep using ``get_async_session()``.
    """
    return _manager


async def close_engine():
    """Close the engine and clean up connections"""
    await _manager.close()

# ------------------------------------------------------------------------------
# Test Connection
# ------------------------------------------------------------------------------
async def test_connection() -> bool:
    """Test database connection"""
    try:
        async with get_async_session() as session:
            result = await session.execute("SELECT 1")
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
